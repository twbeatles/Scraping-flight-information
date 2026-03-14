"""Browser lifecycle helpers for Playwright scraper."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

import scraper_config
from scraping.errors import BrowserInitError

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")


def init_browser(
    scraper: "PlaywrightScraper",
    log_func: Optional[Callable[[str], None]] = None,
    user_data_dir: Optional[str] = None,
    headless: bool = False,
) -> None:
    """Start a usable Playwright browser context."""

    def log(message: str) -> None:
        if log_func:
            log_func(message)
        logger.info(message)

    log("🌐 Playwright 브라우저 시작 중...")

    try:
        playwright = sync_playwright().start()
        scraper.playwright = playwright
    except FileNotFoundError as exc:
        error_message = (
            "❌ Playwright 실행 파일을 찾을 수 없습니다.\n\n"
            "해결 방법:\n"
            "1. pip install playwright\n"
            "2. playwright install\n\n"
            f"상세 오류: {exc}"
        )
        logger.error(error_message)
        raise BrowserInitError(error_message) from exc
    except Exception as exc:
        error_message = (
            "❌ Playwright 초기화에 실패했습니다.\n\n"
            f"오류: {exc}\n\n"
            "해결 방법:\n"
            "- pip install --upgrade playwright"
        )
        logger.error(error_message)
        raise BrowserInitError(error_message) from exc

    browser_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--no-sandbox",
    ]
    browsers_to_try = [
        ("Chrome", "chrome"),
        ("Edge", "msedge"),
        ("Chromium (내장)", None),
    ]
    tried_browsers: list[str] = []
    playwright = scraper.playwright
    if playwright is None:
        raise BrowserInitError("Playwright 객체 초기화 결과를 확인할 수 없습니다.")

    for browser_name, channel in browsers_to_try:
        try:
            log(f"  - {browser_name} 시도 중...")
            launch_options: Dict[str, Any] = {
                "headless": bool(headless),
                "args": browser_args,
            }
            if channel:
                launch_options["channel"] = channel

            if user_data_dir:
                context_options = {
                    **launch_options,
                    "viewport": {"width": 1400, "height": 900},
                    "locale": "ko-KR",
                    "user_agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36"
                    ),
                }
                scraper.context = playwright.chromium.launch_persistent_context(
                    user_data_dir,
                    **context_options,
                )
                log(f"  - {browser_name} 시작 성공 (Persistent Context)")
            else:
                scraper.browser = playwright.chromium.launch(**launch_options)
                log(f"  - {browser_name} 시작 성공")
            return
        except Exception as exc:
            tried_browsers.append(f"{browser_name}: {str(exc)[:50]}")
            logger.debug("%s 시작 실패: %s", browser_name, exc, exc_info=True)

    close_resources(scraper)
    error_details = "\n".join(f"  - {entry}" for entry in tried_browsers)
    error_message = (
        "❌ 사용할 수 있는 브라우저를 찾을 수 없습니다.\n\n"
        "시도한 브라우저:\n"
        f"{error_details}\n\n"
        "해결 방법:\n"
        "  1. Chrome 설치: https://www.google.com/chrome\n"
        "  2. Edge 설치: https://www.microsoft.com/edge\n"
        "  3. 또는 playwright install chromium\n\n"
        "Windows 10 이상에서는 Edge가 기본 설치되어 있는 경우가 많습니다."
    )
    logger.error(error_message)
    raise BrowserInitError(error_message)


def wait_for_results(
    scraper: "PlaywrightScraper",
    is_domestic: bool,
    log_func: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Wait for a known result selector and record telemetry."""

    if not scraper.page:
        return {"found": False, "selector": ""}

    timeout_ms = int(scraper_config.DATA_WAIT_TIMEOUT_SECONDS * 1000)
    selectors = (
        scraper_config.DOMESTIC_WAIT_SELECTORS
        if is_domestic
        else scraper_config.INTERNATIONAL_WAIT_SELECTORS
    )
    per_timeout = max(1000, timeout_ms // max(len(selectors), 1))

    for selector in selectors:
        started = time.perf_counter()
        try:
            scraper.page.wait_for_selector(selector, timeout=per_timeout)
            duration_ms = int((time.perf_counter() - started) * 1000)
            scraper._emit_telemetry(
                "selector_wait",
                success=True,
                route=scraper._current_route,
                selector_name=selector,
                duration_ms=duration_ms,
            )
            return {"found": True, "selector": selector}
        except PlaywrightTimeoutError:
            duration_ms = int((time.perf_counter() - started) * 1000)
            scraper._emit_telemetry(
                "selector_wait",
                success=False,
                route=scraper._current_route,
                selector_name=selector,
                duration_ms=duration_ms,
                error_code="SELECTOR_TIMEOUT",
            )
            if log_func:
                log_func(f"⚠️ 결과 대기 실패: {selector}")

    return {"found": False, "selector": ""}


def wait_for_domestic_return_view(scraper: "PlaywrightScraper") -> bool:
    """Confirm the domestic return-leg screen is visible."""

    if not scraper.page:
        return False

    timeout_ms = int(max(5, scraper_config.DOMESTIC_RETURN_WAIT_TIMEOUT_SECONDS) * 1000)
    try:
        scraper.page.wait_for_function(
            """
            () => {
                const bodyText = document.body?.innerText || '';
                const priceNodes = document.querySelectorAll('button, li, span');
                let priceCount = 0;
                for (const node of priceNodes) {
                    const text = node.textContent || '';
                    if (/\\d{1,3}(,\\d{3})+\\s*원/.test(text)) {
                        priceCount += 1;
                        if (priceCount >= 5) break;
                    }
                }
                return bodyText.includes('오는편') && priceCount >= 5;
            }
            """,
            timeout=timeout_ms,
        )
        return True
    except PlaywrightTimeoutError:
        return False


def close_resources(scraper: "PlaywrightScraper") -> None:
    """Close every Playwright resource on the scraper instance."""

    resources = [
        ("page", scraper.page),
        ("context", scraper.context),
        ("browser", scraper.browser),
        ("playwright", scraper.playwright),
    ]

    for name, resource in resources:
        if not resource:
            continue
        try:
            if name == "playwright":
                resource.stop()
            else:
                resource.close()
        except Exception as exc:
            logger.debug("%s 정리 중 오류 (무시): %s", name, exc)
        finally:
            setattr(scraper, name, None)

    scraper.manual_mode = False
