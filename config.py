"""Backward-compatible facade for core configuration."""

from core.airports import (
    AIRLINE_CATEGORIES,
    AIRPORTS,
    ALL_AIRLINES,
    CITY_CODES_MAP,
    DOMESTIC_AIRPORTS,
    DOMESTIC_AIRPORT_CODES,
    _extract_airport_code,
    get_airline_category,
    validate_airport_code,
)
from core.search_params import (
    SEARCH_PARAMS_SCHEMA_VERSION,
    VALID_CABIN_CLASSES,
    _coerce_bool,
    infer_is_domestic_route,
    normalize_search_date,
    normalize_search_params,
)
from core.preferences import PreferenceManager

__all__ = [
    "AIRLINE_CATEGORIES",
    "AIRPORTS",
    "ALL_AIRLINES",
    "CITY_CODES_MAP",
    "DOMESTIC_AIRPORTS",
    "DOMESTIC_AIRPORT_CODES",
    "SEARCH_PARAMS_SCHEMA_VERSION",
    "VALID_CABIN_CLASSES",
    "PreferenceManager",
    "_coerce_bool",
    "_extract_airport_code",
    "get_airline_category",
    "infer_is_domestic_route",
    "normalize_search_date",
    "normalize_search_params",
    "validate_airport_code",
]
