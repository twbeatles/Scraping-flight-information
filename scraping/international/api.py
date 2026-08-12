"""International API extraction path."""

import logging
from typing import TYPE_CHECKING, Any, Dict, List

import scraping.interpark as scraper_config
from scraping.interpark.adapter import get_interpark_adapter
from scraping.models import FlightResult
from scraping.playwright_api import (
    cache_search_key,
    extract_search_key_from_payload,
    get_api_meta,
    page_fetch_json,
    recent_api_resource_urls,
    resolve_search_key,
)
from scraping.search_cancel import raise_if_search_cancelled
from scraping.international.helpers import _coerce_int, _result_unique_key
from scraping.international.normalizer import _normalize_international_api_item

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")


def _extract_international_prices_via_api(scraper: "PlaywrightScraper") -> List[FlightResult]:
    try:
        context = getattr(scraper, "_last_search_context", {}) or {}
        if not context or context.get("is_domestic"):
            return []

        adapter = get_interpark_adapter()
        search_key = resolve_search_key(scraper, trip_kind="international")
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
            search_key = extract_search_key_from_payload(initial)
            if search_key:
                cache_search_key(scraper, trip_kind="international", key=search_key)
        if not search_key:
            logger.info("국제선 API search key를 찾지 못했습니다: %s", initial)
            _record_international_api_failure(scraper, "international_api_key_missing", initial)
            return []

        status_url = adapter.build_international_status_url(search_key)
        max_polls = max(
            int(getattr(scraper_config, "INTERNATIONAL_STATUS_MAX_POLLS", 60)),
            1,
        )
        poll_initial_ms = max(
            int(getattr(scraper_config, "INTERNATIONAL_STATUS_POLL_INITIAL_MS", 1000)),
            250,
        )
        poll_max_ms = max(
            int(getattr(scraper_config, "INTERNATIONAL_STATUS_POLL_MAX_MS", 2000)),
            poll_initial_ms,
        )
        status_payload: Dict[str, Any] = {}
        complete_value = str(adapter.status_complete_value or "COMPLETE").upper()

        for attempt in range(max_polls):
            raise_if_search_cancelled(scraper)
            status_payload = page_fetch_json(scraper, status_url)
            status_meta = get_api_meta(status_payload)
            if status_meta and not bool(status_meta.get("ok", True)):
                logger.info("국제선 API status HTTP 실패: %s", status_meta)
                _record_international_api_failure(scraper, "international_api_http_failed", status_payload)
                return []
            if str(status_payload.get(adapter.status_field) or "").upper() == complete_value:
                if isinstance(getattr(scraper, "_search_metrics", None), dict):
                    scraper._search_metrics["api_status_poll_attempts"] = attempt + 1
                break
            if status_payload.get(adapter.error_code_field):
                logger.info("국제선 API status 실패: %s", status_payload)
                _record_international_api_failure(scraper, "international_api_status_failed", status_payload)
                return []
            if scraper.page:
                wait_ms = min(poll_initial_ms * (attempt // 5 + 1), poll_max_ms)
                scraper.page.wait_for_timeout(wait_ms)
            if attempt == max_polls - 1:
                logger.info("국제선 API status polling timeout: %s", search_key)
                if isinstance(getattr(scraper, "_search_metrics", None), dict):
                    scraper._search_metrics["api_status_poll_attempts"] = attempt + 1
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
            page_meta = payload.get(adapter.page_meta_key)
            if isinstance(page_meta, dict):
                fetched_pages = max(
                    fetched_pages,
                    _coerce_int(page_meta.get(adapter.page_current_field)),
                )
                api_total_count = max(
                    api_total_count,
                    _coerce_int(page_meta.get(adapter.page_total_count_field)),
                )
            for bucket in adapter.international_result_buckets:
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
                "api_fetched_pages": fetched_pages,
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


def _fetch_international_result_pages(
    scraper: "PlaywrightScraper",
    search_key: str,
) -> List[Dict[str, Any]]:
    adapter = get_interpark_adapter()
    result_url = adapter.build_international_result_url(search_key)
    default_page_size = max(int(adapter.default_api_page_size), 1)
    first_payload = page_fetch_json(
        scraper,
        result_url,
        method="POST",
        body=adapter.international_result_request_body(
            page_number=1,
            page_size=default_page_size,
        ),
    )
    if not isinstance(first_payload, dict):
        return []

    payloads = [first_payload]
    page_meta = first_payload.get(adapter.page_meta_key)
    if not isinstance(page_meta, dict):
        _record_international_pagination_metrics(scraper, fetched_pages=1, total_pages=1, page_cap=1)
        return payloads

    total_count = _coerce_int(page_meta.get(adapter.page_total_count_field))
    page_size = max(_coerce_int(page_meta.get(adapter.page_size_field)), default_page_size)
    total_pages = max((total_count + page_size - 1) // page_size, 1)
    page_cap = max(int(getattr(scraper_config, "INTERNATIONAL_API_MAX_PAGES", 50)), 1)
    limited_total_pages = min(total_pages, page_cap)

    for page_number in range(2, limited_total_pages + 1):
        raise_if_search_cancelled(scraper)
        payload = page_fetch_json(
            scraper,
            result_url,
            method="POST",
            body=adapter.international_result_request_body(
                page_number=page_number,
                page_size=page_size,
            ),
        )
        if not isinstance(payload, dict) or not payload:
            break
        payloads.append(payload)

    _record_international_pagination_metrics(
        scraper,
        fetched_pages=len(payloads),
        total_pages=total_pages,
        page_cap=page_cap,
    )
    return payloads


def _record_international_pagination_metrics(
    scraper: "PlaywrightScraper",
    *,
    fetched_pages: int,
    total_pages: int,
    page_cap: int,
) -> None:
    metrics = getattr(scraper, "_search_metrics", None)
    if not isinstance(metrics, dict):
        return
    metrics.update(
        {
            "api_page_cap": page_cap,
            "api_pages_truncated": total_pages > page_cap,
            "api_total_pages_estimated": total_pages,
            "api_fetched_pages": fetched_pages,
        }
    )


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
    resources = recent_api_resource_urls(scraper, trip_kind="international")
    if resources:
        metrics["api_recent_resources"] = resources
