"""Shared result helpers for Playwright scraper."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, List, Optional

import scraper_config
from scraper_config import ScraperScripts
from scraping.models import FlightResult

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")


def sort_and_limit_results(
    results: List[FlightResult],
    max_results: int,
    log_func: Optional[Callable[[str], None]] = None,
) -> List[FlightResult]:
    """Sort results by price and cap the list when needed."""

    if not results:
        return []

    ordered = sorted(results, key=lambda item: item.price if item.price > 0 else float("inf"))
    if isinstance(max_results, int) and max_results > 0 and len(ordered) > max_results:
        if log_func:
            log_func(f"⚠️ 결과 {len(ordered)}개 중 상위 {max_results}개만 유지합니다.")
        return ordered[:max_results]
    return ordered


def extract_international_prices(scraper: "PlaywrightScraper") -> List[FlightResult]:
    """Extract international flight results from the current page."""

    if not scraper.page:
        return []

    all_results_dict = {}
    max_scrolls = scraper_config.INTERNATIONAL_MAX_SCROLLS
    pause_time = scraper_config.SCROLL_PAUSE_TIME
    logger.info("📜 점진적 추출 시작 (최대 %s회 스크롤)...", max_scrolls)

    try:
        previous_height = 0
        for index in range(max_scrolls):
            js_script = ScraperScripts.get_international_prices_script()
            step_source = "international_primary"
            step_confidence = 0.9
            step_results = scraper.page.evaluate(js_script)

            if not step_results and index == 0:
                fallback_script = ScraperScripts.get_international_prices_fallback_script()
                fallback_results = scraper.page.evaluate(fallback_script)
                if fallback_results:
                    logger.info("국제선 보조 스크립트로 재시도")
                    step_results = fallback_results
                    step_source = "international_fallback"
                    step_confidence = 0.6

            current_count = 0
            for item in step_results:
                item.setdefault("extraction_source", step_source)
                item.setdefault("confidence", step_confidence)
                unique_key = (
                    f"{item.get('airline', '')}|{item.get('price', 0)}|"
                    f"{item.get('depTime', '')}|{item.get('arrTime', '')}|{item.get('stops', 0)}|"
                    f"{item.get('retDepTime', '')}|{item.get('retArrTime', '')}|{item.get('retStops', 0)}"
                )
                if unique_key in all_results_dict:
                    continue
                all_results_dict[unique_key] = item
                current_count += 1

            logger.info(
                "🧭 스크롤 %s: 새 결과 %s개 추가 (총 %s개)",
                index + 1,
                current_count,
                len(all_results_dict),
            )

            scraper.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            scraper.page.wait_for_timeout(pause_time * 1000)

            new_height = scraper.page.evaluate("document.body.scrollHeight")
            if new_height == previous_height and index > 2:
                logger.info("🧭 더 이상 새 콘텐츠가 로드되지 않습니다.")
                break
            previous_height = new_height
    except Exception as exc:
        logger.error("Extraction error: %s", exc, exc_info=True)

    if not all_results_dict and scraper.page:
        fallback_script = ScraperScripts.get_international_prices_fallback_script()
        fallback_results = scraper.page.evaluate(fallback_script)
        if fallback_results:
            for item in fallback_results:
                item.setdefault("extraction_source", "international_fallback")
                item.setdefault("confidence", 0.6)
                unique_key = (
                    f"{item.get('airline', '')}|{item.get('price', 0)}|"
                    f"{item.get('depTime', '')}|{item.get('arrTime', '')}|{item.get('stops', 0)}|"
                    f"{item.get('retDepTime', '')}|{item.get('retArrTime', '')}|{item.get('retStops', 0)}"
                )
                all_results_dict[unique_key] = item

    results: List[FlightResult] = []
    for item in all_results_dict.values():
        results.append(
            FlightResult(
                airline=item.get("airline", "Unknown"),
                price=item.get("price", 0),
                departure_time=item.get("depTime", ""),
                arrival_time=item.get("arrTime", ""),
                stops=item.get("stops", 0),
                source="Interpark (Auto)",
                return_departure_time=item.get("retDepTime", ""),
                return_arrival_time=item.get("retArrTime", ""),
                return_stops=item.get("retStops", 0),
                is_round_trip=item.get("isRoundTrip", False),
                confidence=float(item.get("confidence", 0.9)),
                extraction_source=item.get("extraction_source", "international_primary"),
            )
        )

    return results
