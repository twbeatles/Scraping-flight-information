"""API-first extraction helper."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, List

import scraping.interpark as scraper_config
from scraping.models import FlightResult

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")


def _try_api_first_extraction(
    scraper: "PlaywrightScraper",
    *,
    is_domestic: bool,
    is_round_trip: bool,
    log: Callable[[str], None],
    time_module,
) -> List[FlightResult]:
    """Try the page/API extraction path before waiting on DOM result selectors."""

    page = getattr(scraper, "page", None)
    if page is None or not hasattr(page, "evaluate"):
        return []
    if is_domestic and is_round_trip:
        return []

    if is_domestic:
        log("🇰🇷 국내선 API 우선 추출 시도")
    else:
        log("🌍 국제선 API 우선 추출 시도")

    time_module.sleep(scraper_config.SEARCH_PAGE_STABILIZE_SECONDS)
    try:
        return scraper._extract_domestic_prices() if is_domestic else scraper._extract_prices()
    except Exception as exc:
        logger.info("API-first extraction failed before DOM wait: %s", exc)
        return []
