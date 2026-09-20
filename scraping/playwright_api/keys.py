"""Search-key discovery and waiting (SRP: key resolve/wait only)."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Set, Tuple

from scraping.interpark.adapter import InterparkAdapterConfig, get_interpark_adapter
from scraping.interpark import runtime as interpark_runtime
from scraping.playwright_api.cache import get_cached_search_keys

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


def extract_search_key_from_url(
    url: str,
    *,
    adapter: InterparkAdapterConfig | None = None,
) -> Tuple[str, str]:
    """Return `(trip_kind, key)` parsed from an Interpark API URL."""

    config = adapter or get_interpark_adapter()
    text = str(url or "")
    if not text:
        return "", ""

    for trip_kind, prefix, path in (
        ("domestic", config.domestic_key_prefix, config.domestic_search_api_path),
        ("international", config.international_key_prefix, config.international_search_api_path),
    ):
        if prefix in text:
            start = text.index(prefix)
            token = text[start:].split("/")[0].split("?")[0]
            if token:
                return trip_kind, token
        if path in text:
            tail = text.split(path, 1)[-1]
            token = tail.split("/")[0].split("?")[0]
            if token.startswith(prefix):
                return trip_kind, token
    return "", ""


def extract_search_key_from_payload(payload: Dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        return ""
    adapter = get_interpark_adapter()
    for field in adapter.search_key_fields:
        value = str(payload.get(field) or "").strip()
        if value:
            return value
    return ""


def find_search_keys(
    scraper: "PlaywrightScraper",
    *,
    trip_kind: str,
) -> List[str]:
    """Return search keys from cache and performance resources in stable order."""

    keys: List[str] = []
    for cached in get_cached_search_keys(scraper, trip_kind=trip_kind):
        if cached not in keys:
            keys.append(cached)
    for discovered in find_search_keys_from_performance(scraper, trip_kind=trip_kind):
        if discovered not in keys:
            keys.append(discovered)
    return keys


def find_search_keys_from_performance(
    scraper: "PlaywrightScraper",
    *,
    trip_kind: str,
) -> List[str]:
    """Return seen search keys from resource timing entries in order of first appearance."""

    if not scraper.page:
        return []

    adapter = get_interpark_adapter()
    prefix = adapter.domestic_key_prefix if trip_kind == "domestic" else adapter.international_key_prefix
    pattern = (
        adapter.domestic_search_api_path
        if trip_kind == "domestic"
        else adapter.international_search_api_path
    )
    script = f"""
    () => {{
        const resources = performance.getEntriesByType('resource')
            .map((entry) => String(entry.name || ''))
            .filter((name) => name.includes({json.dumps(pattern)}));
        const seen = [];
        for (const name of resources) {{
            const start = name.indexOf({json.dumps(prefix)});
            if (start < 0) continue;
            const tail = name.slice(start);
            const key = tail.split(/[/?#]/)[0];
            if (!seen.includes(key)) {{
                seen.push(key);
            }}
        }}
        return seen;
    }}
    """
    try:
        result = scraper.page.evaluate(script)
    except Exception:
        return []
    if not isinstance(result, list):
        return []
    return [str(item) for item in result if str(item).strip()]


def resolve_search_key(
    scraper: "PlaywrightScraper",
    *,
    trip_kind: str,
    explicit_key: str | None = None,
    exclude_keys: Iterable[str] | None = None,
) -> str:
    explicit = str(explicit_key or "").strip()
    if explicit:
        return explicit
    excluded = _normalize_exclude_keys(exclude_keys)
    keys = find_search_keys(scraper, trip_kind=trip_kind)
    for key in reversed(keys):
        if key and key not in excluded:
            return key
    return ""


def wait_for_search_key(
    scraper: "PlaywrightScraper",
    *,
    trip_kind: str,
    timeout_seconds: float | None = None,
    poll_ms: int | None = None,
    exclude_keys: Iterable[str] | None = None,
) -> str:
    """Poll network/performance caches until a usable search key appears.

    When the scraper has no real Playwright page (unit tests with stubs), this
    performs a single resolve pass and returns immediately.
    """

    timeout = float(
        timeout_seconds
        if timeout_seconds is not None
        else getattr(interpark_runtime, "SEARCH_KEY_WAIT_TIMEOUT_SECONDS", 12.0)
    )
    poll = max(
        int(
            poll_ms
            if poll_ms is not None
            else getattr(interpark_runtime, "SEARCH_KEY_WAIT_POLL_MS", 250)
        ),
        50,
    )
    excluded = _normalize_exclude_keys(exclude_keys)
    deadline = time.monotonic() + max(timeout, 0.0)

    while True:
        key = resolve_search_key(scraper, trip_kind=trip_kind, exclude_keys=excluded)
        if key:
            _record_key_wait(scraper, trip_kind=trip_kind, source="key_wait")
            return key

        page = getattr(scraper, "page", None)
        can_wait = page is not None and hasattr(page, "wait_for_timeout")
        if not can_wait or time.monotonic() >= deadline:
            return ""

        try:
            wait_for_timeout = getattr(page, "wait_for_timeout", None)
            if not callable(wait_for_timeout):
                return ""
            wait_for_timeout(poll)
        except Exception:
            return ""


def find_latest_search_key(
    scraper: "PlaywrightScraper",
    *,
    trip_kind: str,
    exclude_keys: Iterable[str] | None = None,
) -> str:
    return resolve_search_key(scraper, trip_kind=trip_kind, exclude_keys=exclude_keys)


def _normalize_exclude_keys(exclude_keys: Iterable[str] | None) -> Set[str]:
    if not exclude_keys:
        return set()
    return {str(item).strip() for item in exclude_keys if str(item or "").strip()}


def _record_key_wait(scraper: "PlaywrightScraper", *, trip_kind: str, source: str) -> None:
    metrics = getattr(scraper, "_search_metrics", None)
    if not isinstance(metrics, dict):
        return
    bucket = metrics.setdefault("api_key_sources", {})
    if isinstance(bucket, dict):
        bucket[trip_kind] = source
