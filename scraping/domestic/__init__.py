"""Domestic result extraction package."""

from scraping.domestic.api import (
    _extract_domestic_benefit,
    _fetch_domestic_search_page,
    _normalize_domestic_api_item,
    _record_domestic_api_failure,
    extract_domestic_api_flights_data,
)
from scraping.domestic.dom import extract_domestic_dom_flights_data
from scraping.domestic.helpers import (
    _coerce_int,
    _combine_benefit_labels,
    _iso_timestamp_to_hhmm,
    combine_domestic_round_trip,
)
from scraping.domestic.results import (
    build_domestic_results,
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
