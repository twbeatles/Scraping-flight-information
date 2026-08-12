"""API-first extraction helper."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, List

import scraping.interpark as scraper_config
from scraping.models import FlightResult
from scraping.search_flow.domestic_flow import _handle_domestic_round_trip

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
    max_results: int = 1000,
    background_mode: bool = False,
) -> List[FlightResult]:
    """Try the page/API extraction path before waiting on DOM result selectors.

    Domestic round-trips must not return one-way outbound-only results from the
    simple API list path — they go through the round-trip combination flow.
    """

    page = getattr(scraper, "page", None)
    if page is None or not hasattr(page, "evaluate"):
        return []
    if is_domestic:
        log("🇰🇷 국내선 API 우선 추출 시도")
    else:
        log("🌍 국제선 API 우선 추출 시도")

    time_module.sleep(scraper_config.SEARCH_PAGE_STABILIZE_SECONDS)
    try:
        if is_domestic and is_round_trip:
            log("🇰🇷 국내선 왕복 — API-first에서 가는편/오는편 조합 경로 사용")
            combined = _handle_domestic_round_trip(
                scraper,
                log,
                max_results,
                background_mode,
                time_module,
            )
            return combined if combined is not None else []
        if is_domestic:
            return scraper._extract_domestic_prices()
        return scraper._extract_prices()
    except Exception as exc:
        logger.info("API-first extraction failed before DOM wait: %s", exc)
        return []
