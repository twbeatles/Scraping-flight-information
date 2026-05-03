"""Domestic-flight helpers for Playwright scraper."""

from __future__ import annotations

import heapq
import logging
import time
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

import scraper_config
from scraper_config import ScraperScripts
from scraping.models import FlightResult
from scraping.playwright_api import find_latest_search_key, get_api_meta, page_fetch_json, recent_api_resource_urls

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")


DOMESTIC_CARRIER_NAMES = {
    "KE": "대한항공",
    "OZ": "아시아나항공",
    "7C": "제주항공",
    "LJ": "진에어",
    "TW": "티웨이항공",
    "BX": "에어부산",
    "RS": "에어서울",
    "ZE": "이스타항공",
    "YP": "에어프레미아",
}


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
                str(outbound.get("key", "") or ""),
                str(returning.get("key", "") or ""),
                outbound["airline"],
                returning["airline"],
                total_price,
                outbound["depTime"],
                outbound.get("arrTime", ""),
                returning["depTime"],
                returning.get("arrTime", ""),
                outbound.get("flightNumber", ""),
                returning.get("flightNumber", ""),
                _coerce_int(outbound.get("benefitPrice")),
                _coerce_int(returning.get("benefitPrice")),
                str(outbound.get("benefitLabel", "") or ""),
                str(returning.get("benefitLabel", "") or ""),
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
                flight_number=str(outbound.get("flightNumber", "") or ""),
                source="Interpark (국내선)",
                return_departure_time=returning["depTime"],
                return_arrival_time=returning["arrTime"],
                return_stops=returning["stops"],
                is_round_trip=True,
                outbound_price=outbound["price"],
                return_price=returning["price"],
                return_airline=returning["airline"],
                benefit_price=_coerce_int(outbound.get("benefitPrice")) + _coerce_int(returning.get("benefitPrice")),
                benefit_label=_combine_benefit_labels(outbound, returning),
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
    """Collect domestic flight items, preferring the paged API over DOM scraping."""

    items, metadata = extract_domestic_api_flights_data(scraper)
    if items:
        scraper._search_metrics.update(
            {
                "api_total_count": _coerce_int(metadata.get("total_count")),
                "fetched_pages": _coerce_int(metadata.get("fetched_pages")),
                "api_item_count": len(items),
            }
        )
        return items

    if not getattr(scraper, "_manual_reason", ""):
        scraper._manual_reason = "domestic_api_failed"
    return extract_domestic_dom_flights_data(scraper)


def extract_domestic_api_flights_data(
    scraper: "PlaywrightScraper",
    *,
    search_key: str | None = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    if not scraper.page:
        return [], {"total_count": 0, "fetched_pages": 0}

    key = str(search_key or "").strip() or find_latest_search_key(scraper, trip_kind="domestic")
    if not key:
        logger.info("국내선 API search key를 찾지 못했습니다.")
        _record_domestic_api_failure(scraper, "domestic_api_key_missing", {})
        return [], {"total_count": 0, "fetched_pages": 0}

    context = getattr(scraper, "_last_search_context", {}) or {}
    cabin = str(context.get("cabin_class", "ECONOMY") or "ECONOMY").upper()
    page_size = 20
    page_number = 1
    total_pages = 1
    total_count = 0
    seen: Dict[str, Dict[str, Any]] = {}

    while page_number <= total_pages:
        payload = _fetch_domestic_search_page(scraper, key, page_number=page_number, page_size=page_size, cabin=cabin)
        if not payload:
            _record_domestic_api_failure(scraper, "domestic_api_result_fetch_failed", {})
            break

        page_meta = payload.get("page")
        if not isinstance(page_meta, dict):
            _record_domestic_api_failure(scraper, "domestic_api_payload_mismatch", payload)
            break
        if isinstance(page_meta, dict):
            page_size = max(_coerce_int(page_meta.get("pageSize")), page_size)
            total_count = max(total_count, _coerce_int(page_meta.get("totalCount")))
            total_pages = max((total_count + page_size - 1) // page_size, page_number)

        items = payload.get("items")
        if not isinstance(items, list) or not items:
            _record_domestic_api_failure(scraper, "domestic_api_payload_mismatch", payload)
            break

        for item in items:
            normalized = _normalize_domestic_api_item(item)
            if not normalized:
                continue
            seen[normalized["key"]] = normalized

        page_number += 1

    return (
        sorted(seen.values(), key=lambda item: item.get("price", float("inf"))),
        {
            "total_count": total_count,
            "fetched_pages": max(page_number - 1, 0),
        },
    )


def _fetch_domestic_search_page(
    scraper: "PlaywrightScraper",
    search_key: str,
    *,
    page_number: int,
    page_size: int,
    cabin: str,
) -> Dict[str, Any]:
    url = f"{scraper_config.INTERPARK_AIR_API_BASE}/domestic/flights/search/{search_key}"
    payload = page_fetch_json(
        scraper,
        url,
        method="POST",
        body={
            "pageNumber": page_number,
            "pageSize": page_size,
            "filter": {
                "byAirline": None,
                "byDepartureTimes": None,
                "byPaymentMethods": None,
                "byDiscountTypes": None,
                "byCabins": [cabin],
            },
        },
    )
    return payload if isinstance(payload, dict) else {}


def _record_domestic_api_failure(
    scraper: "PlaywrightScraper",
    reason: str,
    payload: Dict[str, Any],
) -> None:
    if not getattr(scraper, "_manual_reason", ""):
        scraper._manual_reason = reason
    metrics = getattr(scraper, "_search_metrics", None)
    if not isinstance(metrics, dict):
        return
    meta = get_api_meta(payload) if isinstance(payload, dict) else {}
    metrics["api_failure_reason"] = reason
    metrics["api_failure_payload_keys"] = list(payload.keys())[:20] if isinstance(payload, dict) else []
    if meta:
        metrics["api_failure_meta"] = {
            "status": int(meta.get("status") or 0),
            "ok": bool(meta.get("ok")),
            "payload_keys": [str(item) for item in meta.get("payload_keys", [])[:20]],
        }
    resources = recent_api_resource_urls(scraper, trip_kind="domestic")
    if resources:
        metrics["api_recent_resources"] = resources


def _normalize_domestic_api_item(item: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(item, dict):
        return {}

    schedule = item.get("schedule")
    if not isinstance(schedule, dict):
        return {}

    dep_time = _iso_timestamp_to_hhmm(schedule.get("departureAt"))
    arr_time = _iso_timestamp_to_hhmm(schedule.get("arrivalAt"))
    if not dep_time or not arr_time:
        return {}

    fares = item.get("fares")
    if not isinstance(fares, list) or not fares:
        return {}

    best_price = 0
    best_benefit_price = 0
    best_benefit_label = ""
    for fare in fares:
        if not isinstance(fare, dict):
            continue
        total_price = _coerce_int(fare.get("totalPrice"))
        if total_price <= 0:
            continue
        benefit_price, benefit_label = _extract_domestic_benefit(fare)
        if best_price == 0 or total_price < best_price:
            best_price = total_price
            best_benefit_price = benefit_price
            best_benefit_label = benefit_label

    if best_price <= 0:
        return {}

    carrier_code = str(schedule.get("marketingCarrier", "") or "").upper()
    airline = DOMESTIC_CARRIER_NAMES.get(carrier_code, carrier_code or "Unknown")
    flight_number = str(schedule.get("flightNumber", "") or "")
    key = str(item.get("key") or item.get("id") or f"{carrier_code}_{dep_time}_{arr_time}_{best_price}")

    return {
        "key": key,
        "airline": airline,
        "price": best_price,
        "benefitPrice": best_benefit_price,
        "benefitLabel": best_benefit_label,
        "depTime": dep_time,
        "arrTime": arr_time,
        "stops": 0,
        "flightNumber": flight_number,
        "seatAvailability": _coerce_int(item.get("seatAvailability")),
        "discountType": str(item.get("discountType", "") or ""),
    }


def _extract_domestic_benefit(fare: Dict[str, Any]) -> Tuple[int, str]:
    benefits = fare.get("benefits")
    if not isinstance(benefits, list):
        return 0, ""

    best_price = 0
    best_label = ""
    for benefit in benefits:
        if not isinstance(benefit, dict):
            continue
        discounted_price = _coerce_int(benefit.get("discountedPrice"))
        if discounted_price <= 0:
            continue

        cashback = benefit.get("cardCashback")
        if isinstance(cashback, dict):
            card_name = str(cashback.get("cardName", "") or "").strip()
            rate = cashback.get("rate")
            amount = _coerce_int(cashback.get("amount"))
            if rate:
                label = f"{card_name} {rate}% 캐시백 적용 시".strip()
            elif amount > 0:
                label = f"{card_name} {amount:,}원 캐시백 적용 시".strip()
            else:
                label = f"{card_name} 혜택가".strip()
        else:
            label = "혜택가"

        if best_price == 0 or discounted_price < best_price:
            best_price = discounted_price
            best_label = label

    return best_price, best_label


def _iso_timestamp_to_hhmm(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) >= 16 and "T" in text:
        return text[11:16]
    return ""


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
        flight_number = str(item.get("flightNumber", "") or "")
        benefit_price = _coerce_int(item.get("benefitPrice"))
        benefit_label = str(item.get("benefitLabel", "") or "")

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
                flight_number=flight_number,
                source=source,
                return_departure_time="",
                return_arrival_time="",
                return_stops=0,
                is_round_trip=False,
                benefit_price=benefit_price,
                benefit_label=benefit_label,
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
            extraction_source="domestic_api" if any(item.get("flightNumber") for item in extracted) else "domestic_scroll",
            confidence=0.9 if any(item.get("flightNumber") for item in extracted) else 0.75,
        )
        logger.info("🇰🇷 국내선 추출 완료: %s개", len(results))
        return results
    except Exception as exc:
        logger.error("Domestic extraction error: %s", exc, exc_info=True)
        return []


def _coerce_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _combine_benefit_labels(outbound: Dict[str, Any], returning: Dict[str, Any]) -> str:
    parts: list[str] = []
    outbound_price = _coerce_int(outbound.get("benefitPrice"))
    return_price = _coerce_int(returning.get("benefitPrice"))
    outbound_label = str(outbound.get("benefitLabel", "") or "").strip()
    return_label = str(returning.get("benefitLabel", "") or "").strip()

    if outbound_price > 0:
        label = outbound_label or "혜택가"
        parts.append(f"가는편 {label}: {outbound_price:,}원")
    if return_price > 0:
        label = return_label or "혜택가"
        parts.append(f"오는편 {label}: {return_price:,}원")
    return " | ".join(parts)
