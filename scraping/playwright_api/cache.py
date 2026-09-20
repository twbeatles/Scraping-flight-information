"""In-memory search-key cache (SRP: cache read/write only)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


def _ensure_search_key_cache(scraper: "PlaywrightScraper") -> Dict[str, List[str]]:
    cache = getattr(scraper, "_api_search_key_cache", None)
    if not isinstance(cache, dict):
        cache = {"domestic": [], "international": []}
        scraper._api_search_key_cache = cache
    return cache


def cache_search_key(scraper: "PlaywrightScraper", *, trip_kind: str, key: str) -> None:
    normalized = str(key or "").strip()
    if not normalized:
        return
    bucket = _ensure_search_key_cache(scraper).setdefault(trip_kind, [])
    if normalized not in bucket:
        bucket.append(normalized)


def get_cached_search_keys(scraper: "PlaywrightScraper", *, trip_kind: str) -> List[str]:
    cache = _ensure_search_key_cache(scraper)
    values = cache.get(trip_kind, [])
    return [str(item) for item in values if str(item).strip()]


def drop_cached_search_key(scraper: "PlaywrightScraper", *, trip_kind: str, key: str) -> None:
    """Remove one stale key from the in-memory cache (expiry handling)."""

    target = str(key or "").strip()
    if not target:
        return
    cache = _ensure_search_key_cache(scraper)
    bucket = cache.get(trip_kind)
    if isinstance(bucket, list):
        cache[trip_kind] = [item for item in bucket if str(item) != target]
