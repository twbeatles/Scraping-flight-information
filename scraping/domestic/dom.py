"""Domestic DOM fallback extraction path."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Dict

import scraping.interpark as scraper_config
from scraping.interpark.scripts import ScraperScripts
from scraping.search_cancel import raise_if_search_cancelled

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")


def extract_domestic_dom_flights_data(scraper: "PlaywrightScraper") -> list:
    """Collect domestic flight cards while scrolling."""

    if not scraper.page:
        return []

    all_flights: Dict[str, Dict[str, Any]] = {}
    scraper._no_scroll_count = 0
    scraper._no_new_count = 0
    scraper._bottom_count = 0
    airlines_js = str(scraper.DOMESTIC_AIRLINES)

    try:
        scroll_index = -1
        for scroll_index in range(scraper_config.DOMESTIC_MAX_SCROLLS):
            raise_if_search_cancelled(scraper)
            js_script = ScraperScripts.get_domestic_list_script(airlines_js)
            batch = scraper.page.evaluate(js_script)

            new_count = 0
            for item in batch:
                key = item.get(
                    "key",
                    f"{item['airline']}_{item['depTime']}_{item['arrTime']}_{item['price']}",
                )
                if key in all_flights:
                    continue
                all_flights[key] = item
                new_count += 1

            scroll_script = ScraperScripts.get_scroll_check_script()
            scroll_result = scraper.page.evaluate(scroll_script)
            time.sleep(scraper_config.DOMESTIC_SCROLL_PAUSE_SECONDS)

            can_scroll = scroll_result.get("canScroll", False)
            reached_bottom = scroll_result.get("reachedBottom", False)

            if reached_bottom and new_count == 0:
                scraper._bottom_count += 1
                logger.debug(
                    "최하단 도달 체크: %s/3 (새 항목 없음)",
                    scraper._bottom_count,
                )
                if scraper._bottom_count >= 3:
                    logger.info(
                        "✅ 스크롤 최하단 확인: %s개 수집 완료, 다음 단계로 진행",
                        len(all_flights),
                    )
                    break
                time.sleep(scraper_config.DOMESTIC_SCROLL_BOTTOM_PAUSE_SECONDS)
                continue
            scraper._bottom_count = 0

            if not can_scroll:
                scraper._no_scroll_count += 1
                if scraper._no_scroll_count >= 3:
                    logger.info(
                        "스크롤 종료: 더 이상 스크롤할 수 없음 (%s개 수집)",
                        len(all_flights),
                    )
                    break
            else:
                scraper._no_scroll_count = 0

            if new_count == 0:
                scraper._no_new_count += 1
                if scraper._no_new_count >= 8:
                    logger.info(
                        "스크롤 조기 종료: %s회 연속 새 항목 없음 (%s개 수집)",
                        scraper._no_new_count,
                        len(all_flights),
                    )
                    break
            else:
                scraper._no_new_count = 0

        result_list = sorted(
            all_flights.values(),
            key=lambda item: item.get("price", float("inf")),
        )
        logger.info("국내선 %s개 항공편 추출 (스크롤 %s회)", len(result_list), scroll_index + 1)
        return result_list
    except Exception as exc:
        logger.error("Extract domestic data error: %s", exc, exc_info=True)
        return []
