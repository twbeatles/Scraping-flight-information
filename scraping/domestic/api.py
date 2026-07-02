"""Domestic API extraction path."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

import scraping.interpark as scraper_config
from scraping.interpark.adapter import get_interpark_adapter
from scraping.playwright_api import (
    get_api_meta,
    page_fetch_json,
    recent_api_resource_urls,
    resolve_search_key,
)
from scraping.search_cancel import raise_if_search_cancelled
from scraping.domestic.helpers import _coerce_int, _iso_timestamp_to_hhmm

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")

DOMESTIC_API_FAILURE_REASONS = {
    "domestic_api_key_missing",
    "domestic_api_result_fetch_failed",
    "domestic_api_payload_mismatch",
    "domestic_api_failed",
}


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


def extract_domestic_api_flights_data(
    scraper: "PlaywrightScraper",
    *,
    search_key: str | None = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    if not scraper.page:
        return [], {"total_count": 0, "fetched_pages": 0}

    key = str(search_key or "").strip() or resolve_search_key(scraper, trip_kind="domestic")
    if not key:
        logger.info("국내선 API search key를 찾지 못했습니다.")
        _record_domestic_api_failure(scraper, "domestic_api_key_missing", {})
        return [], {"total_count": 0, "fetched_pages": 0}

    context = getattr(scraper, "_last_search_context", {}) or {}
    cabin = str(context.get("cabin_class", "ECONOMY") or "ECONOMY").upper()
    page_cap = max(int(getattr(scraper_config, "DOMESTIC_API_MAX_PAGES", 30)), 1)
    page_size = 20
    page_number = 1
    total_pages = 1
    total_pages_estimated = 1
    pages_truncated = False
    total_count = 0
    seen: Dict[str, Dict[str, Any]] = {}

    while page_number <= total_pages:
        raise_if_search_cancelled(scraper)
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
            total_pages_estimated = max((total_count + page_size - 1) // page_size, page_number)
            pages_truncated = total_pages_estimated > page_cap
            total_pages = min(total_pages_estimated, page_cap)

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


def _fetch_domestic_search_page(
    scraper: "PlaywrightScraper",
    search_key: str,
    *,
    page_number: int,
    page_size: int,
    cabin: str,
) -> Dict[str, Any]:
    adapter = get_interpark_adapter()
    url = f"{adapter.air_api_base}{adapter.domestic_search_api_path}{search_key}"
    payload = page_fetch_json(
        scraper,
        url,
        method="POST",
        body={
            "pageNumber": page_number,
            "pageSize": page_size,
            "filter": {
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
    if isinstance(payload, dict):
        if payload.get("code"):
            metrics["api_failure_code"] = str(payload.get("code"))
        if payload.get("message") or payload.get("title"):
            metrics["api_failure_message"] = str(payload.get("message") or payload.get("title"))
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
