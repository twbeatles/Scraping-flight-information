"""Domestic API extraction path (package facade).

Split (SOLID/SRP) without breaking the public contract: every name
previously importable from `scraping.domestic.api` is re-exported here,
including the private helpers consumed by `scraping.domestic`.
"""

import scraping.interpark as scraper_config
from scraping.playwright_api import page_fetch_json, resolve_search_key, wait_for_search_key
from scraping.domestic.api.client import _fetch_domestic_search_page
from scraping.domestic.api.failures import (
    DOMESTIC_API_FAILURE_REASONS,
    _record_domestic_api_failure,
    clear_domestic_api_failure_after_success,
)
from scraping.domestic.api.key_refresh import (
    INVALID_CACHE_SEARCH_KEY,
    _is_invalid_cache_search_key,
    _refresh_domestic_search_key,
)
from scraping.domestic.api.normalize import (
    DOMESTIC_CARRIER_NAMES,
    _collect_result_items,
    _domestic_airport_code,
    _extract_domestic_benefit,
    _normalize_domestic_api_item,
)
from scraping.domestic.api.service import extract_domestic_api_flights_data

__all__ = [
    "DOMESTIC_API_FAILURE_REASONS",
    "DOMESTIC_CARRIER_NAMES",
    "INVALID_CACHE_SEARCH_KEY",
    "_collect_result_items",
    "_domestic_airport_code",
    "_extract_domestic_benefit",
    "_fetch_domestic_search_page",
    "_is_invalid_cache_search_key",
    "_normalize_domestic_api_item",
    "_record_domestic_api_failure",
    "_refresh_domestic_search_key",
    "clear_domestic_api_failure_after_success",
    "extract_domestic_api_flights_data",
    "page_fetch_json",
    "resolve_search_key",
    "scraper_config",
    "wait_for_search_key",
]
