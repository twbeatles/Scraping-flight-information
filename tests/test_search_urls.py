from typing import Any, cast
import scraper_config
from scraper_v2 import (
    FlightResult,
    FlightSearcher,
    ManualModeActivationError,
    PlaywrightScraper,
    ParallelSearcher,
)
from scraping.playwright_api import find_search_keys, page_fetch_json

def test_find_search_keys_accepts_status_and_final_resource_urls():
    class _FakePage:
        def evaluate(self, script):
            assert "performance.getEntriesByType('resource')" in script
            return ["INTERNATIONAL::old", "INTERNATIONAL::abc"]

    scraper = PlaywrightScraper()
    cast(Any, scraper).page = _FakePage()

    assert find_search_keys(scraper, trip_kind="international") == [
        "INTERNATIONAL::old",
        "INTERNATIONAL::abc",
    ]

def test_build_interpark_search_url_normalizes_hyphenated_dates():
    url = scraper_config.build_interpark_search_url(
        "ICN",
        "NRT",
        "2026-03-01",
        "2026-03-05",
        cabin="BUSINESS",
        adults=2,
    )

    assert "/c:SEL-c:TYO-20260301/c:TYO-c:SEL-20260305" in url
    assert url.endswith("?cabin=BUSINESS&infant=0&child=0&adult=2")

def test_build_interpark_search_url_treats_sel_as_city_code():
    url = scraper_config.build_interpark_search_url("SEL", "CJU", "2026-05-01")

    # SEL is a pure city code; CJU stays as airport on domestic routes.
    assert "/c:SEL-a:CJU-20260501" in url

def test_build_interpark_search_url_keeps_domestic_airport_codes():
    url = scraper_config.build_interpark_search_url("GMP", "CJU", "2026-05-01")

    assert "/a:GMP-a:CJU-20260501" in url
    assert "c:SEL" not in url

def test_build_interpark_search_url_international_still_uses_city_map():
    url = scraper_config.build_interpark_search_url(
        "ICN", "NRT", "2026-05-01", is_domestic=False
    )
    assert "/c:SEL-c:TYO-20260501" in url

def test_build_interpark_international_api_search_url_uses_city_route_types():
    url = scraper_config.build_interpark_international_api_search_url(
        "ICN",
        "NRT",
        "2026-04-15",
        "2026-04-18",
        cabin="BUSINESS",
        adults=2,
    )

    assert "/flights/search/CITY:SEL-CITY:TYO/2026-04-15/CITY:TYO-CITY:SEL/2026-04-18" in url
    assert url.endswith("?adult=2&child=0&infant=0&cabins=BUSINESS&freeBaggageOnly=false")

def test_page_fetch_json_sends_post_body_as_json_string():
    class _FakePage:
        def __init__(self):
            self.script = ""

        def evaluate(self, script):
            self.script = script
            return {"ok": True}

    scraper = PlaywrightScraper()
    page = _FakePage()
    cast(Any, scraper).page = page

    payload = page_fetch_json(
        scraper,
        "https://example.test/api",
        method="POST",
        body={"pageNumber": 1, "filter": {"byCabins": ["ECONOMY"]}},
    )

    assert payload == {"ok": True}
    assert "body: JSON.parse" not in page.script
    assert 'headers: {"content-type":"application/json"}' in page.script
    body_line = next(line.strip() for line in page.script.splitlines() if line.strip().startswith("body:"))
    assert body_line == 'body: "{\\"pageNumber\\": 1, \\"filter\\": {\\"byCabins\\": [\\"ECONOMY\\"]}}",'

