"""Shared result helpers for Playwright scraper."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional

import scraper_config
from scraper_config import ScraperScripts
from scraping.models import FlightResult
from scraping.playwright_api import find_latest_search_key, get_api_meta, page_fetch_json, recent_api_resource_urls

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

    api_results = _extract_international_prices_via_api(scraper)
    if api_results:
        logger.info("🌍 국제선 API 추출 성공: %s개", len(api_results))
        return api_results

    logger.info("🌍 국제선 API 추출 실패 - DOM fallback으로 전환")
    return _extract_international_prices_from_dom(scraper)


def _extract_international_prices_via_api(scraper: "PlaywrightScraper") -> List[FlightResult]:
    try:
        context = getattr(scraper, "_last_search_context", {}) or {}
        if not context or context.get("is_domestic"):
            return []

        search_key = find_latest_search_key(scraper, trip_kind="international")
        initial: Dict[str, Any] = {}
        if not search_key:
            search_url = scraper_config.build_interpark_international_api_search_url(
                context.get("origin", ""),
                context.get("destination", ""),
                context.get("departure_date", ""),
                context.get("return_date"),
                cabin=context.get("cabin_class", "ECONOMY"),
                adults=context.get("adults", 1),
                child=context.get("child", 0),
                infant=context.get("infant", 0),
            )
            initial = page_fetch_json(scraper, search_url)
            search_key = str(initial.get("key") or "").strip()
        if not search_key:
            logger.info("국제선 API search key를 찾지 못했습니다: %s", initial)
            _record_international_api_failure(scraper, "international_api_key_missing", initial)
            return []

        status_url = (
            f"{scraper_config.INTERPARK_AIR_API_BASE}/international/flights/search/v2/{search_key}/status"
        )
        max_polls = max(int(scraper_config.DATA_WAIT_TIMEOUT_SECONDS), 1)
        status_payload: Dict[str, Any] = {}

        for attempt in range(max_polls):
            status_payload = page_fetch_json(scraper, status_url)
            status_meta = get_api_meta(status_payload)
            if status_meta and not bool(status_meta.get("ok", True)):
                logger.info("국제선 API status HTTP 실패: %s", status_meta)
                _record_international_api_failure(scraper, "international_api_http_failed", status_payload)
                return []
            if str(status_payload.get("status") or "").upper() == "COMPLETE":
                break
            if status_payload.get("code"):
                logger.info("국제선 API status 실패: %s", status_payload)
                _record_international_api_failure(scraper, "international_api_status_failed", status_payload)
                return []
            if scraper.page:
                scraper.page.wait_for_timeout(1000)
            if attempt == max_polls - 1:
                logger.info("국제선 API status polling timeout: %s", search_key)
                _record_international_api_failure(scraper, "international_api_status_timeout", status_payload)
                return []

        payloads = _fetch_international_result_pages(scraper, search_key)
        if not payloads:
            _record_international_api_failure(scraper, "international_api_result_fetch_failed", {})
            return []

        items: List[Dict[str, Any]] = []
        fetched_pages = 0
        api_total_count = 0
        for payload in payloads:
            page_meta = payload.get("page")
            if isinstance(page_meta, dict):
                fetched_pages = max(fetched_pages, _coerce_int(page_meta.get("currentPage")))
                api_total_count = max(api_total_count, _coerce_int(page_meta.get("totalCount")))
            for bucket in ("bestFares", "contents"):
                value = payload.get(bucket)
                if isinstance(value, list):
                    items.extend(item for item in value if isinstance(item, dict))

        if not items:
            logger.info("국제선 API 결과 payload shape mismatch: %s", list(payloads[0].keys())[:10])
            _record_international_api_failure(scraper, "international_api_payload_mismatch", payloads[0])
            return []

        normalized: Dict[str, FlightResult] = {}
        for item in items:
            result = _normalize_international_api_item(item)
            if result is None:
                continue
            normalized[_result_unique_key(result)] = result
        scraper._search_metrics.update(
            {
                "api_total_count": api_total_count,
                "fetched_pages": fetched_pages,
                "api_item_count": len(normalized),
            }
        )
        return sorted(
            normalized.values(),
            key=lambda item: item.price if item.price > 0 else float("inf"),
        )
    except Exception as exc:
        logger.info("국제선 API 추출 예외: %s", exc)
        _record_international_api_failure(scraper, "international_api_exception", {"error": str(exc)})
        return []


def _extract_international_prices_from_dom(scraper: "PlaywrightScraper") -> List[FlightResult]:
    if not scraper.page:
        return []

    all_results_dict: Dict[str, Dict[str, Any]] = {}
    max_scrolls = scraper_config.INTERNATIONAL_MAX_SCROLLS
    pause_time = scraper_config.SCROLL_PAUSE_TIME
    logger.info("📜 점진적 추출 시작 (최대 %s회 스크롤)...", max_scrolls)
    seen_indices: set[int] = set()
    stalled_iterations = 0

    try:
        for index in range(max_scrolls):
            step_results = scraper.page.evaluate(ScraperScripts.get_international_prices_script())
            step_source = "international_primary"
            step_confidence = 0.9

            if not step_results and index == 0:
                fallback_results = scraper.page.evaluate(
                    ScraperScripts.get_international_prices_fallback_script()
                )
                if fallback_results:
                    logger.info("국제선 보조 스크립트로 재시도")
                    step_results = fallback_results
                    step_source = "international_fallback"
                    step_confidence = 0.6

            current_count = 0
            for item in step_results or []:
                item.setdefault("extraction_source", step_source)
                item.setdefault("confidence", step_confidence)
                unique_key = _browser_item_unique_key(item)
                if unique_key in all_results_dict:
                    continue
                all_results_dict[unique_key] = item
                current_count += 1

            current_indices = _read_current_result_indices(scraper)
            before_index_count = len(seen_indices)
            seen_indices.update(current_indices)
            new_index_count = len(seen_indices) - before_index_count

            logger.info(
                "🧭 스크롤 %s: 새 결과 %s개 추가 (총 %s개, index %s개)",
                index + 1,
                current_count,
                len(all_results_dict),
                len(seen_indices),
            )

            scroll_state = _advance_results_scroll(scraper)
            scraper.page.wait_for_timeout(pause_time * 1000)

            if current_count == 0 and new_index_count == 0:
                stalled_iterations += 1
            else:
                stalled_iterations = 0

            if (not scroll_state.get("advanced", False) and stalled_iterations >= 2) or stalled_iterations >= 4:
                logger.info("🧭 더 이상 새 콘텐츠가 로드되지 않습니다.")
                break
    except Exception as exc:
        logger.error("Extraction error: %s", exc, exc_info=True)

    if not all_results_dict and scraper.page:
        fallback_results = scraper.page.evaluate(ScraperScripts.get_international_prices_fallback_script())
        for item in fallback_results or []:
            item.setdefault("extraction_source", "international_fallback")
            item.setdefault("confidence", 0.6)
            all_results_dict[_browser_item_unique_key(item)] = item

    sorted_indices = sorted(seen_indices)
    dom_gap_detected = any(
        sorted_indices[idx] - sorted_indices[idx - 1] > 1
        for idx in range(1, len(sorted_indices))
    )
    scraper._search_metrics.update(
        {
            "dom_seen_indices": sorted_indices,
            "dom_gap_detected": dom_gap_detected,
        }
    )
    if dom_gap_detected:
        scraper._manual_reason = "dom_fallback_gap_risk"

    return _build_international_results(all_results_dict.values())


def _fetch_international_result_pages(
    scraper: "PlaywrightScraper",
    search_key: str,
) -> List[Dict[str, Any]]:
    result_url = (
        f"{scraper_config.INTERPARK_AIR_API_BASE}/international/flights/search/v2/{search_key}"
    )
    first_payload = page_fetch_json(
        scraper,
        result_url,
        method="POST",
        body={"pageNumber": 1, "pageSize": 20, "filter": {}},
    )
    if not isinstance(first_payload, dict):
        return []

    payloads = [first_payload]
    page_meta = first_payload.get("page")
    if not isinstance(page_meta, dict):
        return payloads

    total_count = _coerce_int(page_meta.get("totalCount"))
    page_size = max(_coerce_int(page_meta.get("pageSize")), 20)
    total_pages = max((total_count + page_size - 1) // page_size, 1)

    for page_number in range(2, total_pages + 1):
        payload = page_fetch_json(
            scraper,
            result_url,
            method="POST",
            body={"pageNumber": page_number, "pageSize": page_size, "filter": {}},
        )
        if not isinstance(payload, dict) or not payload:
            break
        payloads.append(payload)

    return payloads


def _record_international_api_failure(
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
    resources = recent_api_resource_urls(scraper, trip_kind="international")
    if resources:
        metrics["api_recent_resources"] = resources


def _read_current_result_indices(scraper: "PlaywrightScraper") -> List[int]:
    if not scraper.page:
        return []

    script = """
    () => Array.from(document.querySelectorAll('li[data-index], div[data-index]'))
        .map((node) => Number(node.getAttribute('data-index')))
        .filter((value) => Number.isFinite(value))
    """
    result = scraper.page.evaluate(script)
    if not isinstance(result, list):
        return []
    return sorted({int(item) for item in result if isinstance(item, (int, float))})


def _advance_results_scroll(scraper: "PlaywrightScraper") -> Dict[str, Any]:
    if not scraper.page:
        return {"advanced": False, "atEnd": True}

    script = """
    () => {
        const cards = Array.from(document.querySelectorAll('li[data-index], div[data-index]'));
        const candidates = Array.from(document.querySelectorAll('*'))
            .filter((el) => {
                const style = getComputedStyle(el);
                const overflowY = style.overflowY;
                return (
                    (overflowY === 'auto' || overflowY === 'scroll') &&
                    el.scrollHeight > el.clientHeight + 20 &&
                    cards.some((card) => el.contains(card))
                );
            })
            .sort((a, b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight));

        const target = candidates[0];
        if (target) {
            const maxTop = Math.max(0, target.scrollHeight - target.clientHeight);
            const beforeTop = target.scrollTop;
            const nextTop = Math.min(maxTop, beforeTop + Math.max(Math.floor(target.clientHeight * 0.8), 320));
            target.scrollTop = nextTop;
            target.dispatchEvent(new Event('scroll', { bubbles: true }));
            return {
                advanced: nextTop !== beforeTop,
                atEnd: nextTop >= maxTop,
                scrollTop: nextTop,
                maxTop,
                mode: 'container',
            };
        }

        const beforeY = window.scrollY;
        const maxY = Math.max(0, document.body.scrollHeight - window.innerHeight);
        const nextY = Math.min(maxY, beforeY + Math.max(Math.floor(window.innerHeight * 0.8), 320));
        window.scrollTo(0, nextY);
        return {
            advanced: nextY !== beforeY,
            atEnd: nextY >= maxY,
            scrollTop: nextY,
            maxTop: maxY,
            mode: 'window',
        };
    }
    """
    result = scraper.page.evaluate(script)
    return result if isinstance(result, dict) else {"advanced": False, "atEnd": True}


def _normalize_international_api_item(item: Dict[str, Any]) -> Optional[FlightResult]:
    schedules = item.get("schedules")
    if not isinstance(schedules, list) or not schedules:
        return None

    price = _coerce_int(item.get("adultPrice"))
    if price <= 0:
        fares = item.get("fares")
        if isinstance(fares, list):
            fare_prices = [_coerce_int(fare.get("adultPrice")) for fare in fares if isinstance(fare, dict)]
            fare_prices = [value for value in fare_prices if value > 0]
            price = min(fare_prices) if fare_prices else 0
    if price <= 0:
        return None

    outbound = schedules[0] if isinstance(schedules[0], dict) else None
    inbound = schedules[1] if len(schedules) > 1 and isinstance(schedules[1], dict) else None
    if outbound is None:
        return None

    dep_time, arr_time = _schedule_bounds(outbound)
    if not dep_time or not arr_time:
        return None

    airline = _schedule_airline(outbound) or "Unknown"
    is_round_trip = inbound is not None
    return_dep_time, return_arr_time = _schedule_bounds(inbound) if inbound else ("", "")
    return_airline = _schedule_airline(inbound) if inbound else ""
    if is_round_trip and not return_airline:
        return_airline = airline

    return FlightResult(
        airline=airline,
        return_airline=return_airline,
        price=price,
        departure_time=dep_time,
        arrival_time=arr_time,
        duration=_iso_duration_to_text(outbound.get("totalFlightTime")),
        stops=_coerce_int(outbound.get("stop")),
        source="Interpark (API)",
        return_departure_time=return_dep_time,
        return_arrival_time=return_arr_time,
        return_duration=_iso_duration_to_text(inbound.get("totalFlightTime")) if inbound else "",
        return_stops=_coerce_int(inbound.get("stop")) if inbound else 0,
        is_round_trip=is_round_trip,
        confidence=0.98,
        extraction_source="international_api",
    )


def _build_international_results(items: Iterable[Dict[str, Any]]) -> List[FlightResult]:
    results: List[FlightResult] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        airline = str(item.get("airline", "Unknown") or "Unknown")
        is_round_trip = bool(item.get("isRoundTrip", False))
        return_airline = str(item.get("returnAirline", "") or "")
        if is_round_trip and not return_airline:
            return_airline = airline
        price = _coerce_int(item.get("price"))
        departure_time = str(item.get("depTime", "") or "")
        arrival_time = str(item.get("arrTime", "") or "")
        if price <= 0 or not departure_time or not arrival_time:
            continue
        results.append(
            FlightResult(
                airline=airline,
                return_airline=return_airline,
                price=price,
                departure_time=departure_time,
                arrival_time=arrival_time,
                stops=_coerce_int(item.get("stops")),
                source="Interpark (Auto)",
                return_departure_time=str(item.get("retDepTime", "") or ""),
                return_arrival_time=str(item.get("retArrTime", "") or ""),
                return_stops=_coerce_int(item.get("retStops")),
                is_round_trip=is_round_trip,
                confidence=float(item.get("confidence", 0.9) or 0.9),
                extraction_source=str(
                    item.get("extraction_source", "international_primary") or "international_primary"
                ),
            )
        )
    return results


def _schedule_bounds(schedule: Optional[Dict[str, Any]]) -> tuple[str, str]:
    if not isinstance(schedule, dict):
        return "", ""

    segments = schedule.get("segments")
    if isinstance(segments, list) and segments:
        first = segments[0] if isinstance(segments[0], dict) else {}
        last = segments[-1] if isinstance(segments[-1], dict) else {}
        return _iso_timestamp_to_hhmm(_nested_get(first, "departure", "at")), _iso_timestamp_to_hhmm(
            _nested_get(last, "arrival", "at")
        )
    return "", ""


def _schedule_airline(schedule: Optional[Dict[str, Any]]) -> str:
    if not isinstance(schedule, dict):
        return ""

    carrier = schedule.get("carrier")
    if isinstance(carrier, dict) and carrier.get("name"):
        return str(carrier["name"])

    marketing = schedule.get("marketingCarriers")
    if isinstance(marketing, list):
        for item in marketing:
            if isinstance(item, dict) and item.get("name"):
                return str(item["name"])

    segments = schedule.get("segments")
    if isinstance(segments, list):
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            marketing_carrier = segment.get("marketingCarrier")
            if isinstance(marketing_carrier, dict) and marketing_carrier.get("name"):
                return str(marketing_carrier["name"])
    return ""


def _browser_item_unique_key(item: Dict[str, Any]) -> str:
    return "|".join(
        [
            str(item.get("airline", "") or ""),
            str(item.get("returnAirline", "") or ""),
            str(_coerce_int(item.get("price"))),
            str(item.get("depTime", "") or ""),
            str(item.get("arrTime", "") or ""),
            str(_coerce_int(item.get("stops"))),
            str(item.get("retDepTime", "") or ""),
            str(item.get("retArrTime", "") or ""),
            str(_coerce_int(item.get("retStops"))),
        ]
    )


def _result_unique_key(result: FlightResult) -> str:
    return "|".join(
        [
            result.airline,
            result.return_airline,
            str(result.price),
            result.departure_time,
            result.arrival_time,
            str(result.stops),
            result.return_departure_time,
            result.return_arrival_time,
            str(result.return_stops),
        ]
    )


def _iso_timestamp_to_hhmm(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) >= 16 and "T" in text:
        return text[11:16]
    return ""


def _iso_duration_to_text(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text.startswith("PT"):
        return ""

    hour_match = re.search(r"(\d+)H", text)
    minute_match = re.search(r"(\d+)M", text)
    hours = int(hour_match.group(1)) if hour_match else 0
    minutes = int(minute_match.group(1)) if minute_match else 0
    if hours and minutes:
        return f"{hours:02d}시간 {minutes:02d}분"
    if hours:
        return f"{hours:02d}시간"
    if minutes:
        return f"{minutes:02d}분"
    return ""


def _nested_get(value: Dict[str, Any], *keys: str) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _coerce_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
