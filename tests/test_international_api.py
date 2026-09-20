from typing import Any, cast
from scraper_v2 import (
    FlightResult,
    FlightSearcher,
    ManualModeActivationError,
    PlaywrightScraper,
    ParallelSearcher,
)
from scraping.playwright_results import _normalize_international_api_item
from scraping.international.api import _fetch_international_result_pages

class _PlaywrightPageStubMixin:
    def on(self, _event, _handler):
        return None

def test_international_api_pagination_respects_page_cap(monkeypatch):
    calls = []
    scraper = PlaywrightScraper()
    cast(Any, scraper).page = object()
    scraper._search_metrics = {}

    monkeypatch.setattr("scraping.international.api.scraper_config.INTERNATIONAL_API_MAX_PAGES", 3)

    def _fake_fetch(_scraper, _url, *, method="GET", body=None):
        page_number = int((body or {}).get("pageNumber", 1))
        calls.append(page_number)
        return {
            "page": {"currentPage": page_number, "pageSize": 20, "totalCount": 120},
            "contents": [{"id": page_number}],
        }

    monkeypatch.setattr("scraping.international.api.page_fetch_json", _fake_fetch)

    payloads = _fetch_international_result_pages(scraper, "INTERNATIONAL::cap")

    assert calls == [1, 2, 3]
    assert len(payloads) == 3
    assert scraper._search_metrics["api_pages_truncated"] is True
    assert scraper._search_metrics["api_page_cap"] == 3
    assert scraper._search_metrics["api_total_pages_estimated"] == 6

def test_international_dedup_key_preserves_distinct_return_details():
    class _FakePage:
        def evaluate(self, script):
            if script == "document.body.scrollHeight":
                return 100
            if script.startswith("window.scrollTo("):
                return None
            if "const cards = document.querySelectorAll('li[data-index], div[data-index]');" in script:
                return [
                    {
                        "airline": "TestAir",
                        "price": 200000,
                        "depTime": "10:00",
                        "arrTime": "12:00",
                        "stops": 0,
                        "retDepTime": "14:00",
                        "retArrTime": "16:00",
                        "retStops": 0,
                        "isRoundTrip": True,
                    },
                    {
                        "airline": "TestAir",
                        "price": 200000,
                        "depTime": "10:00",
                        "arrTime": "12:30",
                        "stops": 1,
                        "retDepTime": "18:00",
                        "retArrTime": "20:00",
                        "retStops": 1,
                        "isRoundTrip": True,
                    },
                ]
            if "const candidates = document.querySelectorAll(" in script:
                return []
            return []

        def wait_for_timeout(self, _):
            return None

    scraper = PlaywrightScraper()
    page = _FakePage()
    cast(Any, scraper).page = page

    results = scraper._extract_prices()

    assert len(results) == 2
    assert sorted(r.return_stops for r in results) == [0, 1]

def test_international_api_path_paginates_and_builds_results_without_dom_fallback():
    class _FakePage:
        def __init__(self):
            self.fetch_calls = []
            self.result_calls = 0

        def evaluate(self, script):
            if "performance.getEntriesByType('resource')" in script and "INTERNATIONAL::" in script:
                return ["INTERNATIONAL::abc"]
            if "fetch(" in script and "/status" in script:
                self.fetch_calls.append("status")
                return {"status": "COMPLETE", "content": {"listKey": "INTERNATIONAL::abc"}}
            if "fetch(" in script and '/international/flights/search/v2/INTERNATIONAL::abc' in script:
                self.result_calls += 1
                self.fetch_calls.append(f"final-{self.result_calls}")
                assert '"POST"' in script
                if self.result_calls == 1:
                    shared_item = {
                        "adultPrice": 359400,
                        "schedules": [
                            {
                                "carrier": {"name": "제주항공"},
                                "totalFlightTime": "PT2H30M",
                                "stop": 0,
                                "segments": [
                                    {
                                        "departure": {"at": "2026-04-15T10:25:00"},
                                        "arrival": {"at": "2026-04-15T12:55:00"},
                                        "marketingCarrier": {"name": "제주항공"},
                                    }
                                ],
                            },
                            {
                                "carrier": {"name": "파라타항공"},
                                "totalFlightTime": "PT2H45M",
                                "stop": 0,
                                "segments": [
                                    {
                                        "departure": {"at": "2026-04-18T13:30:00"},
                                        "arrival": {"at": "2026-04-18T16:15:00"},
                                        "marketingCarrier": {"name": "파라타항공"},
                                    }
                                ],
                            },
                        ],
                        "fares": [{"adultPrice": 359400}],
                    }
                    return {
                        "page": {"currentPage": 1, "pageSize": 20, "totalCount": 40},
                        "bestFares": [shared_item],
                        "contents": [shared_item],
                    }
                return {
                    "page": {"currentPage": 2, "pageSize": 20, "totalCount": 40},
                    "bestFares": [],
                    "contents": [
                        {
                            "adultPrice": 489100,
                            "schedules": [
                                {
                                    "carrier": {"name": "대한항공"},
                                    "totalFlightTime": "PT2H20M",
                                    "stop": 0,
                                    "segments": [
                                        {
                                            "departure": {"at": "2026-04-15T08:10:00"},
                                            "arrival": {"at": "2026-04-15T10:30:00"},
                                            "marketingCarrier": {"name": "대한항공"},
                                        }
                                    ],
                                },
                                {
                                    "carrier": {"name": "진에어"},
                                    "totalFlightTime": "PT2H30M",
                                    "stop": 0,
                                    "segments": [
                                        {
                                            "departure": {"at": "2026-04-18T18:00:00"},
                                            "arrival": {"at": "2026-04-18T20:30:00"},
                                            "marketingCarrier": {"name": "진에어"},
                                        }
                                    ],
                                },
                            ],
                            "fares": [{"adultPrice": 489100}],
                        }
                    ],
                }
            if "fetch(" in script and "/flights/search/CITY:SEL-CITY:TYO/2026-04-15/CITY:TYO-CITY:SEL/2026-04-18" in script:
                raise AssertionError("existing search key should prevent rebuilding the initial search request")
            if "const cards = document.querySelectorAll('li[data-index], div[data-index]');" in script:
                raise AssertionError("DOM fallback should not run when API succeeds")
            if "const candidates = document.querySelectorAll(" in script:
                raise AssertionError("Fallback DOM parser should not run when API succeeds")
            if script == "document.body.scrollHeight":
                return 100
            if script.startswith("window.scrollTo("):
                return None
            raise AssertionError(f"Unexpected script: {script[:120]}")

        def wait_for_timeout(self, _timeout):
            return None

    scraper = PlaywrightScraper()
    page = _FakePage()
    cast(Any, scraper).page = page
    cast(Any, scraper)._last_search_context = {
        "origin": "ICN",
        "destination": "NRT",
        "departure_date": "20260415",
        "return_date": "20260418",
        "adults": 1,
        "cabin_class": "BUSINESS",
        "child": 0,
        "infant": 0,
        "is_domestic": False,
    }

    results = scraper._extract_prices()

    assert len(results) == 2
    assert results[0].price == 359400
    assert results[0].airline == "제주항공"
    assert results[0].return_airline == "파라타항공"
    assert results[0].extraction_source == "international_api"
    assert scraper._search_metrics["api_total_count"] == 40
    assert scraper._search_metrics["fetched_pages"] == 2
    assert scraper._search_metrics["api_item_count"] == 2
    assert page.fetch_calls == ["status", "final-1", "final-2"]

def test_international_api_failure_records_reason_and_meta():
    class _FakePage:
        def evaluate(self, script):
            if "performance.getEntriesByType('resource')" in script:
                return [
                    "https://example.test/international/flights/search/v2/INTERNATIONAL::abc/status",
                    "https://example.test/international/flights/search/v2/INTERNATIONAL::abc",
                ]
            if "fetch(" in script and "/status" in script:
                return {
                    "code": "RATE_LIMIT",
                    "__flightbot_api_meta": {
                        "status": 429,
                        "ok": False,
                        "payload_keys": ["code"],
                    },
                }
            if "const cards = document.querySelectorAll('li[data-index], div[data-index]');" in script:
                return []
            if "Array.from(document.querySelectorAll('li[data-index], div[data-index]'))" in script:
                return []
            if "const cards = Array.from(document.querySelectorAll('li[data-index], div[data-index]'));" in script:
                return {"advanced": False, "atEnd": True}
            if "const candidates = document.querySelectorAll(" in script:
                return []
            raise AssertionError(f"Unexpected script: {script[:120]}")

        def wait_for_timeout(self, _timeout):
            return None

    scraper = PlaywrightScraper()
    cast(Any, scraper).page = _FakePage()
    cast(Any, scraper)._last_search_context = {
        "origin": "ICN",
        "destination": "NRT",
        "departure_date": "20260415",
        "return_date": "20260418",
        "adults": 1,
        "cabin_class": "ECONOMY",
        "child": 0,
        "infant": 0,
        "is_domestic": False,
    }

    assert scraper._extract_prices() == []
    assert scraper._manual_reason == "international_api_http_failed"
    assert scraper._search_metrics["api_failure_reason"] == "international_api_http_failed"
    assert scraper._search_metrics["api_failure_meta"]["status"] == 429
    assert scraper._search_metrics["api_recent_resources"]

def test_international_dom_fallback_detects_virtualized_index_gap():
    class _FakePage:
        def __init__(self):
            self.primary_calls = 0
            self.index_calls = 0
            self.advance_calls = 0

        def evaluate(self, script):
            if "performance.getEntriesByType('resource')" in script and "INTERNATIONAL::" in script:
                return []
            if "fetch(" in script:
                return {}
            if "const cards = document.querySelectorAll('li[data-index], div[data-index]');" in script:
                self.primary_calls += 1
                if self.primary_calls == 1:
                    return [
                        {
                            "airline": "제주항공",
                            "price": 100000,
                            "depTime": "10:00",
                            "arrTime": "12:00",
                            "stops": 0,
                            "retDepTime": "15:00",
                            "retArrTime": "17:00",
                            "retStops": 0,
                            "isRoundTrip": True,
                        }
                    ]
                if self.primary_calls == 2:
                    return [
                        {
                            "airline": "대한항공",
                            "price": 120000,
                            "depTime": "11:00",
                            "arrTime": "13:00",
                            "stops": 0,
                            "retDepTime": "18:00",
                            "retArrTime": "20:00",
                            "retStops": 0,
                            "isRoundTrip": True,
                        }
                    ]
                return []
            if "Array.from(document.querySelectorAll('li[data-index], div[data-index]'))" in script:
                self.index_calls += 1
                if self.index_calls == 1:
                    return list(range(0, 9))
                return list(range(15, 31))
            if "const cards = Array.from(document.querySelectorAll('li[data-index], div[data-index]'));" in script:
                self.advance_calls += 1
                return {
                    "advanced": self.advance_calls < 3,
                    "atEnd": self.advance_calls >= 3,
                    "scrollTop": self.advance_calls * 100,
                    "maxTop": 300,
                    "mode": "container",
                }
            if "const candidates = document.querySelectorAll(" in script:
                return []
            raise AssertionError(f"Unexpected script: {script[:120]}")

        def wait_for_timeout(self, _timeout):
            return None

    scraper = PlaywrightScraper()
    cast(Any, scraper).page = _FakePage()
    cast(Any, scraper)._last_search_context = {
        "origin": "ICN",
        "destination": "NRT",
        "departure_date": "20260415",
        "return_date": "20260418",
        "adults": 1,
        "cabin_class": "ECONOMY",
        "child": 0,
        "infant": 0,
        "is_domestic": False,
    }

    results = scraper._extract_prices()

    assert len(results) == 2
    assert scraper._search_metrics["dom_gap_detected"] is True
    assert 0 in scraper._search_metrics["dom_seen_indices"]
    assert 30 in scraper._search_metrics["dom_seen_indices"]
    assert scraper._manual_reason == "dom_fallback_gap_risk"

def test_international_api_item_preserves_cheapest_fare_benefit():
    result = _normalize_international_api_item(
        {
            "adultPrice": 0,
            "schedules": [
                {
                    "carrier": {"name": "제주항공"},
                    "totalFlightTime": "PT2H30M",
                    "stop": 0,
                    "segments": [
                        {
                            "departure": {"at": "2026-04-15T10:25:00"},
                            "arrival": {"at": "2026-04-15T12:55:00"},
                            "marketingCarrier": {"name": "제주항공"},
                        }
                    ],
                }
            ],
            "fares": [
                {"adultPrice": 420000},
                {
                    "adultPrice": 390000,
                    "benefits": [
                        {
                            "discountedPrice": 380000,
                            "cardCashback": {"cardName": "KB국민", "rate": 10},
                            "promotionName": "카드 즉시할인",
                        }
                    ],
                },
            ],
        }
    )

    assert result is not None
    assert result.price == 390000
    assert result.benefit_price == 380000
    assert "KB국민 10% 캐시백 적용 시" in result.benefit_label
    assert "카드 즉시할인" in result.benefit_label

def test_international_search_attempts_api_extraction_before_dom_wait(monkeypatch):
    class _FakePage(_PlaywrightPageStubMixin):
        def __init__(self):
            self.urls = []

        def goto(self, url, *_args, **_kwargs):
            self.urls.append(url)

        def evaluate(self, _script):
            return []

    class _FakeContext:
        def __init__(self, page):
            self._page = page

        def new_page(self):
            return self._page

        def close(self):
            return None

    page = _FakePage()
    scraper = PlaywrightScraper()
    calls = {"wait": 0, "extract": 0}

    def _fake_init_browser(*_args, **_kwargs):
        cast(Any, scraper).context = _FakeContext(page)

    def _fake_wait(*_args, **_kwargs):
        calls["wait"] += 1
        raise AssertionError("DOM wait should not block a successful API-first extraction")

    def _fake_extract():
        calls["extract"] += 1
        return [
            FlightResult(
                airline="API항공",
                price=180000,
                departure_time="10:00",
                arrival_time="12:00",
                extraction_source="international_api",
            )
        ]

    monkeypatch.setattr(scraper, "_init_browser", _fake_init_browser)
    monkeypatch.setattr(scraper, "_wait_for_results", _fake_wait)
    monkeypatch.setattr(scraper, "_extract_prices", _fake_extract)
    monkeypatch.setattr(scraper, "close", lambda: None)
    monkeypatch.setattr("scraping.playwright_scraper.time.sleep", lambda *_args, **_kwargs: None)

    results = scraper.search("ICN", "NRT", "20260301", None, adults=1, cabin_class="ECONOMY", max_results=10)

    assert len(results) == 1
    assert calls == {"wait": 0, "extract": 1}
    assert page.urls

