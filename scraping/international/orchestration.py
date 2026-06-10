"""International extraction orchestration."""

import logging
from typing import TYPE_CHECKING, List

from scraping.models import FlightResult
from scraping.international.api import _extract_international_prices_via_api
from scraping.international.dom import _extract_international_prices_from_dom

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")


def extract_international_prices(scraper: "PlaywrightScraper") -> List[FlightResult]:
    """Extract international flight results from the current page."""

    if not scraper.page:
        return []

    api_results = _extract_international_prices_via_api(scraper)
    if api_results:
        logger.info("🌍 국제선 API 추출 성공: %s개", len(api_results))
        return api_results

    logger.info("🌍 국제선 API 추출 실패 - DOM fallback으로 전환")
    return _extract_international_prices_from_dom(scraper)
