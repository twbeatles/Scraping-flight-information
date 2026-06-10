"""Backward-compatible facade for search flow helpers."""

from __future__ import annotations

from typing import Callable

from scraping.playwright_api import find_latest_search_key
from scraping.search_flow import (
    _activate_manual_mode_or_raise,
    _try_api_first_extraction,
    run_search,
)
from scraping.search_flow import domestic_flow as _domestic_flow


def _handle_domestic_round_trip(*args, **kwargs):
    original = _domestic_flow.find_latest_search_key
    _domestic_flow.find_latest_search_key = find_latest_search_key
    try:
        return _domestic_flow._handle_domestic_round_trip(*args, **kwargs)
    finally:
        _domestic_flow.find_latest_search_key = original


__all__ = [
    "run_search",
    "_activate_manual_mode_or_raise",
    "_handle_domestic_round_trip",
    "_try_api_first_extraction",
    "find_latest_search_key",
]
