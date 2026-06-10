"""Backward-compatible facade for scraper components."""

import time

from scraping.errors import (
    BrowserInitError,
    DataExtractionError,
    ManualModeActivationError,
    NetworkError,
    ScraperError,
)
from scraping.models import FlightResult
from scraping.parallel import ParallelSearcher
from scraping.playwright_scraper import PlaywrightScraper
from scraping.searcher import FlightSearcher

__all__ = [
    "ScraperError",
    "BrowserInitError",
    "NetworkError",
    "DataExtractionError",
    "ManualModeActivationError",
    "FlightResult",
    "PlaywrightScraper",
    "FlightSearcher",
    "ParallelSearcher",
]
