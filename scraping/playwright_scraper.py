"""Playwright-backed scraping engine."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

import logging
from playwright.sync_api import Browser, BrowserContext, Page, Playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

import scraper_config
from scraping.models import FlightResult
from scraping.playwright_browser import (
    close_resources,
    configure_resource_blocking,
    init_browser,
    wait_for_domestic_return_view,
    wait_for_results,
)
from scraping.domestic import (
    build_domestic_results,
    combine_domestic_round_trip,
    extract_domestic_api_flights_data,
    extract_domestic_dom_flights_data,
    extract_domestic_flights_data,
    extract_domestic_prices,
)
from scraping.international import extract_international_prices, sort_and_limit_results
from scraping.search_flow import run_search


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
        self._last_search_context: Dict[str, Any] = {}
        self._manual_reason: str = ""
        self._search_metrics: Dict[str, Any] = {}

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
        block_resources: bool = False,
    ) -> None:
        init_browser(
            self,
            log_func=log_func,
            user_data_dir=user_data_dir,
            headless=headless,
            block_resources=block_resources,
        )

    def _configure_resource_blocking(self, enabled: bool) -> None:
        configure_resource_blocking(self, enabled)

    def _enter_manual_mode(
        self,
        url: str,
        profile_dir: str | None,
        is_domestic: bool,
        log_func: Callable[[str], None],
        reopen_visible: bool,
    ) -> bool:
        """Open or reuse a visible browser so the user can extract manually."""
        if not reopen_visible and self.page is not None:
            self.manual_mode = True
            log_func("수동 모드 활성화 - 브라우저에서 결과 로딩 후 추출 버튼을 누르세요")
            return True

        if reopen_visible:
            log_func("자동 추출 실패 - 수동 모드 브라우저를 여는 중...")
        else:
            log_func("수동 모드 재초기화: 기존 브라우저 세션이 없어 새로 엽니다.")

        try:
            self.close()
            try:
                self._init_browser(
                    log_func=log_func,
                    user_data_dir=profile_dir,
                    headless=False,
                    block_resources=False,
                )
            except TypeError as exc:
                if "block_resources" not in str(exc):
                    raise
                self._init_browser(
                    log_func=log_func,
                    user_data_dir=profile_dir,
                    headless=False,
                )
            if self.context is None and self.browser is not None:
                self.context = self.browser.new_context(
                    viewport={"width": 1400, "height": 900},
                    locale="ko-KR",
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36"
                    ),
                )
            if self.context is None:
                return False
            self.page = self.context.new_page()

            if url and self.page is not None:
                try:
                    self.page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=scraper_config.PAGE_LOAD_TIMEOUT_MS,
                    )
                except PlaywrightTimeoutError:
                    log_func("수동 모드 페이지 로딩 시간 초과 - 계속 진행합니다.")
                except Exception as exc:
                    log_func(f"수동 모드 페이지 진입 실패: {exc}")
            self._wait_for_results(is_domestic, lambda _msg: None)
            self.manual_mode = True
            log_func("수동 모드 활성화 - 브라우저에서 결과 로딩 후 추출 버튼을 누르세요")
            return True
        except Exception as exc:
            logger.error("Manual mode activation failed: %s", exc, exc_info=True)
            self.close()
            self.manual_mode = False
            return False

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

    def _extract_domestic_api_flights_data(
        self,
        *,
        search_key: str | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        return extract_domestic_api_flights_data(self, search_key=search_key)

    def _extract_domestic_dom_flights_data(self) -> list:
        return extract_domestic_dom_flights_data(self)

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

    def get_manual_reason(self) -> str:
        return self._manual_reason

    def close(self) -> None:
        close_resources(self)

    def is_manual_mode(self) -> bool:
        return self.manual_mode and self.page is not None
