"""Backward-compatible facade for domestic result helpers."""

from scraping.domestic import (
    _coerce_int,
    _combine_benefit_labels,
    _extract_domestic_benefit,
    _fetch_domestic_search_page,
    _iso_timestamp_to_hhmm,
    _normalize_domestic_api_item,
    _record_domestic_api_failure,
    build_domestic_results,
    combine_domestic_round_trip,
    extract_domestic_api_flights_data,
    extract_domestic_dom_flights_data,
    extract_domestic_flights_data,
    extract_domestic_prices,
)

__all__ = [
    "combine_domestic_round_trip",
    "extract_domestic_flights_data",
    "extract_domestic_api_flights_data",
    "extract_domestic_dom_flights_data",
    "build_domestic_results",
    "extract_domestic_prices",
    "_fetch_domestic_search_page",
    "_record_domestic_api_failure",
    "_normalize_domestic_api_item",
    "_extract_domestic_benefit",
    "_iso_timestamp_to_hhmm",
    "_coerce_int",
    "_combine_benefit_labels",
]
