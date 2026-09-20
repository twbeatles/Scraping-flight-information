"""Result extraction phases (SRP: API-first + DOM-wait extraction only)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, List, Optional

import scraping.interpark as scraper_config
from scraping.errors import DataExtractionError
from scraping.models import FlightResult
from scraping.search_flow.api_first import _try_api_first_extraction
from scraping.search_flow.domestic_flow import _handle_domestic_round_trip
from scraping.search_flow.manual_mode import _activate_manual_mode_or_raise

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")


def run_api_first_phase(
    scraper: "PlaywrightScraper",
    *,
    is_domestic: bool,
    normalized_return_date: Optional[str],
    log: Callable[[str], None],
    time_module: Any,
    max_results: int,
    background_mode: bool,
) -> List[FlightResult]:
    """Return sorted results when API-first extraction succeeds, else []."""

    api_first_results = _try_api_first_extraction(
        scraper,
        is_domestic=is_domestic,
        is_round_trip=bool(normalized_return_date),
        log=log,
        time_module=time_module,
        max_results=max_results,
        background_mode=background_mode,
    )
    if api_first_results:
        results = scraper._sort_and_limit_results(api_first_results, max_results, log)
        log(f"✅ 자동 추출 성공: {len(results)}개")
        return results
    return []


def run_wait_and_extract_phase(
    scraper: "PlaywrightScraper",
    *,
    is_domestic: bool,
    normalized_return_date: Optional[str],
    max_results: int,
    background_mode: bool,
    log: Callable[[str], None],
    time_module: Any,
    url: str,
    profile_dir: Optional[str],
    auto_headless: bool,
) -> List[FlightResult]:
    """Wait for result DOM, then extract via round-trip/DOM paths."""

    log("결과 로딩 대기 중...")
    wait_result = scraper._wait_for_results(is_domestic, log)
    found_data = wait_result.get("found", False)
    selected_selector = wait_result.get("selector", "")
    if selected_selector:
        scraper._emit_telemetry(
            "selector_selected",
            success=True,
            route=scraper._current_route,
            selector_name=selected_selector,
        )

    if not found_data:
        log("데이터가 충분히 로드되지 않았습니다.")
        if not is_domestic:
            log("🌍 국제선은 DOM 대기 실패 시에도 API 우선 추출을 시도합니다.")
        elif background_mode:
            log("백그라운드 모드에서는 수동 모드 전환 없이 종료합니다.")
            scraper._search_metrics["background_failure_reason"] = "selector_wait_failed"
            return []

    if is_domestic and normalized_return_date and found_data:
        domestic_round_trip = _handle_domestic_round_trip(
            scraper,
            log,
            max_results,
            background_mode,
            time_module,
        )
        if domestic_round_trip is not None:
            return domestic_round_trip

    can_attempt_extraction = found_data or not is_domestic

    if can_attempt_extraction:
        if found_data:
            log("데이터 준비 완료! 추출 시작")
        else:
            log("DOM 준비 신호 없이 국제선 API/DOM 추출을 시도합니다.")
        time_module.sleep(scraper_config.SEARCH_PAGE_STABILIZE_SECONDS)

        if is_domestic:
            log("🇰🇷 국내선 편도 추출")
            results = scraper._extract_domestic_prices()
        else:
            results = scraper._extract_prices()

        if not results:
            if not scraper._manual_reason:
                scraper._manual_reason = (
                    "domestic_api_failed" if is_domestic else "international_api_failed"
                )
            raise DataExtractionError("자동 추출 결과가 없습니다.")
    else:
        log("데이터가 충분히 로드되지 않았습니다.")
        if background_mode:
            return []
        scraper._manual_reason = "international_api_failed" if not is_domestic else "domestic_api_failed"
        _activate_manual_mode_or_raise(
            scraper,
            url=url,
            profile_dir=profile_dir,
            is_domestic=is_domestic,
            log=log,
            auto_headless=auto_headless,
            message="결과 로딩 실패 후 수동 모드 전환에 실패했습니다.",
        )
        return []

    results = scraper._sort_and_limit_results(results, max_results, log)
    if results:
        log(f"✅ 자동 추출 성공: {len(results)}개")
    return results
