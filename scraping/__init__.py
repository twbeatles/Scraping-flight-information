"""Scraping package exports.

Runtime-heavy scraper classes are loaded lazily so configuration facades can
import Interpark submodules without triggering Playwright scraper cycles.
"""

from scraping.errors import (
    BrowserInitError,
    DataExtractionError,
    NetworkError,
    ScraperError,
)
from scraping.models import FlightResult
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scraping.parallel import ParallelSearcher
    from scraping.playwright_scraper import PlaywrightScraper
    from scraping.searcher import FlightSearcher

__all__ = [
    "ScraperError",
    "BrowserInitError",
    "NetworkError",
    "DataExtractionError",
    "FlightResult",
    "PlaywrightScraper",
    "FlightSearcher",
    "ParallelSearcher",
]


def __getattr__(name: str):
    if name == "PlaywrightScraper":
        from scraping.playwright_scraper import PlaywrightScraper

        return PlaywrightScraper
    if name == "FlightSearcher":
        from scraping.searcher import FlightSearcher

        return FlightSearcher
    if name == "ParallelSearcher":
        from scraping.parallel import ParallelSearcher

        return ParallelSearcher
    raise AttributeError(name)
