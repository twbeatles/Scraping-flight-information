"""Domestic-flight helpers for Playwright scraper."""

from __future__ import annotations

import heapq
import logging
import time
from typing import TYPE_CHECKING, Any, Dict, List

import scraper_config
from scraper_config import ScraperScripts
from scraping.models import FlightResult

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")


def combine_domestic_round_trip(
    outbound_flights: List[Dict[str, Any]],
    return_flights: List[Dict[str, Any]],
    max_results: int,
) -> List[FlightResult]:
    """Create the cheapest domestic round-trip combinations."""

    outbound_flights = [
        item
        for item in outbound_flights
        if item.get("price", 0) > 0 and item.get("depTime") and item.get("arrTime")
    ]
    return_flights = [
        item
        for item in return_flights
        if item.get("price", 0) > 0 and item.get("depTime") and item.get("arrTime")
    ]
    if not outbound_flights or not return_flights:
        return []

    outbound_flights.sort(key=lambda item: item["price"])
    return_flights.sort(key=lambda item: item["price"])
    top_outbound = outbound_flights[: scraper_config.DOMESTIC_COMBINATION_TOP_N]
    top_return = return_flights[: scraper_config.DOMESTIC_COMBINATION_TOP_N]

    max_keep = (
        max_results
        if isinstance(max_results, int) and max_results > 0
        else len(top_outbound) * len(top_return)
    )
    max_heap: list[tuple[int, int, FlightResult]] = []
    seen = set()
    seq = 0

    for outbound in top_outbound:
        for returning in top_return:
            total_price = outbound["price"] + returning["price"]
            dedup_key = (
                outbound["airline"],
                returning["airline"],
                total_price,
                outbound["depTime"],
                returning["depTime"],
            )
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            seq += 1

            flight = FlightResult(
                airline=outbound["airline"],
                price=total_price,
                departure_time=outbound["depTime"],
                arrival_time=outbound["arrTime"],
                stops=outbound["stops"],
                source="Interpark (국내선)",
                return_departure_time=returning["depTime"],
                return_arrival_time=returning["arrTime"],
                return_stops=returning["stops"],
                is_round_trip=True,
                outbound_price=outbound["price"],
                return_price=returning["price"],
                return_airline=returning["airline"],
                confidence=0.8,
                extraction_source="domestic_combined",
            )

            entry = (-total_price, -seq, flight)
            if len(max_heap) < max_keep:
                heapq.heappush(max_heap, entry)
                continue

            worst_price = -max_heap[0][0]
            worst_seq = -max_heap[0][1]
            if (total_price, seq) < (worst_price, worst_seq):
                heapq.heapreplace(max_heap, entry)

    ranked = sorted(max_heap, key=lambda item: (-item[0], -item[1]))
    return [item[2] for item in ranked]


def extract_domestic_flights_data(scraper: "PlaywrightScraper") -> list:
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


def build_domestic_results(
    items: List[Dict[str, Any]],
    *,
    source: str = "Interpark (국내선)",
    extraction_source: str = "domestic_scroll",
    confidence: float = 0.75,
) -> List[FlightResult]:
    """Normalize raw domestic items into `FlightResult`s."""

    results: List[FlightResult] = []
    seen = set()

    for item in items or []:
        price = int(item.get("price", 0) or 0)
        dep_time = item.get("depTime", "") or ""
        arr_time = item.get("arrTime", "") or ""
        airline = item.get("airline", "Unknown") or "Unknown"
        stops = int(item.get("stops", 0) or 0)

        if price <= 0 or not dep_time or not arr_time:
            continue

        key = f"{airline}_{dep_time}_{arr_time}_{price}"
        if key in seen:
            continue
        seen.add(key)

        results.append(
            FlightResult(
                airline=airline,
                price=price,
                departure_time=dep_time,
                arrival_time=arr_time,
                stops=stops,
                source=source,
                return_departure_time="",
                return_arrival_time="",
                return_stops=0,
                is_round_trip=False,
                confidence=confidence,
                extraction_source=extraction_source,
            )
        )

    return results


def extract_domestic_prices(scraper: "PlaywrightScraper") -> List[FlightResult]:
    """Convert scrolled domestic results into final results."""

    if not scraper.page:
        return []

    logger.info("🇰🇷 국내선 항공편 추출 시작...")
    try:
        extracted = scraper._extract_domestic_flights_data()
        results = build_domestic_results(
            extracted,
            source="Interpark (국내선)",
            extraction_source="domestic_scroll",
            confidence=0.75,
        )
        logger.info("🇰🇷 국내선 추출 완료: %s개", len(results))
        return results
    except Exception as exc:
        logger.error("Domestic extraction error: %s", exc, exc_info=True)
        return []
