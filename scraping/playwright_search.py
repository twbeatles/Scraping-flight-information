"""Search orchestration helpers for Playwright scraper."""

from __future__ import annotations

import logging
import os
import sys
from typing import TYPE_CHECKING, Callable, List, Optional

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

import config
import scraper_config
from scraper_config import ScraperScripts
from scraping.errors import BrowserInitError, DataExtractionError, NetworkError
from scraping.models import FlightResult

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
    *,
    time_module,
) -> List[FlightResult]:
    """Run a full Playwright-backed search."""

    search_start_time = time_module.time()

    def log(message: str) -> None:
        if emit:
            emit(message)
        logger.info(message)

    results: List[FlightResult] = []
    scraper.manual_mode = False
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

    try:
        for attempt_idx in range(start_attempt, max_attempts):
            attempt_no = attempt_idx + 1
            scraper.manual_mode = False

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

                scraper._init_browser(log, profile_dir, headless=background_mode)

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

                scraper.page = scraper.context.new_page()

                _, origin_code = scraper_config.resolve_interpark_location(origin_upper)
                _, dest_code = scraper_config.resolve_interpark_location(destination_upper)
                url = scraper_config.build_interpark_search_url(
                    origin_upper,
                    destination_upper,
                    departure_date,
                    normalized_return_date,
                    cabin=cabin,
                    adults=adults,
                    infant=0,
                    child=0,
                )

                if is_domestic:
                    log(f"🇰🇷 국내선 검색 모드 ({origin_code} -> {dest_code})")
                else:
                    log("🌍 국제선 검색 모드")
                log(f"URL: {url}")

                try:
                    scraper.page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=scraper_config.PAGE_LOAD_TIMEOUT_MS,
                    )
                except PlaywrightTimeoutError:
                    log("⚠️ 페이지 로딩 시간 초과 - 계속 진행합니다.")
                except Exception as exc:
                    raise NetworkError("페이지 로딩 실패", url) from exc

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
                    if background_mode:
                        log("백그라운드 모드에서는 수동 모드 전환 없이 종료합니다.")
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

                if found_data:
                    log("데이터 준비 완료! 추출 시작")
                    time_module.sleep(scraper_config.SEARCH_PAGE_STABILIZE_SECONDS)

                    if is_domestic:
                        log("🇰🇷 국내선 편도 추출")
                        results = scraper._extract_domestic_prices()
                    else:
                        results = scraper._extract_prices()

                    if not results:
                        raise DataExtractionError("자동 추출 결과가 없습니다.")
                else:
                    log("데이터가 충분히 로드되지 않았습니다.")
                    if background_mode:
                        break
                    scraper.manual_mode = True
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
            except BrowserInitError:
                raise
            except DataExtractionError as exc:
                if background_mode:
                    log(f"⚠️ {exc} - 백그라운드 모드 종료")
                    scraper.manual_mode = False
                else:
                    log(f"⚠️ {exc} - 수동 모드로 전환")
                    scraper.manual_mode = True
                break
            except Exception as exc:
                logger.error("Playwright error: %s", exc, exc_info=True)
                if emit:
                    emit(f"오류 발생: {exc}")
                scraper.manual_mode = False if background_mode else True
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
            details={"attempt": attempt_no, "background_mode": background_mode},
        )

    return results


def _handle_domestic_round_trip(
    scraper: "PlaywrightScraper",
    log: Callable[[str], None],
    max_results: int,
    background_mode: bool,
    time_module,
) -> Optional[List[FlightResult]]:
    """Handle domestic round-trip collection when Interpark splits legs."""

    log("🇰🇷 국내선 왕복: 가는편/오는편 분리 수집 시작")
    try:
        log("1단계: 가는편 목록 추출 중...")
        outbound_flights = scraper._extract_domestic_flights_data()
        log(f"가는편 {len(outbound_flights)}개 발견")

        if not outbound_flights:
            if background_mode:
                log("⚠️ 가는편 데이터 없음 - 백그라운드 모드 종료")
                return []
            log("⚠️ 가는편 데이터 없음 - 수동 모드 권장")
            scraper.manual_mode = True
            return []

        log("2단계: 가는편 선택 -> 오는편 화면 전환...")
        airlines_js = str(scraper.DOMESTIC_AIRLINES)
        best_outbound = min(outbound_flights, key=lambda item: item.get("price", float("inf")))
        price_text = (
            f"{best_outbound.get('price', 0):,}원"
            if best_outbound.get("price")
            else ""
        )
        js_click = ScraperScripts.get_click_flight_by_details_script(
            best_outbound.get("airline", ""),
            best_outbound.get("depTime", ""),
            best_outbound.get("arrTime", ""),
            price_text,
        )
        clicked = scraper.page.evaluate(js_click) if scraper.page else False
        if not clicked and scraper.page:
            js_click = ScraperScripts.get_click_flight_script(airlines_js)
            clicked = scraper.page.evaluate(js_click)

        if not clicked:
            log("⚠️ 가는편 선택 실패 - 가는편만 반환")
            return scraper._sort_and_limit_results(
                scraper._build_domestic_results(
                    outbound_flights,
                    source="Interpark (국내선 가는편)",
                    extraction_source="domestic_outbound_only",
                    confidence=0.7,
                ),
                max_results,
                log,
            )

        log("3단계: 오는편 로딩 대기...")
        return_ready = scraper._wait_for_domestic_return_view()
        if return_ready:
            log("✅ 오는편 화면 확인됨")
        if not return_ready:
            log("⚠️ 오는편 화면 로딩 실패 - 가는편만 반환")
            return scraper._sort_and_limit_results(
                scraper._build_domestic_results(
                    outbound_flights,
                    source="Interpark (국내선 가는편)",
                    extraction_source="domestic_outbound_only",
                    confidence=0.7,
                ),
                max_results,
                log,
            )

        log("4단계: 오는편 목록 추출 중...")
        time_module.sleep(scraper_config.DOMESTIC_RETURN_POST_CLICK_SETTLE_SECONDS)
        return_flights = scraper._extract_domestic_flights_data()
        log(f"오는편 {len(return_flights)}개 발견")

        log("5단계: 가는편/오는편 조합 중...")
        if outbound_flights and return_flights:
            log(
                "가는편/오는편 조합 계산 중... "
                f"(상위 {scraper_config.DOMESTIC_COMBINATION_TOP_N}x"
                f"{scraper_config.DOMESTIC_COMBINATION_TOP_N})"
            )
            results = scraper._combine_domestic_round_trip(
                outbound_flights,
                return_flights,
                max_results=max_results,
            )
            log(f"최저가 기준 상위 {len(results)}개 조합 반환")
            return scraper._sort_and_limit_results(results, max_results, log)

        return scraper._sort_and_limit_results(
            scraper._build_domestic_results(outbound_flights),
            max_results,
            log,
        )
    except Exception as exc:
        log(f"⚠️ 국내선 처리 중 오류: {exc}")
        logger.error("Domestic error: %s", exc, exc_info=True)
        return None
