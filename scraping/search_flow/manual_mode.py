"""Manual-mode transition helper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from scraping.errors import ManualModeActivationError

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


def _activate_manual_mode_or_raise(
    scraper: "PlaywrightScraper",
    *,
    url: str,
    profile_dir: str | None,
    is_domestic: bool,
    log: Callable[[str], None],
    auto_headless: bool,
    message: str,
) -> None:
    entered = scraper._enter_manual_mode(
        url=url,
        profile_dir=profile_dir,
        is_domestic=is_domestic,
        log_func=log,
        reopen_visible=auto_headless,
    )
    if not entered:
        raise ManualModeActivationError(message)
