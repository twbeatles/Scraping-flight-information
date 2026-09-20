"""Domestic API pagination orchestration (SRP: page-loop only)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

import scraping.interpark as scraper_config
from scraping.domestic.api.failures import _record_domestic_api_failure
from scraping.domestic.api.key_refresh import _is_invalid_cache_search_key, _refresh_domestic_search_key
from scraping.domestic.api.normalize import _collect_result_items, _normalize_domestic_api_item
from scraping.domestic.helpers import _coerce_int
from scraping.interpark.adapter import get_interpark_adapter
from scraping.search_cancel import raise_if_search_cancelled

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")


def _api_package():
    """Return the `scraping.domestic.api` facade for monkeypatch-compatible lookups.

    Tests patch collaborators (key resolution, page fetch) on the facade
    namespace; resolving them here at call time keeps those seams working
    after the module -> package split.
    """

    from scraping.domestic import api as api_package

    return api_package


def extract_domestic_api_flights_data(
    scraper: "PlaywrightScraper",
    *,
    search_key: str | None = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    if not scraper.page:
        return [], {"total_count": 0, "fetched_pages": 0}

    adapter = get_interpark_adapter()
    api = _api_package()
    key = str(search_key or "").strip() or api.resolve_search_key(scraper, trip_kind="domestic")
    waited_for_key = False
    if not key:
        waited_for_key = True
        key = api.wait_for_search_key(scraper, trip_kind="domestic")
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
        payload = api._fetch_domestic_search_page(
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
