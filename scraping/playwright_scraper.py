"""Playwright-backed scraping engine."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

import logging
from playwright.sync_api import Browser, BrowserContext, Page, Playwright

from scraping.models import FlightResult
from scraping.playwright_browser import (
    close_resources,
    init_browser,
    wait_for_domestic_return_view,
    wait_for_results,
)
from scraping.playwright_domestic import (
    build_domestic_results,
    combine_domestic_round_trip,
    extract_domestic_flights_data,
    extract_domestic_prices,
)
from scraping.playwright_results import extract_international_prices, sort_and_limit_results
from scraping.playwright_search import run_search


logger = logging.getLogger("ScraperV2")


class PlaywrightScraper:
    """Context-managed Playwright scraper entry point."""

    DOMESTIC_AIRLINES = [
        "대한항공",
        "아시아나",
        "제주항공",
        "진에어",
        "티웨이",
        "에어부산",
        "에어서울",
        "이스타항공",
        "하이에어",
        "에어프레미아",
        "플라이강원",
    ]

    def __init__(self, telemetry_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.context: Optional[BrowserContext] = None
        self.manual_mode: bool = False
        self.telemetry_callback = telemetry_callback
        self._last_is_domestic: bool = False
        self._current_route: str = ""
        self._no_scroll_count: int = 0
        self._no_new_count: int = 0
        self._bottom_count: int = 0

    def _emit_telemetry(self, event_type: str, success: bool = True, **kwargs) -> None:
        if not self.telemetry_callback:
            return

        payload = {
            "event_type": event_type,
            "success": bool(success),
        }
        payload.update(kwargs)

        try:
            self.telemetry_callback(payload)
        except Exception:
            logger.debug("Telemetry callback failed", exc_info=True)

    def __enter__(self) -> "PlaywrightScraper":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.close()
        return False

    def _init_browser(
        self,
        log_func: Optional[Callable[[str], None]] = None,
        user_data_dir: Optional[str] = None,
        headless: bool = False,
    ) -> None:
        init_browser(
            self,
            log_func=log_func,
            user_data_dir=user_data_dir,
            headless=headless,
        )

    def _wait_for_results(
        self,
        is_domestic: bool,
        log_func: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        return wait_for_results(self, is_domestic=is_domestic, log_func=log_func)

    def _wait_for_domestic_return_view(self) -> bool:
        return wait_for_domestic_return_view(self)

    @staticmethod
    def _sort_and_limit_results(
        results: List[FlightResult],
        max_results: int,
        log_func: Optional[Callable[[str], None]] = None,
    ) -> List[FlightResult]:
        return sort_and_limit_results(results, max_results, log_func)

    def _combine_domestic_round_trip(
        self,
        outbound_flights: List[Dict[str, Any]],
        return_flights: List[Dict[str, Any]],
        max_results: int,
    ) -> List[FlightResult]:
        return combine_domestic_round_trip(outbound_flights, return_flights, max_results)

    def search(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        cabin_class: str = "ECONOMY",
        max_results: int = 1000,
        emit: Optional[Callable[[str], None]] = None,
        _retry_count: int = 0,
        background_mode: bool = False,
    ) -> List[FlightResult]:
        return run_search(
            self,
            origin,
            destination,
            departure_date,
            return_date=return_date,
            adults=adults,
            cabin_class=cabin_class,
            max_results=max_results,
            emit=emit,
            retry_count=_retry_count,
            background_mode=background_mode,
            time_module=time,
        )

    def _extract_domestic_flights_data(self) -> list:
        return extract_domestic_flights_data(self)

    @staticmethod
    def _build_domestic_results(
        items: List[Dict[str, Any]],
        *,
        source: str = "Interpark (국내선)",
        extraction_source: str = "domestic_scroll",
        confidence: float = 0.75,
    ) -> List[FlightResult]:
        return build_domestic_results(
            items,
            source=source,
            extraction_source=extraction_source,
            confidence=confidence,
        )

    def _extract_domestic_prices(self) -> List[FlightResult]:
        return extract_domestic_prices(self)

    def _extract_prices(self) -> List[FlightResult]:
        return extract_international_prices(self)

    def extract_from_current_page(self) -> List[FlightResult]:
        if self._last_is_domestic:
            return self._extract_domestic_prices()
        return self._extract_prices()

    def close(self) -> None:
        close_resources(self)

    def is_manual_mode(self) -> bool:
        return self.manual_mode and self.page is not None
