"""Domestic round-trip search flow."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

import scraping.interpark as scraper_config
from scraping.interpark.scripts import ScraperScripts
from scraping.models import FlightResult
from scraping.playwright_api import find_latest_search_key

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")


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
        outbound_key = find_latest_search_key(scraper, trip_kind="domestic")
        outbound_flights, outbound_meta = scraper._extract_domestic_api_flights_data(search_key=outbound_key)
        if not outbound_flights:
            outbound_flights = scraper._extract_domestic_flights_data()
            outbound_meta = {
                "total_count": len(outbound_flights),
                "fetched_pages": 0,
            }
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
        return_key = find_latest_search_key(scraper, trip_kind="domestic")
        return_flights: List[Dict[str, Any]] = []
        return_meta = {"total_count": 0, "fetched_pages": 0}
        if return_key and return_key != outbound_key:
            return_flights, return_meta = scraper._extract_domestic_api_flights_data(search_key=return_key)
        else:
            scraper._manual_reason = "domestic_return_key_missing"

        if not return_flights:
            return_flights = scraper._extract_domestic_dom_flights_data()
            if return_flights and scraper._manual_reason == "domestic_return_key_missing":
                return_meta = {
                    "total_count": len(return_flights),
                    "fetched_pages": 0,
                }
        log(f"오는편 {len(return_flights)}개 발견")
        scraper._search_metrics.update(
            {
                "api_total_count": int(outbound_meta.get("total_count", 0) or 0)
                + int(return_meta.get("total_count", 0) or 0),
                "fetched_pages": int(outbound_meta.get("fetched_pages", 0) or 0)
                + int(return_meta.get("fetched_pages", 0) or 0),
                "api_item_count": len(outbound_flights) + len(return_flights),
            }
        )

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
