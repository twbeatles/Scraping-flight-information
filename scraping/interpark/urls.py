"""Interpark URL and route normalization helpers."""

from datetime import datetime

from core.airports import CITY_CODES_MAP, DOMESTIC_AIRPORT_CODES
from scraping.interpark.adapter import get_interpark_adapter

_ADAPTER = get_interpark_adapter()
INTERPARK_SEARCH_URL_BASE = _ADAPTER.search_url_base
INTERPARK_AIR_API_BASE = _ADAPTER.air_api_base

# Pure city codes that should keep the city prefix even on domestic routes.
_DOMESTIC_CITY_CODES = frozenset({"SEL"})


def normalize_interpark_date(date_text: str | None) -> str:
    """Convert supported user-facing date formats to Interpark compact paths."""
    if not date_text:
        return ""

    value = str(date_text).strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y%m%d")
        except ValueError:
            continue

    raise ValueError(f"Unsupported Interpark date format: {date_text}")


def normalize_interpark_api_date(date_text: str | None) -> str:
    """Convert supported dates to Interpark API's dashed format."""
    compact = normalize_interpark_date(date_text)
    return datetime.strptime(compact, "%Y%m%d").strftime("%Y-%m-%d")


def _is_domestic_airport_code(code: str) -> bool:
    normalized = (code or "").strip().upper()
    if not normalized:
        return False
    if normalized in DOMESTIC_AIRPORT_CODES:
        return True
    mapped = CITY_CODES_MAP.get(normalized, normalized)
    return mapped in DOMESTIC_AIRPORT_CODES


def infer_interpark_is_domestic(origin: str, destination: str) -> bool:
    """True when both ends are domestic airport/city codes."""
    return _is_domestic_airport_code(origin) and _is_domestic_airport_code(destination)


def resolve_interpark_location(
    code: str,
    *,
    is_domestic: bool = False,
) -> tuple[str, str]:
    """Return the route prefix and normalized city/airport code for URLs.

    Domestic routes keep airport codes (a:GMP) so Gimpo/Incheon are not collapsed
    into the Seoul city code. International routes keep the city-map behaviour
    (ICN→SEL, NRT→TYO). Explicit city codes like SEL remain c:SEL.
    """
    normalized = (code or "").strip().upper()
    if not normalized:
        return "a", ""

    if is_domestic:
        if normalized in _DOMESTIC_CITY_CODES:
            return "c", normalized
        # Prefer the airport code itself; do not map GMP/ICN → SEL.
        return "a", normalized

    if normalized in CITY_CODES_MAP:
        return "c", CITY_CODES_MAP[normalized]
    return "a", normalized


def _interpark_api_location(code: str) -> str:
    """International API location token (CITY/AIRPORT). Always city-map based."""
    prefix, normalized = resolve_interpark_location(code, is_domestic=False)
    route_type = "CITY" if prefix == "c" else "AIRPORT"
    return f"{route_type}:{normalized}"


def build_interpark_search_url(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None = None,
    *,
    cabin: str = "ECONOMY",
    adults: int = 1,
    infant: int = 0,
    child: int = 0,
    is_domestic: bool | None = None,
) -> str:
    """Build a canonical Interpark search URL with compact dates."""
    domestic = (
        bool(is_domestic)
        if is_domestic is not None
        else infer_interpark_is_domestic(origin, destination)
    )
    origin_prefix, origin_code = resolve_interpark_location(origin, is_domestic=domestic)
    dest_prefix, dest_code = resolve_interpark_location(destination, is_domestic=domestic)
    departure = normalize_interpark_date(departure_date)
    returning = normalize_interpark_date(return_date) if return_date else ""

    route = f"{origin_prefix}:{origin_code}-{dest_prefix}:{dest_code}-{departure}"
    if returning:
        route = (
            f"{route}/"
            f"{dest_prefix}:{dest_code}-{origin_prefix}:{origin_code}-{returning}"
        )

    safe_cabin = (cabin or "ECONOMY").upper()
    safe_adults = max(1, int(adults or 1))

    return (
        f"{INTERPARK_SEARCH_URL_BASE}/{route}"
        f"?cabin={safe_cabin}&infant={int(infant)}&child={int(child)}&adult={safe_adults}"
    )


def build_interpark_international_api_search_url(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None = None,
    *,
    cabin: str = "ECONOMY",
    adults: int = 1,
    infant: int = 0,
    child: int = 0,
) -> str:
    """Build the current Interpark international search API URL."""
    origin_code = _interpark_api_location(origin)
    dest_code = _interpark_api_location(destination)
    departure = normalize_interpark_api_date(departure_date)
    returning = normalize_interpark_api_date(return_date) if return_date else ""
    safe_cabin = (cabin or "ECONOMY").upper()
    safe_adults = max(1, int(adults or 1))

    route = f"{origin_code}-{dest_code}/{departure}"
    if returning:
        route = f"{route}/{dest_code}-{origin_code}/{returning}"

    return (
        f"{_ADAPTER.air_api_base}{_ADAPTER.international_initial_search_api_path}{route}"
        f"?adult={safe_adults}&child={int(child)}&infant={int(infant)}"
        f"&cabins={safe_cabin}&freeBaggageOnly=false"
    )
