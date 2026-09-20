"""Browser session setup and search-page navigation.

SRP: browser lifecycle only — no extraction or retry decisions.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import TYPE_CHECKING, Any, Callable, Optional

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

import scraping.interpark as scraper_config
from scraping.errors import BrowserInitError, NetworkError
from scraping.interpark.network_listener import attach_interpark_response_listener

if TYPE_CHECKING:
    from playwright.sync_api import Page as PlaywrightPage

    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")


def resolve_profile_dir(background_mode: bool) -> Optional[str]:
    if background_mode:
        return None
    if getattr(sys, "frozen", False):
        app_data = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "FlightBot",
        )
        profile_dir = os.path.join(app_data, "playwright_profile")
    else:
        profile_dir = os.path.join(os.getcwd(), "playwright_profile")
    os.makedirs(profile_dir, exist_ok=True)
    return profile_dir


def init_browser_session(
    scraper: "PlaywrightScraper",
    log: Callable[[str], None],
    profile_dir: Optional[str],
    *,
    auto_headless: bool,
) -> "PlaywrightPage":
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
    return page


def navigate_to_search(
    scraper: "PlaywrightScraper",
    page: Any,
    *,
    origin_upper: str,
    destination_upper: str,
    departure_date: str,
    normalized_return_date: Optional[str],
    cabin: str,
    adults: int,
    is_domestic: bool,
    auto_headless: bool,
    log: Callable[[str], None],
) -> str:
    _, origin_code = scraper_config.resolve_interpark_location(
        origin_upper, is_domestic=is_domestic
    )
    _, dest_code = scraper_config.resolve_interpark_location(
        destination_upper, is_domestic=is_domestic
    )
    url = scraper_config.build_interpark_search_url(
        origin_upper,
        destination_upper,
        departure_date,
        normalized_return_date,
        cabin=cabin,
        adults=adults,
        infant=scraper._last_search_context.get("infant", 0),
        child=scraper._last_search_context.get("child", 0),
        is_domestic=is_domestic,
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
    return url
