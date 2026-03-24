from pathlib import Path
import re
from typing import Any, cast

import pytest

import scraper_config
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from scraper_v2 import PlaywrightScraper
from scraper_config import ScraperScripts


def test_selector_candidates_exist_for_domestic_and_international():
    assert scraper_config.DOMESTIC_WAIT_SELECTORS
    assert scraper_config.INTERNATIONAL_WAIT_SELECTORS
    assert any("data-index" in s for s in scraper_config.INTERNATIONAL_WAIT_SELECTORS)


def test_regex_patterns_match_fixture_sample():
    fixture = Path(__file__).resolve().parent / "fixtures" / "interpark_sample_result.html"
    html = fixture.read_text(encoding="utf-8")

    time_matches = re.findall(scraper_config.REGEX_TIME, html)
    price_matches = re.findall(scraper_config.REGEX_PRICE, html)
    stop_matches = re.findall(scraper_config.REGEX_STOPS, html)

    assert ("10:20", "12:45") in time_matches
    assert any(p.startswith("123,000") for p in price_matches)
    assert "1" in stop_matches


def test_price_regex_avoids_time_digit_prefix_regression():
    fixture = Path(__file__).resolve().parent / "fixtures" / "interpark_domestic_card.html"
    html = fixture.read_text(encoding="utf-8")

    price_matches = re.findall(scraper_config.REGEX_PRICE, html)

    assert "31,500" in price_matches
    assert "31,200" in price_matches
    assert "531,500" not in price_matches


def test_wait_for_results_returns_selected_selector():
    class _FakePage:
        def __init__(self):
            self.calls = 0

        def wait_for_selector(self, _selector, timeout=0):
            self.calls += 1
            if self.calls < 2:
                raise PlaywrightTimeoutError("timeout")
            return True

    scraper = PlaywrightScraper()
    cast(Any, scraper).page = _FakePage()

    # Exception type is broad in fake page; fallback path should still keep trying.
    result = scraper._wait_for_results(is_domestic=False, log_func=lambda _m: None)

    assert isinstance(result, dict)
    assert result["found"] is True
    assert result["selector"]


def test_international_script_handles_live_like_fixture_and_ignores_crossselling():
    fixture = Path(__file__).resolve().parent / "fixtures" / "interpark_international_live_like.html"
    html = fixture.read_text(encoding="utf-8")

    results = _evaluate_script_on_fixture(html, ScraperScripts.get_international_prices_script())

    assert results
    assert results[0]["airline"] == "제주항공"
    assert results[0]["returnAirline"] == "파라타항공"
    assert all(item["airline"] != "크로스셀링" for item in results)


def test_domestic_script_extracts_base_and_benefit_price_from_fixture():
    fixture = Path(__file__).resolve().parent / "fixtures" / "interpark_domestic_card.html"
    html = fixture.read_text(encoding="utf-8")

    results = _evaluate_script_on_fixture(
        html,
        ScraperScripts.get_domestic_list_script(str(PlaywrightScraper.DOMESTIC_AIRLINES)),
    )

    assert results
    assert results[0]["price"] == 31500
    assert results[0]["benefitPrice"] == 31200
    assert "1% 캐시백 적용 시" in results[0]["benefitLabel"]


def _evaluate_script_on_fixture(html: str, script: str):
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        pytest.skip(f"Playwright unavailable: {exc}")

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html)
            result = page.evaluate(script)
            browser.close()
            return result
    except Exception as exc:
        pytest.skip(f"Playwright browser unavailable: {exc}")
