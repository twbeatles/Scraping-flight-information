from pathlib import Path
import re
from typing import Any, cast

import scraper_config
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from scraper_v2 import PlaywrightScraper


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
