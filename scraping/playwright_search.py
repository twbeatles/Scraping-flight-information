"""Backward-compatible facade for search flow helpers.

Prefer importing from `scraping.search_flow` for new code.
This module re-exports the same callables so older imports keep working.
"""

from __future__ import annotations

from typing import Callable

from scraping.playwright_api import find_latest_search_key, wait_for_search_key
from scraping.search_flow import (
    _activate_manual_mode_or_raise,
    _try_api_first_extraction,
    run_search,
)
from scraping.search_flow import domestic_flow as _domestic_flow


def _handle_domestic_round_trip(*args, **kwargs):
    """Proxy that rebinds key helpers so tests can monkeypatch this module."""

    original_find = _domestic_flow.find_latest_search_key
    original_wait = _domestic_flow.wait_for_search_key
    _domestic_flow.find_latest_search_key = find_latest_search_key
    _domestic_flow.wait_for_search_key = wait_for_search_key
    try:
        return _domestic_flow._handle_domestic_round_trip(*args, **kwargs)
    finally:
        _domestic_flow.find_latest_search_key = original_find
        _domestic_flow.wait_for_search_key = original_wait


__all__ = [
    "run_search",
    "_activate_manual_mode_or_raise",
    "_handle_domestic_round_trip",
    "_try_api_first_extraction",
    "find_latest_search_key",
    "wait_for_search_key",
]
