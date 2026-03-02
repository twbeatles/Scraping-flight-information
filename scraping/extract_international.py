"""International extraction helpers."""

from typing import List

from scraping.models import FlightResult
from scraping.playwright_scraper import PlaywrightScraper

def extract_international_prices(scraper: PlaywrightScraper) -> List[FlightResult]:
    return scraper._extract_prices()
