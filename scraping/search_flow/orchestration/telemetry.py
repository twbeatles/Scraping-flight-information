"""Search telemetry emission (SRP: attempt/result events only)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, List, Optional

from scraping.models import FlightResult

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")


def emit_search_attempt(
    scraper: "PlaywrightScraper",
    *,
    attempt_no: int,
    cabin: str,
    is_domestic: bool,
    background_mode: bool,
) -> None:
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


def emit_search_result(
    scraper: "PlaywrightScraper",
    results: List[FlightResult],
    *,
    elapsed_time: float,
    emit: Optional[Callable[[str], None]],
    attempt_no: int,
    background_mode: bool,
) -> None:
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


def make_log(emit: Optional[Callable[[str], None]]) -> Callable[[str], None]:
    def log(message: str) -> None:
        if emit:
            emit(message)
        logger.info(message)

    return log
