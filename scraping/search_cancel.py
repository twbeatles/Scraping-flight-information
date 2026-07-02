"""Cooperative cancellation helpers for long-running scraper work."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

from scraping.errors import SearchCancelledError

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper

CancelCheck = Optional[Callable[[], bool]]


def set_cancel_check(scraper: "PlaywrightScraper", cancel_check: CancelCheck) -> None:
    scraper._cancel_check = cancel_check


def clear_cancel_check(scraper: "PlaywrightScraper") -> None:
    scraper._cancel_check = None


def is_search_cancelled(scraper: "PlaywrightScraper") -> bool:
    cancel_check = getattr(scraper, "_cancel_check", None)
    if not callable(cancel_check):
        return False
    try:
        return bool(cancel_check())
    except Exception:
        return False


def raise_if_search_cancelled(scraper: "PlaywrightScraper") -> None:
    if is_search_cancelled(scraper):
        raise SearchCancelledError()