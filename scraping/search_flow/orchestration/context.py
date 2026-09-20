"""Search preparation: route classification and parameter normalization.

SRP: pure preparation only — no browser, network, or telemetry side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import config
import scraping.interpark as scraper_config


@dataclass(frozen=True)
class PreparedSearch:
    origin_upper: str
    destination_upper: str
    cabin: str
    departure_date: str
    normalized_return_date: Optional[str]
    is_domestic: bool
    max_results: int
    background_mode: bool


def classify_route(origin: str, destination: str) -> tuple[str, str, bool]:
    domestic_airports = config.DOMESTIC_AIRPORT_CODES
    origin_upper = origin.upper()
    destination_upper = destination.upper()
    origin_domestic = (
        origin_upper in domestic_airports
        or config.CITY_CODES_MAP.get(origin_upper, origin_upper) in domestic_airports
    )
    dest_domestic = (
        destination_upper in domestic_airports
        or config.CITY_CODES_MAP.get(destination_upper, destination_upper) in domestic_airports
    )
    return origin_upper, destination_upper, bool(origin_domestic and dest_domestic)


def normalize_cabin(cabin_class: str) -> str:
    cabin = cabin_class.upper() if cabin_class else "ECONOMY"
    if cabin not in ["ECONOMY", "BUSINESS", "FIRST"]:
        cabin = "ECONOMY"
    return cabin


def normalize_dates(
    departure_date: str, return_date: Optional[str]
) -> tuple[str, Optional[str]]:
    normalized_departure = scraper_config.normalize_interpark_date(departure_date)
    normalized_return = (
        scraper_config.normalize_interpark_date(return_date) if return_date else None
    )
    return normalized_departure, normalized_return


def prepare_search(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    cabin_class: str = "ECONOMY",
    max_results: int = 1000,
    background_mode: bool = False,
    child: int = 0,
    infant: int = 0,
) -> tuple[PreparedSearch, Dict[str, Any]]:
    origin_upper, destination_upper, is_domestic = classify_route(origin, destination)
    cabin = normalize_cabin(cabin_class)
    normalized_departure, normalized_return = normalize_dates(departure_date, return_date)
    prepared = PreparedSearch(
        origin_upper=origin_upper,
        destination_upper=destination_upper,
        cabin=cabin,
        departure_date=normalized_departure,
        normalized_return_date=normalized_return,
        is_domestic=is_domestic,
        max_results=max_results,
        background_mode=background_mode,
    )
    context = {
        "origin": origin_upper,
        "destination": destination_upper,
        "departure_date": normalized_departure,
        "return_date": normalized_return,
        "adults": adults,
        "cabin_class": cabin,
        "child": max(0, int(child or 0)),
        "infant": max(0, int(infant or 0)),
        "is_domestic": is_domestic,
    }
    return prepared, context


def reset_attempt_state(scraper: Any, origin: str, destination: str) -> None:
    scraper.manual_mode = False
    scraper._manual_reason = ""
    scraper._search_metrics = {}
    scraper._current_route = f"{origin.upper()}->{destination.upper()}"


def compute_retry_window(retry_count: int) -> tuple[int, int]:
    max_attempts = max(int(scraper_config.MAX_RETRY_COUNT), 1)
    start_attempt = max(int(retry_count or 0), 0)
    if start_attempt >= max_attempts:
        start_attempt = max_attempts - 1
    return start_attempt, max_attempts
