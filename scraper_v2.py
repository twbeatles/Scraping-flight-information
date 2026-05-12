"""Backward-compatible facade for scraper components."""

import time
import os
import sys
import heapq
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Callable
import logging
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError

import config
import scraper_config
from scraper_config import ScraperScripts

from scraping.errors import (
    ScraperError,
    BrowserInitError,
    NetworkError,
    DataExtractionError,
    ManualModeActivationError,
)
from scraping.models import FlightResult
from scraping.playwright_scraper import PlaywrightScraper
from scraping.searcher import FlightSearcher
from scraping.parallel import ParallelSearcher

logger = logging.getLogger("ScraperV2")

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
