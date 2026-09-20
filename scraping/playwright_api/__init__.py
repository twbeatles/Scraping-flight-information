"""Shared Playwright page/API helpers (package facade).

Split (SOLID/SRP) without breaking the public contract: every name
previously importable from `scraping.playwright_api` stays importable here.

The facade resolves names lazily (PEP 562) instead of importing every
submodule up front. This keeps a pre-existing import cycle harmless:
`scraping.interpark.__init__` imports `network_listener`, which imports
names from this package, while this package's submodules import
`scraping.interpark.adapter`. Eager imports made the outcome depend on
which side was imported first; lazy resolution works in either order.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from scraping.playwright_api.cache import (
        _ensure_search_key_cache,
        cache_search_key,
        drop_cached_search_key,
        get_cached_search_keys,
    )
    from scraping.playwright_api.fetch import _maybe_cache_search_key_from_fetch, page_fetch_json
    from scraping.playwright_api.keys import (
        _normalize_exclude_keys,
        _record_key_wait,
        extract_search_key_from_payload,
        extract_search_key_from_url,
        find_latest_search_key,
        find_search_keys,
        find_search_keys_from_performance,
        resolve_search_key,
        wait_for_search_key,
    )
    from scraping.playwright_api.meta import _record_api_meta, _sanitize_resource_url, get_api_meta
    from scraping.playwright_api.resources import recent_api_resource_urls

_SUBMODULE_BY_NAME = {
    "page_fetch_json": "fetch",
    "_maybe_cache_search_key_from_fetch": "fetch",
    "get_api_meta": "meta",
    "_record_api_meta": "meta",
    "_sanitize_resource_url": "meta",
    "_ensure_search_key_cache": "cache",
    "cache_search_key": "cache",
    "drop_cached_search_key": "cache",
    "get_cached_search_keys": "cache",
    "extract_search_key_from_url": "keys",
    "extract_search_key_from_payload": "keys",
    "find_search_keys": "keys",
    "find_search_keys_from_performance": "keys",
    "resolve_search_key": "keys",
    "wait_for_search_key": "keys",
    "find_latest_search_key": "keys",
    "_normalize_exclude_keys": "keys",
    "_record_key_wait": "keys",
    "recent_api_resource_urls": "resources",
}

__all__ = [
    "_ensure_search_key_cache",
    "_maybe_cache_search_key_from_fetch",
    "_normalize_exclude_keys",
    "_record_api_meta",
    "_record_key_wait",
    "_sanitize_resource_url",
    "cache_search_key",
    "drop_cached_search_key",
    "extract_search_key_from_payload",
    "extract_search_key_from_url",
    "find_latest_search_key",
    "find_search_keys",
    "find_search_keys_from_performance",
    "get_api_meta",
    "get_cached_search_keys",
    "page_fetch_json",
    "recent_api_resource_urls",
    "resolve_search_key",
    "wait_for_search_key",
]


def __getattr__(name: str) -> Any:
    target = _SUBMODULE_BY_NAME.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    module = importlib.import_module(f"{__name__}.{target}")
    return getattr(module, name)


def __dir__() -> list[str]:
    return sorted(__all__)
