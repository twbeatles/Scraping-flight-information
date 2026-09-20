"""Domestic search-key expiry handling (SRP: key refresh only)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict

import scraping.interpark as scraper_config
from scraping.interpark.adapter import get_interpark_adapter
from scraping.playwright_api import drop_cached_search_key

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")

INVALID_CACHE_SEARCH_KEY = "INVALID_CACHE_SEARCH_KEY"


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
    from scraping.domestic import api as api_package

    exclude = {str(expired_key).strip()} if expired_key else set()
    wait_seconds = float(
        getattr(scraper_config, "SEARCH_KEY_RETURN_WAIT_TIMEOUT_SECONDS", 10.0)
    )

    fresh = api_package.wait_for_search_key(
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
            if expired_key:
                drop_cached_search_key(scraper, trip_kind="domestic", key=expired_key)
            page.reload(wait_until="domcontentloaded", timeout=scraper_config.PAGE_LOAD_TIMEOUT_MS)
            metrics = getattr(scraper, "_search_metrics", None)
            if isinstance(metrics, dict):
                metrics["api_key_reload_attempted"] = True
        except Exception as exc:
            logger.info("국내선 key 갱신을 위한 soft reload 실패: %s", exc)

    fresh = api_package.wait_for_search_key(
        scraper,
        trip_kind="domestic",
        timeout_seconds=wait_seconds,
        exclude_keys=exclude,
    )
    if fresh and fresh not in exclude:
        return fresh
    latest = api_package.resolve_search_key(scraper, trip_kind="domestic", exclude_keys=exclude)
    return latest if latest and latest not in exclude else ""
