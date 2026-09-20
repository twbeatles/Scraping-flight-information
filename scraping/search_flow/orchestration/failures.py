"""Retry-loop failure handling (SRP: per-error-type recovery only).

Each handler mirrors one `except` branch of the original `run_search`.
Handlers return normally when the search should stop retrying (`break`
in the original loop); `handle_network_error` returns True when the
caller should sleep and `continue` to the next attempt.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Optional

import scraping.interpark as scraper_config
from scraping.search_flow.manual_mode import _activate_manual_mode_or_raise

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")


def handle_network_error(
    scraper: "PlaywrightScraper",
    exc: Exception,
    *,
    log: Callable[[str], None],
    time_module: Any,
    attempt_no: int,
    max_attempts: int,
    attempt_idx: int,
) -> bool:
    """Return True when the caller should retry, False when it must re-raise."""

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
        return True
    return False


def handle_search_cancelled(scraper: "PlaywrightScraper", log: Callable[[str], None]) -> None:
    log("검색이 취소되었습니다.")
    scraper.manual_mode = False
    scraper._search_metrics["cancelled"] = True


def handle_data_extraction_error(
    scraper: "PlaywrightScraper",
    exc: Exception,
    *,
    is_domestic: bool,
    background_mode: bool,
    log: Callable[[str], None],
    url: str,
    profile_dir: Optional[str],
    auto_headless: bool,
) -> None:
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


def handle_unexpected_error(
    scraper: "PlaywrightScraper",
    exc: Exception,
    *,
    is_domestic: bool,
    background_mode: bool,
    log: Callable[[str], None],
    emit: Optional[Callable[[str], None]],
    url: str,
    profile_dir: Optional[str],
    auto_headless: bool,
) -> None:
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

