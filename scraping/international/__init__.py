"""International result extraction package."""

from scraping.international.api import (
    _extract_international_prices_via_api,
    _fetch_international_result_pages,
    _record_international_api_failure,
)
from scraping.international.dom import (
    _advance_results_scroll,
    _extract_international_prices_from_dom,
    _read_current_result_indices,
)
from scraping.international.normalizer import (
    _build_international_results,
    _normalize_international_api_item,
)
from scraping.international.orchestration import extract_international_prices
from scraping.international.sorting import sort_and_limit_results
from scraping.international.helpers import (
    _benefit_label_parts,
    _browser_item_unique_key,
    _coerce_int,
    _extract_international_benefit,
    _first_positive_int,
    _iso_duration_to_text,
    _iso_timestamp_to_hhmm,
    _iter_benefit_nodes,
    _join_label_parts,
    _nested_get,
    _result_unique_key,
    _schedule_airline,
    _schedule_bounds,
    _select_international_fare,
)

__all__ = [
    "sort_and_limit_results",
    "extract_international_prices",
    "_extract_international_prices_via_api",
    "_extract_international_prices_from_dom",
    "_fetch_international_result_pages",
    "_record_international_api_failure",
    "_read_current_result_indices",
    "_advance_results_scroll",
    "_normalize_international_api_item",
    "_build_international_results",
    "_schedule_bounds",
    "_schedule_airline",
    "_browser_item_unique_key",
    "_result_unique_key",
    "_iso_timestamp_to_hhmm",
    "_iso_duration_to_text",
    "_nested_get",
    "_coerce_int",
    "_select_international_fare",
    "_extract_international_benefit",
    "_first_positive_int",
    "_iter_benefit_nodes",
    "_benefit_label_parts",
    "_join_label_parts",
]
