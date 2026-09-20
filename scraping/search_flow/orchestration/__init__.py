"""Full Playwright-backed search orchestration (package facade).

Split (SOLID/SRP): `run_search` keeps the retry-loop orchestration only;
route preparation, browser setup, extraction phases, failure recovery,
and telemetry live in focused sibling modules. The public signature and
behavior are unchanged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, List, Optional

import scraping.interpark as scraper_config
from scraping.errors import (
    BrowserInitError,
    DataExtractionError,
    ManualModeActivationError,
    NetworkError,
    SearchCancelledError,
)
from scraping.models import FlightResult
from scraping.search_cancel import raise_if_search_cancelled
from scraping.search_flow.orchestration.browser import (
    init_browser_session,
    navigate_to_search,
    resolve_profile_dir,
)
from scraping.search_flow.orchestration.context import (
    compute_retry_window,
    prepare_search,
    reset_attempt_state,
)
from scraping.search_flow.orchestration.extraction import (
    run_api_first_phase,
    run_wait_and_extract_phase,
)
from scraping.search_flow.orchestration.failures import (
    handle_data_extraction_error,
    handle_network_error,
    handle_search_cancelled,
    handle_unexpected_error,
)
from scraping.search_flow.orchestration.telemetry import (
    emit_search_attempt,
    emit_search_result,
    make_log,
)

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


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

    log = make_log(emit)

    results: List[FlightResult] = []
    reset_attempt_state(scraper, origin, destination)
    start_attempt, max_attempts = compute_retry_window(retry_count)
    attempt_no = start_attempt + 1

    prepared, search_context = prepare_search(
        origin,
        destination,
        departure_date,
        return_date,
        adults,
        cabin_class,
        max_results,
        background_mode,
        child,
        infant,
    )
    is_domestic = prepared.is_domestic
    scraper._last_is_domestic = is_domestic
    scraper._last_search_context = search_context

    try:
        for attempt_idx in range(start_attempt, max_attempts):
            raise_if_search_cancelled(scraper)
            attempt_no = attempt_idx + 1
            reset_attempt_state(scraper, origin, destination)

            scraper.close()
            scraper.manual_mode = False
            emit_search_attempt(
                scraper,
                attempt_no=attempt_no,
                cabin=prepared.cabin,
                is_domestic=is_domestic,
                background_mode=background_mode,
            )

            try:
                profile_dir = resolve_profile_dir(background_mode)

                page = init_browser_session(
                    scraper, log, profile_dir, auto_headless=auto_headless
                )
                url = navigate_to_search(
                    scraper,
                    page,
                    origin_upper=prepared.origin_upper,
                    destination_upper=prepared.destination_upper,
                    departure_date=prepared.departure_date,
                    normalized_return_date=prepared.normalized_return_date,
                    cabin=prepared.cabin,
                    adults=adults,
                    is_domestic=is_domestic,
                    auto_headless=auto_headless,
                    log=log,
                )

                results = run_api_first_phase(
                    scraper,
                    is_domestic=is_domestic,
                    normalized_return_date=prepared.normalized_return_date,
                    log=log,
                    time_module=time_module,
                    max_results=max_results,
                    background_mode=background_mode,
                )
                if results:
                    break

                results = run_wait_and_extract_phase(
                    scraper,
                    is_domestic=is_domestic,
                    normalized_return_date=prepared.normalized_return_date,
                    max_results=max_results,
                    background_mode=background_mode,
                    log=log,
                    time_module=time_module,
                    url=url,
                    profile_dir=profile_dir,
                    auto_headless=auto_headless,
                )
                break

            except NetworkError as exc:
                should_retry = handle_network_error(
                    scraper,
                    exc,
                    log=log,
                    time_module=time_module,
                    attempt_no=attempt_no,
                    max_attempts=max_attempts,
                    attempt_idx=attempt_idx,
                )
                if should_retry:
                    continue
                raise
            except SearchCancelledError:
                handle_search_cancelled(scraper, log)
                break
            except BrowserInitError:
                raise
            except ManualModeActivationError:
                raise
            except DataExtractionError as exc:
                handle_data_extraction_error(
                    scraper,
                    exc,
                    is_domestic=is_domestic,
                    background_mode=background_mode,
                    log=log,
                    url=url,
                    profile_dir=profile_dir,
                    auto_headless=auto_headless,
                )
                break
            except Exception as exc:
                handle_unexpected_error(
                    scraper,
                    exc,
                    is_domestic=is_domestic,
                    background_mode=background_mode,
                    log=log,
                    emit=emit,
                    url=url,
                    profile_dir=profile_dir,
                    auto_headless=auto_headless,
                )
                break
    finally:
        if not scraper.manual_mode:
            scraper.close()

        elapsed_time = time_module.time() - search_start_time
        emit_search_result(
            scraper,
            results,
            elapsed_time=elapsed_time,
            emit=emit,
            attempt_no=attempt_no,
            background_mode=background_mode,
        )

    return results
