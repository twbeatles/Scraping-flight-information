"""Domestic extraction helpers."""

from typing import List

from scraping.models import FlightResult
from scraping.playwright_scraper import PlaywrightScraper

def extract_domestic_flights_data(scraper: PlaywrightScraper) -> list:
    return scraper._extract_domestic_flights_data()

def extract_domestic_prices(scraper: PlaywrightScraper) -> List[FlightResult]:
    return scraper._extract_domestic_prices()
