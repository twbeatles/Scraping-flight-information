"""Full Playwright-backed search orchestration."""

from __future__ import annotations

import logging
import os
import sys
from typing import TYPE_CHECKING, Callable, List, Optional

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

import config
import scraping.interpark as scraper_config
from scraping.errors import (
    BrowserInitError,
    DataExtractionError,
    ManualModeActivationError,
    NetworkError,
    SearchCancelledError,
)
from scraping.search_cancel import raise_if_search_cancelled
from scraping.models import FlightResult
from scraping.search_flow.api_first import _try_api_first_extraction
from scraping.search_flow.domestic_flow import _handle_domestic_round_trip
from scraping.interpark.network_listener import attach_interpark_response_listener
from scraping.search_flow.manual_mode import _activate_manual_mode_or_raise

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")


def run_search(
    scraper: "PlaywrightScraper",
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    cabin_class: str = "ECONOMY",
    max_results: int = 1000,
    emit: Optional[Callable[[str], None]] = None,
    retry_count: int = 0,
    background_mode: bool = False,
    child: int = 0,
    infant: int = 0,
    *,
    time_module,
) -> List[FlightResult]:
    """Run a full Playwright-backed search."""

    search_start_time = time_module.time()
    url = ""
    profile_dir: str | None = None
    auto_headless = bool(
        background_mode or getattr(scraper_config, "AUTO_SEARCH_HEADLESS", True)
    )

    def log(message: str) -> None:
        if emit:
            emit(message)
        logger.info(message)

    results: List[FlightResult] = []
    scraper.manual_mode = False
    scraper._manual_reason = ""
    scraper._search_metrics = {}
    scraper._current_route = f"{origin.upper()}->{destination.upper()}"
    max_attempts = max(int(scraper_config.MAX_RETRY_COUNT), 1)
    start_attempt = max(int(retry_count or 0), 0)
    if start_attempt >= max_attempts:
        start_attempt = max_attempts - 1
    attempt_no = start_attempt + 1

    domestic_airports = config.DOMESTIC_AIRPORT_CODES
    origin_upper = origin.upper()
    destination_upper = destination.upper()
    origin_domestic = (
        origin_upper in domestic_airports
        or config.CITY_CODES_MAP.get(origin_upper, origin_upper) in domestic_airports
    )
    dest_domestic = (
        destination_upper in domestic_airports
        or config.CITY_CODES_MAP.get(destination_upper, destination_upper) in domestic_airports
    )
    is_domestic = origin_domestic and dest_domestic
    scraper._last_is_domestic = is_domestic

    cabin = cabin_class.upper() if cabin_class else "ECONOMY"
    departure_date = scraper_config.normalize_interpark_date(departure_date)
    normalized_return_date = (
        scraper_config.normalize_interpark_date(return_date) if return_date else None
    )
    if cabin not in ["ECONOMY", "BUSINESS", "FIRST"]:
        cabin = "ECONOMY"
    scraper._last_search_context = {
        "origin": origin_upper,
        "destination": destination_upper,
        "departure_date": departure_date,
        "return_date": normalized_return_date,
        "adults": adults,
        "cabin_class": cabin,
        "child": max(0, int(child or 0)),
        "infant": max(0, int(infant or 0)),
        "is_domestic": is_domestic,
    }

    try:
        for attempt_idx in range(start_attempt, max_attempts):
            raise_if_search_cancelled(scraper)
            attempt_no = attempt_idx + 1
            scraper.manual_mode = False
            scraper._manual_reason = ""
            scraper._search_metrics = {}

            scraper.close()
            scraper.manual_mode = False
            scraper._emit_telemetry(
                "search_attempt",
                success=True,
                route=scraper._current_route,
                details={
                    "attempt": attempt_no,
                    "cabin_class": cabin,
                    "is_domestic": is_domestic,
                    "background_mode": background_mode,
                },
            )

            try:
                profile_dir = None
                if not background_mode:
                    if getattr(sys, "frozen", False):
                        app_data = os.path.join(
                            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                            "FlightBot",
                        )
                        profile_dir = os.path.join(app_data, "playwright_profile")
                    else:
                        profile_dir = os.path.join(os.getcwd(), "playwright_profile")
                    os.makedirs(profile_dir, exist_ok=True)

                try:
                    scraper._init_browser(
                        log,
                        profile_dir,
                        headless=auto_headless,
                        block_resources=auto_headless,
                    )
                except TypeError as exc:
                    if "block_resources" not in str(exc):
                        raise
                    scraper._init_browser(log, profile_dir, headless=auto_headless)

                if scraper.context is None:
                    if scraper.browser is None:
                        raise BrowserInitError("브라우저 컨텍스트를 초기화할 수 없습니다.")
                    scraper.context = scraper.browser.new_context(
                        viewport={"width": 1400, "height": 900},
                        locale="ko-KR",
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        ),
                    )
                    scraper._configure_resource_blocking(auto_headless)

                context = scraper.context
                if context is None:
                    raise BrowserInitError("브라우저 컨텍스트가 정상적으로 생성되지 않았습니다.")
                scraper.page = context.new_page()
                page = scraper.page
                if page is None:
                    raise BrowserInitError("브라우저 페이지를 생성할 수 없습니다.")
                attach_interpark_response_listener(scraper, page)

                _, origin_code = scraper_config.resolve_interpark_location(origin_upper)
                _, dest_code = scraper_config.resolve_interpark_location(destination_upper)
                url = scraper_config.build_interpark_search_url(
                    origin_upper,
                    destination_upper,
                    departure_date,
                    normalized_return_date,
                    cabin=cabin,
                    adults=adults,
                    infant=scraper._last_search_context.get("infant", 0),
                    child=scraper._last_search_context.get("child", 0),
                )

                if is_domestic:
                    log(f"🇰🇷 국내선 검색 모드 ({origin_code} -> {dest_code})")
                else:
                    log("🌍 국제선 검색 모드")
                log(f"URL: {url}")
                if auto_headless:
                    log("자동 검색 최적화 모드: Headless + 리소스 차단")

                try:
                    page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=scraper_config.PAGE_LOAD_TIMEOUT_MS,
                    )
                except PlaywrightTimeoutError:
                    log("⚠️ 페이지 로딩 시간 초과 - 계속 진행합니다.")
                except Exception as exc:
                    raise NetworkError("페이지 로딩 실패", url) from exc

                api_first_results = _try_api_first_extraction(
                    scraper,
                    is_domestic=is_domestic,
                    is_round_trip=bool(normalized_return_date),
                    log=log,
                    time_module=time_module,
                )
                if api_first_results:
                    results = scraper._sort_and_limit_results(api_first_results, max_results, log)
                    log(f"✅ 자동 추출 성공: {len(results)}개")
                    break

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
                        break

                if is_domestic and normalized_return_date and found_data:
                    domestic_round_trip = _handle_domestic_round_trip(
                        scraper,
                        log,
                        max_results,
                        background_mode,
                        time_module,
                    )
                    if domestic_round_trip is not None:
                        results = domestic_round_trip
                        break

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
                        break
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
                    break

                results = scraper._sort_and_limit_results(results, max_results, log)
                if results:
                    log(f"✅ 자동 추출 성공: {len(results)}개")
                break

            except NetworkError as exc:
                logger.warning(
                    "네트워크 오류 (시도 %s/%s): %s",
                    attempt_no,
                    max_attempts,
                    exc,
                )
                scraper._emit_telemetry(
                    "search_attempt",
                    success=False,
                    route=scraper._current_route,
                    error_code="NETWORK_ERROR",
                    details={"attempt": attempt_no, "error": str(exc)},
                )
                scraper.close()
                scraper.manual_mode = False
                if attempt_idx + 1 < max_attempts:
                    delay = scraper_config.RETRY_DELAY_SECONDS * (2**attempt_idx)
                    log(f"🔁 네트워크 오류로 재시도합니다... ({attempt_no}/{max_attempts}, {delay}s 대기)")
                    time_module.sleep(delay)
                    continue
                raise
            except SearchCancelledError:
                log("검색이 취소되었습니다.")
                scraper.manual_mode = False
                scraper._search_metrics["cancelled"] = True
                break
            except BrowserInitError:
                raise
            except ManualModeActivationError:
                raise
            except DataExtractionError as exc:
                if background_mode:
                    log(f"⚠️ {exc} - 백그라운드 모드 종료")
                    scraper.manual_mode = False
                    scraper._search_metrics["background_failure_reason"] = str(exc)
                else:
                    log(f"⚠️ {exc} - 수동 모드로 전환")
                    if not scraper._manual_reason:
                        scraper._manual_reason = (
                            "domestic_api_failed" if is_domestic else "international_api_failed"
                        )
                    _activate_manual_mode_or_raise(
                        scraper,
                        url=url,
                        profile_dir=profile_dir,
                        is_domestic=is_domestic,
                        log=log,
                        auto_headless=auto_headless,
                        message="자동 추출 결과 없음 이후 수동 모드 전환에 실패했습니다.",
                    )
                break
            except Exception as exc:
                logger.error("Playwright error: %s", exc, exc_info=True)
                if emit:
                    emit(f"오류 발생: {exc}")
                if not scraper._manual_reason and not background_mode:
                    scraper._manual_reason = (
                        "domestic_api_failed" if is_domestic else "international_api_failed"
                    )
                if background_mode:
                    scraper.manual_mode = False
                else:
                    _activate_manual_mode_or_raise(
                        scraper,
                        url=url,
                        profile_dir=profile_dir,
                        is_domestic=is_domestic,
                        log=log,
                        auto_headless=auto_headless,
                        message="오류 복구 중 수동 모드 전환에 실패했습니다.",
                    )
                break
    finally:
        if not scraper.manual_mode:
            scraper.close()

        elapsed_time = time_module.time() - search_start_time
        result_count = len(results)
        logger.info("🔤 검색 완료 - 소요시간: %.1f초 결과: %s건", elapsed_time, result_count)
        if emit:
            emit(f"🔤 검색 완료 ({elapsed_time:.1f}초, {result_count}건)")
        scraper._emit_telemetry(
            "search_result",
            success=bool(results),
            route=scraper._current_route,
            manual_mode=scraper.manual_mode,
            result_count=result_count,
            duration_ms=int(elapsed_time * 1000),
            extraction_source=results[0].extraction_source if results else "",
            confidence=results[0].confidence if results else 0.0,
            details={
                "attempt": attempt_no,
                "background_mode": background_mode,
                "manual_reason": scraper._manual_reason,
                **(scraper._search_metrics or {}),
            },
        )

    return results
