"""Domestic extraction helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from scraping.models import FlightResult
from scraping.playwright_domestic import (
    extract_domestic_flights_data as _extract_domestic_flights_data,
    extract_domestic_prices as _extract_domestic_prices,
)

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


def extract_domestic_flights_data(scraper: "PlaywrightScraper") -> list:
    return _extract_domestic_flights_data(scraper)


def extract_domestic_prices(scraper: "PlaywrightScraper") -> List[FlightResult]:
    return _extract_domestic_prices(scraper)
