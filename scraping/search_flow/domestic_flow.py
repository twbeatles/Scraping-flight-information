"""Domestic round-trip search flow."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

import scraping.interpark as scraper_config
from scraping.interpark.scripts import ScraperScripts
from scraping.models import FlightResult
from scraping.playwright_api import find_latest_search_key, wait_for_search_key

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
        if not outbound_key:
            outbound_key = wait_for_search_key(scraper, trip_kind="domestic")
        outbound_flights, outbound_meta = scraper._extract_domestic_api_flights_data(
            search_key=outbound_key
        )
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
        return_flights, return_meta, click_meta = _select_outbound_and_collect_return(
            scraper,
            outbound_flights,
            outbound_key=outbound_key,
            log=log,
            time_module=time_module,
        )
        if isinstance(getattr(scraper, "_search_metrics", None), dict):
            scraper._search_metrics.update(click_meta)

        if not return_flights and not click_meta.get("outbound_clicked"):
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

        if not return_flights and click_meta.get("return_view_ready") is False:
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

        log(f"오는편 {len(return_flights)}개 발견")
        outbound_pages_truncated = bool(outbound_meta.get("pages_truncated"))
        return_pages_truncated = bool(return_meta.get("pages_truncated"))
        scraper._search_metrics.update(
            {
                "api_total_count": int(outbound_meta.get("total_count", 0) or 0)
                + int(return_meta.get("total_count", 0) or 0),
                "fetched_pages": int(outbound_meta.get("fetched_pages", 0) or 0)
                + int(return_meta.get("fetched_pages", 0) or 0),
                "api_fetched_pages": int(outbound_meta.get("fetched_pages", 0) or 0)
                + int(return_meta.get("fetched_pages", 0) or 0),
                "api_page_cap": int(outbound_meta.get("page_cap", 0) or 0)
                + int(return_meta.get("page_cap", 0) or 0),
                "api_pages_truncated": outbound_pages_truncated or return_pages_truncated,
                "api_total_pages_estimated": int(outbound_meta.get("total_pages_estimated", 0) or 0)
                + int(return_meta.get("total_pages_estimated", 0) or 0),
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


def _select_outbound_and_collect_return(
    scraper: "PlaywrightScraper",
    outbound_flights: List[Dict[str, Any]],
    *,
    outbound_key: str,
    log: Callable[[str], None],
    time_module,
) -> tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    """Try multiple outbound candidates until a return leg can be collected."""

    airlines_js = str(scraper.DOMESTIC_AIRLINES)
    candidate_limit = max(
        int(getattr(scraper_config, "DOMESTIC_ROUND_TRIP_CLICK_CANDIDATES", 5)),
        1,
    )
    candidates = sorted(
        outbound_flights,
        key=lambda item: item.get("price", float("inf")),
    )[:candidate_limit]

    click_meta: Dict[str, Any] = {
        "outbound_clicked": False,
        "outbound_click_attempts": 0,
        "return_view_ready": False,
        "return_key_found": False,
    }
    empty_meta = {"total_count": 0, "fetched_pages": 0}

    for index, candidate in enumerate(candidates):
        click_meta["outbound_click_attempts"] = index + 1
        if not scraper.page:
            break

        price_text = (
            f"{candidate.get('price', 0):,}원"
            if candidate.get("price")
            else ""
        )
        js_click = ScraperScripts.get_click_flight_by_details_script(
            candidate.get("airline", ""),
            candidate.get("depTime", ""),
            candidate.get("arrTime", ""),
            price_text,
            flight_number=str(candidate.get("flightNumber", "") or ""),
        )
        clicked = scraper.page.evaluate(js_click)
        if not clicked and index == 0:
            # First failure: also try any airline-matching button as a last resort.
            clicked = scraper.page.evaluate(ScraperScripts.get_click_flight_script(airlines_js))
        if not clicked:
            continue

        click_meta["outbound_clicked"] = True
        log(f"3단계: 오는편 로딩 대기... (후보 {index + 1}/{len(candidates)})")
        return_ready = scraper._wait_for_domestic_return_view()
        click_meta["return_view_ready"] = bool(return_ready)
        if return_ready:
            log("✅ 오는편 화면 확인됨")
        else:
            log("⚠️ 오는편 화면 미확인 - 다음 후보 시도")
            continue

        log("4단계: 오는편 목록 추출 중...")
        time_module.sleep(scraper_config.DOMESTIC_RETURN_POST_CLICK_SETTLE_SECONDS)
        exclude = {outbound_key} if outbound_key else set()
        return_key = wait_for_search_key(
            scraper,
            trip_kind="domestic",
            timeout_seconds=float(
                getattr(scraper_config, "SEARCH_KEY_RETURN_WAIT_TIMEOUT_SECONDS", 10.0)
            ),
            exclude_keys=exclude,
        )
        return_flights: List[Dict[str, Any]] = []
        return_meta: Dict[str, Any] = dict(empty_meta)

        if return_key:
            click_meta["return_key_found"] = True
            return_flights, return_meta = scraper._extract_domestic_api_flights_data(
                search_key=return_key
            )
        else:
            scraper._manual_reason = "domestic_return_key_missing"

        if not return_flights:
            return_flights = scraper._extract_domestic_dom_flights_data()
            if return_flights and scraper._manual_reason == "domestic_return_key_missing":
                return_meta = {
                    "total_count": len(return_flights),
                    "fetched_pages": 0,
                }

        if return_flights:
            if scraper._manual_reason == "domestic_return_key_missing" and return_key:
                scraper._manual_reason = ""
            return return_flights, return_meta, click_meta

        log("⚠️ 오는편 추출 실패 - 다음 가는편 후보 시도")

    return [], empty_meta, click_meta
