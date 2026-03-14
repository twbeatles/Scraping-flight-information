"""International extraction helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from scraping.models import FlightResult
from scraping.playwright_results import (
    extract_international_prices as _extract_international_prices,
)

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


def extract_international_prices(scraper: "PlaywrightScraper") -> List[FlightResult]:
    return _extract_international_prices(scraper)
