"""Domestic API extraction path."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

import scraping.interpark as scraper_config
from scraping.interpark.adapter import get_interpark_adapter
from scraping.interpark.contract.carriers import DOMESTIC_CARRIER_CODE_TO_NAME
from scraping.playwright_api import (
    get_api_meta,
    page_fetch_json,
    recent_api_resource_urls,
    resolve_search_key,
    wait_for_search_key,
)
from scraping.search_cancel import raise_if_search_cancelled
from scraping.domestic.helpers import _coerce_int, _iso_timestamp_to_hhmm

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")

DOMESTIC_API_FAILURE_REASONS = {
    "domestic_api_key_missing",
    "domestic_api_key_timeout",
    "domestic_api_key_expired",
    "domestic_api_result_fetch_failed",
    "domestic_api_payload_mismatch",
    "domestic_api_failed",
}

INVALID_CACHE_SEARCH_KEY = "INVALID_CACHE_SEARCH_KEY"

# Backward-compatible alias for existing imports/tests.
DOMESTIC_CARRIER_NAMES = DOMESTIC_CARRIER_CODE_TO_NAME


def extract_domestic_api_flights_data(
    scraper: "PlaywrightScraper",
    *,
    search_key: str | None = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    if not scraper.page:
        return [], {"total_count": 0, "fetched_pages": 0}

    adapter = get_interpark_adapter()
    key = str(search_key or "").strip() or resolve_search_key(scraper, trip_kind="domestic")
    waited_for_key = False
    if not key:
        waited_for_key = True
        key = wait_for_search_key(scraper, trip_kind="domestic")
    if not key:
        reason = "domestic_api_key_timeout" if waited_for_key else "domestic_api_key_missing"
        # Stubs without wait capability still surface the historical missing reason.
        page = getattr(scraper, "page", None)
        if waited_for_key and not (page is not None and hasattr(page, "wait_for_timeout")):
            reason = "domestic_api_key_missing"
        logger.info("국내선 API search key를 찾지 못했습니다 (%s).", reason)
        _record_domestic_api_failure(scraper, reason, {})
        return [], {"total_count": 0, "fetched_pages": 0}

    context = getattr(scraper, "_last_search_context", {}) or {}
    cabin = str(context.get("cabin_class", "ECONOMY") or "ECONOMY").upper()
    page_cap = max(int(getattr(scraper_config, "DOMESTIC_API_MAX_PAGES", 30)), 1)
    page_size = max(int(adapter.default_api_page_size), 1)
    page_number = 1
    total_pages = 1
    total_pages_estimated = 1
    pages_truncated = False
    total_count = 0
    seen: Dict[str, Dict[str, Any]] = {}
    key_retry_used = False

    while page_number <= total_pages:
        raise_if_search_cancelled(scraper)
        payload = _fetch_domestic_search_page(
            scraper,
            key,
            page_number=page_number,
            page_size=page_size,
            cabin=cabin,
        )
        if not payload:
            _record_domestic_api_failure(scraper, "domestic_api_result_fetch_failed", {})
            break

        if _is_invalid_cache_search_key(payload):
            if page_number == 1 and not key_retry_used:
                logger.info("국내선 search key 만료 감지 — 새 키로 1회 재시도")
                key_retry_used = True
                refreshed = _refresh_domestic_search_key(scraper, expired_key=key)
                metrics = getattr(scraper, "_search_metrics", None)
                if isinstance(metrics, dict):
                    metrics["api_key_retry_count"] = int(metrics.get("api_key_retry_count", 0) or 0) + 1
                if refreshed:
                    key = refreshed
                    continue
                _record_domestic_api_failure(scraper, "domestic_api_key_expired", payload)
                break
            _record_domestic_api_failure(scraper, "domestic_api_key_expired", payload)
            break

        page_meta = payload.get(adapter.page_meta_key)
        if not isinstance(page_meta, dict):
            _record_domestic_api_failure(scraper, "domestic_api_payload_mismatch", payload)
            break

        page_size = max(_coerce_int(page_meta.get(adapter.page_size_field)), page_size)
        total_count = max(total_count, _coerce_int(page_meta.get(adapter.page_total_count_field)))
        total_pages_estimated = max((total_count + page_size - 1) // page_size, page_number)
        pages_truncated = total_pages_estimated > page_cap
        total_pages = min(total_pages_estimated, page_cap)

        items = _collect_result_items(payload, adapter.domestic_result_buckets)
        if not items:
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
            "page_cap": page_cap,
            "pages_truncated": pages_truncated,
            "total_pages_estimated": total_pages_estimated,
        },
    )


def clear_domestic_api_failure_after_success(scraper: "PlaywrightScraper") -> None:
    """Move stale domestic API failure state out of the final search status."""

    metrics = getattr(scraper, "_search_metrics", None)
    stale_reason = ""
    if isinstance(metrics, dict):
        stale_reason = str(metrics.pop("api_failure_reason", "") or "")
        if stale_reason:
            metrics.setdefault("prewait_api_failure_reason", stale_reason)
        for key in (
            "api_failure_payload_keys",
            "api_failure_code",
            "api_failure_message",
            "api_failure_meta",
            "api_recent_resources",
        ):
            if key in metrics:
                metrics[f"prewait_{key}"] = metrics.pop(key)

    manual_reason = str(getattr(scraper, "_manual_reason", "") or "")
    if manual_reason in DOMESTIC_API_FAILURE_REASONS or manual_reason == stale_reason:
        scraper._manual_reason = ""


def _is_invalid_cache_search_key(payload: Dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        return False
    adapter = get_interpark_adapter()
    code = str(payload.get(adapter.error_code_field) or "").strip().upper()
    if code == INVALID_CACHE_SEARCH_KEY:
        return True
    message = " ".join(
        str(payload.get(field) or "")
        for field in adapter.error_message_fields
    )
    return "조회시간이 경과" in message or "INVALID_CACHE_SEARCH_KEY" in message.upper()


def _refresh_domestic_search_key(scraper: "PlaywrightScraper", *, expired_key: str) -> str:
    """Try to obtain a fresher domestic search key after expiry.

    Strategy:
    1. Wait briefly for a *new* key (excluding the expired one).
    2. If none arrives, soft-reload the current search URL so the page issues
       a new search-key request, then wait again.
    """
    exclude = {str(expired_key).strip()} if expired_key else set()
    wait_seconds = float(
        getattr(scraper_config, "SEARCH_KEY_RETURN_WAIT_TIMEOUT_SECONDS", 10.0)
    )

    fresh = wait_for_search_key(
        scraper,
        trip_kind="domestic",
        timeout_seconds=min(wait_seconds, 4.0),
        exclude_keys=exclude,
    )
    if fresh and fresh not in exclude:
        return fresh

    page = getattr(scraper, "page", None)
    if page is not None and hasattr(page, "reload"):
        try:
            # Drop the expired key from in-memory cache so we do not reuse it.
            cache = getattr(scraper, "_api_search_key_cache", None)
            if isinstance(cache, dict):
                bucket = cache.get("domestic")
                if isinstance(bucket, list):
                    cache["domestic"] = [item for item in bucket if str(item) not in exclude]
            page.reload(wait_until="domcontentloaded", timeout=scraper_config.PAGE_LOAD_TIMEOUT_MS)
            metrics = getattr(scraper, "_search_metrics", None)
            if isinstance(metrics, dict):
                metrics["api_key_reload_attempted"] = True
        except Exception as exc:
            logger.info("국내선 key 갱신을 위한 soft reload 실패: %s", exc)

    fresh = wait_for_search_key(
        scraper,
        trip_kind="domestic",
        timeout_seconds=wait_seconds,
        exclude_keys=exclude,
    )
    if fresh and fresh not in exclude:
        return fresh
    latest = resolve_search_key(scraper, trip_kind="domestic", exclude_keys=exclude)
    return latest if latest and latest not in exclude else ""


def _collect_result_items(
    payload: Dict[str, Any],
    buckets: tuple[str, ...],
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for bucket in buckets:
        value = payload.get(bucket)
        if isinstance(value, list):
            items.extend(item for item in value if isinstance(item, dict))
    return items


def _fetch_domestic_search_page(
    scraper: "PlaywrightScraper",
    search_key: str,
    *,
    page_number: int,
    page_size: int,
    cabin: str,
) -> Dict[str, Any]:
    adapter = get_interpark_adapter()
    url = adapter.build_domestic_result_url(search_key)
    payload = page_fetch_json(
        scraper,
        url,
        method="POST",
        body=adapter.domestic_result_request_body(
            page_number=page_number,
            page_size=page_size,
            cabin=cabin,
        ),
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
    adapter = get_interpark_adapter()
    meta = get_api_meta(payload) if isinstance(payload, dict) else {}
    metrics["api_failure_reason"] = reason
    metrics["api_failure_payload_keys"] = list(payload.keys())[:20] if isinstance(payload, dict) else []
    if isinstance(payload, dict):
        code = payload.get(adapter.error_code_field)
        if code:
            metrics["api_failure_code"] = str(code)
        for message_field in adapter.error_message_fields:
            message = payload.get(message_field)
            if message:
                metrics["api_failure_message"] = str(message)
                break
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
    airline = DOMESTIC_CARRIER_CODE_TO_NAME.get(carrier_code, carrier_code or "Unknown")
    flight_number = str(schedule.get("flightNumber", "") or "")
    key = str(item.get("key") or item.get("id") or f"{carrier_code}_{dep_time}_{arr_time}_{best_price}")
    dep_airport = _domestic_airport_code(
        schedule,
        ("departureAirport", "originAirport", "departureAirportCode", "origin", "departure"),
        nested_keys=(("departure", "airport", "code"), ("departure", "code")),
    )
    arr_airport = _domestic_airport_code(
        schedule,
        ("arrivalAirport", "destinationAirport", "arrivalAirportCode", "destination", "arrival"),
        nested_keys=(("arrival", "airport", "code"), ("arrival", "code")),
    )

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
        "depAirport": dep_airport,
        "arrAirport": arr_airport,
        "duration": str(schedule.get("duration") or schedule.get("flightTime") or ""),
    }


def _domestic_airport_code(
    schedule: Dict[str, Any],
    flat_keys: tuple[str, ...],
    *,
    nested_keys: tuple[tuple[str, ...], ...] = (),
) -> str:
    for key in flat_keys:
        value = schedule.get(key)
        if isinstance(value, dict):
            code = str(value.get("code") or value.get("airportCode") or "").strip().upper()
        else:
            code = str(value or "").strip().upper()
        if len(code) == 3 and code.isalpha():
            return code
    for path in nested_keys:
        current: Any = schedule
        for part in path:
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(part)
        code = str(current or "").strip().upper()
        if len(code) == 3 and code.isalpha():
            return code
    return ""


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
