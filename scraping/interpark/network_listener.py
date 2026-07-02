"""Playwright response listener for Interpark search-key capture."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Set

from scraping.interpark.adapter import InterparkAdapterConfig, get_interpark_adapter
from scraping.playwright_api import (
    cache_search_key,
    extract_search_key_from_payload,
    extract_search_key_from_url,
)

if TYPE_CHECKING:
    from playwright.sync_api import Page, Response

    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")


def _listener_pages(scraper: "PlaywrightScraper") -> Set[int]:
    pages = getattr(scraper, "_network_listener_page_ids", None)
    if not isinstance(pages, set):
        pages = set()
        scraper._network_listener_page_ids = pages
    return pages


def attach_interpark_response_listener(
    scraper: "PlaywrightScraper",
    page: "Page",
    *,
    adapter: InterparkAdapterConfig | None = None,
) -> None:
    """Attach a response listener that caches Interpark search keys from network traffic."""

    if page is None:
        return

    page_id = id(page)
    if page_id in _listener_pages(scraper):
        return

    config = adapter or get_interpark_adapter()

    def _on_response(response: "Response") -> None:
        try:
            _capture_search_key_from_response(scraper, response, config)
        except Exception as exc:
            logger.debug("Interpark response listener skipped: %s", exc)

    page.on("response", _on_response)
    _listener_pages(scraper).add(page_id)


def _capture_search_key_from_response(
    scraper: "PlaywrightScraper",
    response: "Response",
    adapter: InterparkAdapterConfig,
) -> None:
    url = str(getattr(response, "url", "") or "")
    if not url:
        return

    trip_kind, key = extract_search_key_from_url(url, adapter=adapter)
    if trip_kind and key:
        cache_search_key(scraper, trip_kind=trip_kind, key=key)
        _record_key_source(scraper, trip_kind, "network_url")
        return

    if not bool(getattr(response, "ok", False)):
        return

    content_type = str(response.headers.get("content-type", "") or "").lower()
    if "json" not in content_type:
        return

    if not _is_search_api_url(url, adapter):
        return

    try:
        payload = response.json()
    except Exception:
        return

    if not isinstance(payload, dict):
        return

    payload_key = extract_search_key_from_payload(payload)
    if not payload_key:
        return

    inferred_kind = _infer_trip_kind(url, payload_key, adapter)
    cache_search_key(scraper, trip_kind=inferred_kind, key=payload_key)
    _record_key_source(scraper, inferred_kind, "network_json")


def _is_search_api_url(url: str, adapter: InterparkAdapterConfig) -> bool:
    return any(
        fragment in url
        for fragment in (
            adapter.domestic_search_api_path,
            adapter.international_search_api_path,
            adapter.international_initial_search_api_path,
        )
    )


def _infer_trip_kind(url: str, key: str, adapter: InterparkAdapterConfig) -> str:
    if adapter.domestic_search_api_path in url or key.startswith(adapter.domestic_key_prefix):
        return "domestic"
    return "international"


def _record_key_source(scraper: "PlaywrightScraper", trip_kind: str, source: str) -> None:
    metrics = getattr(scraper, "_search_metrics", None)
    if not isinstance(metrics, dict):
        return
    bucket = metrics.setdefault("api_key_sources", {})
    if isinstance(bucket, dict):
        bucket[trip_kind] = source