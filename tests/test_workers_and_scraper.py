import threading
import time
from datetime import datetime, timedelta
from types import SimpleNamespace
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
from scraping.playwright_results import _normalize_international_api_item
from scraping.playwright_search import _handle_domestic_round_trip
from scraping.domestic.results import extract_domestic_flights_data
from scraping.domestic.api import extract_domestic_api_flights_data
from scraping.international.api import _fetch_international_result_pages
from ui.workers import AlertAutoCheckWorker, DateRangeWorker, MultiSearchWorker, SearchWorker


class _PlaywrightPageStubMixin:
    def on(self, _event, _handler):
        return None


def test_date_range_worker_closes_searcher_when_cancelled_after_init(monkeypatch):
    class _FakeSearcher:
        instances = []

        def __init__(self):
            self.closed = False
            _FakeSearcher.instances.append(self)

        def search(self, *args, **kwargs):
            raise AssertionError("cancelled flow should not call search()")

        def close(self):
            self.closed = True

        def is_manual_mode(self):
            return False

    monkeypatch.setattr("ui.workers.FlightSearcher", _FakeSearcher)

    dep = (datetime.now() + timedelta(days=7)).strftime("%Y%m%d")
    worker = DateRangeWorker("ICN", "NRT", [dep], 0, 1, max_results=10)

    call_count = {"n": 0}

    def _fake_is_cancelled():
        call_count["n"] += 1
        return call_count["n"] >= 2

    worker.is_cancelled = _fake_is_cancelled
    worker.run()

    if _FakeSearcher.instances:
        assert all(instance.closed is True for instance in _FakeSearcher.instances)
    assert worker._active_searchers == set()


def test_search_worker_cancel_before_run_does_not_search(monkeypatch):
    calls = {"search": 0, "close": 0}

    class _FakeSearcher:
        def __init__(self, *args, **kwargs):
            return None

        def search(self, *args, **kwargs):
            calls["search"] += 1
            return []

        def close(self):
            calls["close"] += 1

        def is_manual_mode(self):
            return False

    monkeypatch.setattr("ui.workers.FlightSearcher", _FakeSearcher)

    worker = SearchWorker("ICN", "NRT", "20260301", None, 1, max_results=10)
    worker.cancel()
    worker.run()

    assert calls["search"] == 0
    assert calls["close"] >= 1


def test_api_first_domestic_round_trip_uses_combination_path(monkeypatch):
    """Domestic round-trip must not early-return one-way outbound API lists."""
    from scraping.search_flow.api_first import _try_api_first_extraction
    from scraping.models import FlightResult

    class _FakePage:
        def evaluate(self, *_args, **_kwargs):
            return []

    scraper = PlaywrightScraper()
    cast(Any, scraper).page = _FakePage()
    called = {"round_trip": False, "one_way": False}

    def _fake_round_trip(*_args, **_kwargs):
        called["round_trip"] = True
        return [
            FlightResult(
                airline="제주항공",
                price=70000,
                departure_time="07:00",
                arrival_time="08:10",
                return_departure_time="18:00",
                return_arrival_time="19:10",
                is_round_trip=True,
                outbound_price=30000,
                return_price=40000,
                return_airline="대한항공",
            )
        ]

    def _fake_one_way():
        called["one_way"] = True
        return [
            FlightResult(
                airline="제주항공",
                price=30000,
                departure_time="07:00",
                arrival_time="08:10",
                is_round_trip=False,
            )
        ]

    monkeypatch.setattr(
        "scraping.search_flow.api_first._handle_domestic_round_trip",
        _fake_round_trip,
    )
    monkeypatch.setattr(scraper, "_extract_domestic_prices", _fake_one_way)
    monkeypatch.setattr(
        "scraping.search_flow.api_first.scraper_config.SEARCH_PAGE_STABILIZE_SECONDS",
        0,
    )

    results = _try_api_first_extraction(
        scraper,
        is_domestic=True,
        is_round_trip=True,
        log=lambda _m: None,
        time_module=SimpleNamespace(sleep=lambda *_a, **_k: None),
        max_results=10,
        background_mode=True,
    )

    assert called["round_trip"] is True
    assert called["one_way"] is False
    assert results and results[0].is_round_trip is True
    assert results[0].price == 70000


def test_combine_round_trip_preserves_airports_and_seats():
    scraper = PlaywrightScraper()
    outbound = [
        {
            "key": "o1",
            "airline": "제주항공",
            "price": 30000,
            "depTime": "07:30",
            "arrTime": "08:40",
            "stops": 0,
            "flightNumber": "7C111",
            "depAirport": "GMP",
            "arrAirport": "CJU",
            "seatAvailability": 4,
            "benefitPrice": 0,
            "benefitLabel": "",
        }
    ]
    inbound = [
        {
            "key": "i1",
            "airline": "대한항공",
            "price": 40000,
            "depTime": "18:10",
            "arrTime": "19:20",
            "stops": 0,
            "flightNumber": "KE2001",
            "depAirport": "CJU",
            "arrAirport": "GMP",
            "seatAvailability": 2,
            "benefitPrice": 0,
            "benefitLabel": "",
        }
    ]
    combined = scraper._combine_domestic_round_trip(outbound, inbound, max_results=5)
    assert len(combined) == 1
    assert combined[0].departure_airport == "GMP"
    assert combined[0].arrival_airport == "CJU"
    assert combined[0].return_departure_airport == "CJU"
    assert combined[0].return_arrival_airport == "GMP"
    assert combined[0].seat_availability == 2


def test_domestic_api_retries_once_on_invalid_cache_search_key(monkeypatch):
    from scraping.domestic.api import extract_domestic_api_flights_data

    scraper = PlaywrightScraper()
    cast(Any, scraper).page = object()
    scraper._last_search_context = {"cabin_class": "ECONOMY"}
    scraper._search_metrics = {}
    calls: list[str] = []

    monkeypatch.setattr(
        "scraping.domestic.api.resolve_search_key",
        lambda *_args, **_kwargs: "DOMESTIC::expired",
    )
    monkeypatch.setattr(
        "scraping.domestic.api.wait_for_search_key",
        lambda *_args, **_kwargs: "DOMESTIC::fresh",
    )

    def _fake_fetch(_scraper, search_key, **_kwargs):
        calls.append(search_key)
        if search_key == "DOMESTIC::expired":
            return {
                "code": "INVALID_CACHE_SEARCH_KEY",
                "title": "만료",
                "message": "해당 항공편 조회시간이 경과되었습니다.",
            }
        return {
            "page": {"pageSize": 20, "totalCount": 1},
            "items": [
                {
                    "key": "ok",
                    "schedule": {
                        "departureAt": "2026-03-01T09:00:00",
                        "arrivalAt": "2026-03-01T10:00:00",
                        "marketingCarrier": "7C",
                        "flightNumber": "7C101",
                    },
                    "fares": [{"totalPrice": 50000}],
                    "seatAvailability": 3,
                }
            ],
        }

    monkeypatch.setattr("scraping.domestic.api._fetch_domestic_search_page", _fake_fetch)

    items, meta = extract_domestic_api_flights_data(scraper)

    assert calls == ["DOMESTIC::expired", "DOMESTIC::fresh"]
    assert len(items) == 1
    assert items[0]["price"] == 50000
    assert items[0]["seatAvailability"] == 3
    assert meta["fetched_pages"] == 1
    assert scraper._search_metrics.get("api_key_retry_count") == 1


def test_domestic_api_pagination_respects_page_cap(monkeypatch):
    calls = []
    scraper = PlaywrightScraper()
    cast(Any, scraper).page = object()
    scraper._last_search_context = {"cabin_class": "ECONOMY"}

    monkeypatch.setattr("scraping.domestic.api.resolve_search_key", lambda *_args, **_kwargs: "DOMESTIC::cap")
    monkeypatch.setattr("scraping.domestic.api.scraper_config.DOMESTIC_API_MAX_PAGES", 2)

    def _fake_fetch(_scraper, _url, *, method="GET", body=None):
        page_number = int((body or {}).get("pageNumber", 1))
        calls.append(page_number)
        return {
            "page": {"pageSize": 20, "totalCount": 100},
            "items": [
                {
                    "key": f"flight-{page_number}",
                    "schedule": {
                        "departureAt": f"2026-03-01T{page_number + 7:02d}:00:00",
                        "arrivalAt": f"2026-03-01T{page_number + 8:02d}:00:00",
                        "marketingCarrier": "KE",
                        "flightNumber": f"{100 + page_number}",
                    },
                    "fares": [{"totalPrice": 100000 + page_number}],
                }
            ],
        }

    monkeypatch.setattr("scraping.domestic.api.page_fetch_json", _fake_fetch)

    items, metadata = extract_domestic_api_flights_data(scraper)

    assert calls == [1, 2]
    assert len(items) == 2
    assert metadata["pages_truncated"] is True
    assert metadata["page_cap"] == 2
    assert metadata["total_pages_estimated"] == 5


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


def test_domestic_prewait_failure_is_not_final_after_later_api_success(monkeypatch):
    keys = iter(["", "DOMESTIC::ok"])
    scraper = PlaywrightScraper()
    cast(Any, scraper).page = object()
    scraper._last_search_context = {"cabin_class": "ECONOMY"}
    scraper._search_metrics = {}

    monkeypatch.setattr("scraping.domestic.api.resolve_search_key", lambda *_args, **_kwargs: next(keys))

    def _fake_fetch(_scraper, _url, *, method="GET", body=None):
        return {
            "page": {"pageSize": 20, "totalCount": 1},
            "items": [
                {
                    "key": "flight-ok",
                    "schedule": {
                        "departureAt": "2026-03-01T09:00:00",
                        "arrivalAt": "2026-03-01T10:00:00",
                        "marketingCarrier": "KE",
                        "flightNumber": "123",
                    },
                    "fares": [{"totalPrice": 100000}],
                }
            ],
        }

    monkeypatch.setattr("scraping.domestic.api.page_fetch_json", _fake_fetch)

    assert extract_domestic_flights_data(scraper) == []
    assert scraper._manual_reason == "domestic_api_key_missing"

    items = extract_domestic_flights_data(scraper)

    assert items
    assert scraper._manual_reason == ""
    assert "api_failure_reason" not in scraper._search_metrics
    assert scraper._search_metrics["prewait_api_failure_reason"] == "domestic_api_key_missing"


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


def test_domestic_topk_combination_matches_naive_ordering():
    scraper = PlaywrightScraper()
    max_results = 7
    outbound = [
        {"airline": "A", "price": 100000 + i * 1000, "depTime": f"0{i}:00", "arrTime": f"1{i}:00", "stops": i % 2}
        for i in range(8)
    ]
    inbound = [
        {"airline": "B", "price": 120000 + j * 1500, "depTime": f"1{j}:30", "arrTime": f"2{j}:30", "stops": j % 2}
        for j in range(8)
    ]

    top_outbound = sorted(outbound, key=lambda x: x["price"])[: scraper_config.DOMESTIC_COMBINATION_TOP_N]
    top_inbound = sorted(inbound, key=lambda x: x["price"])[: scraper_config.DOMESTIC_COMBINATION_TOP_N]
    seen = set()
    naive = []
    for ob in top_outbound:
        for ret in top_inbound:
            price = ob["price"] + ret["price"]
            key = (ob["airline"], ret["airline"], price, ob["depTime"], ret["depTime"])
            if key in seen:
                continue
            seen.add(key)
            naive.append(key)
    naive.sort(key=lambda x: x[2])
    naive = naive[:max_results]

    combined = scraper._combine_domestic_round_trip(outbound, inbound, max_results=max_results)
    combined_keys = [
        (f.airline, f.return_airline, f.price, f.departure_time, f.return_departure_time)
        for f in combined
    ]

    assert combined_keys == naive


def test_enter_manual_mode_reinitializes_when_session_missing(monkeypatch):
    scraper = PlaywrightScraper()
    scraper.page = None
    scraper.context = None
    scraper.browser = None

    calls = {"init": 0, "goto": 0}

    class _FakePage(_PlaywrightPageStubMixin):
        def goto(self, *args, **kwargs):
            calls["goto"] += 1

    class _FakeContext:
        def new_page(self):
            return _FakePage()

    def _fake_init_browser(*args, **kwargs):
        calls["init"] += 1
        cast(Any, scraper).context = _FakeContext()
        cast(Any, scraper).browser = object()

    monkeypatch.setattr(scraper, "_init_browser", _fake_init_browser)
    monkeypatch.setattr(scraper, "_wait_for_results", lambda *args, **kwargs: {"found": True})
    monkeypatch.setattr(scraper, "close", lambda: None)

    entered = scraper._enter_manual_mode(
        url="https://example.com/search",
        profile_dir="playwright_profile",
        is_domestic=False,
        log_func=lambda _msg: None,
        reopen_visible=False,
    )

    assert entered is True
    assert scraper.manual_mode is True
    assert calls["init"] == 1
    assert calls["goto"] == 1


def test_flight_searcher_uses_cache_for_same_query(monkeypatch):
    monkeypatch.setattr(scraper_config, "ENABLE_SEARCH_CACHE", True)
    FlightSearcher.clear_cache()

    class _FakeSource:
        source_id = "fake"
        metadata = {}

        def __init__(self):
            self.calls = 0

        def build_search_url(self, params):
            return "https://example.test"

        def search(self, *args, **kwargs):
            self.calls += 1
            return [FlightResult(airline="CacheAir", price=150000, departure_time="10:00", arrival_time="12:00")]

        def extract_manual(self):
            return []

        def is_manual_mode(self):
            return False

        def close(self):
            return None

    searcher = FlightSearcher()
    fake_source = _FakeSource()
    searcher.source = fake_source
    dep = (datetime.now() + timedelta(days=7)).strftime("%Y%m%d")

    first = searcher.search("ICN", "NRT", dep, None, 1, "ECONOMY", max_results=20, progress_callback=None)
    second = searcher.search("ICN", "NRT", dep, None, 1, "ECONOMY", max_results=20, progress_callback=None)

    assert first and second
    assert fake_source.calls == 1
    assert second[0].price == first[0].price

    FlightSearcher.clear_cache()


def test_flight_searcher_cache_expires_after_ttl(monkeypatch):
    monkeypatch.setattr(scraper_config, "ENABLE_SEARCH_CACHE", True)
    monkeypatch.setattr(scraper_config, "SEARCH_CACHE_TTL_SECONDS", 1)
    FlightSearcher.clear_cache()

    class _FakeSource:
        source_id = "fake"
        metadata = {}

        def __init__(self):
            self.calls = 0

        def build_search_url(self, params):
            return "https://example.test"

        def search(self, *args, **kwargs):
            self.calls += 1
            return [
                FlightResult(
                    airline="CacheAir",
                    price=120000 + self.calls,
                    departure_time="09:00",
                    arrival_time="11:00",
                )
            ]

        def extract_manual(self):
            return []

        def is_manual_mode(self):
            return False

        def close(self):
            return None

    searcher = FlightSearcher()
    fake_source = _FakeSource()
    searcher.source = fake_source
    dep = (datetime.now() + timedelta(days=8)).strftime("%Y%m%d")

    first = searcher.search("ICN", "NRT", dep, None, 1, "ECONOMY", max_results=20, progress_callback=None)

    with FlightSearcher._cache_lock:
        for key, (saved_at, payload) in list(FlightSearcher._search_cache.items()):
            FlightSearcher._search_cache[key] = (saved_at - 5, payload)

    second = searcher.search("ICN", "NRT", dep, None, 1, "ECONOMY", max_results=20, progress_callback=None)

    assert first and second
    assert fake_source.calls == 2
    assert second[0].price != first[0].price

    FlightSearcher.clear_cache()


def test_search_worker_passes_force_refresh(monkeypatch):
    calls = {"force_refresh": None}

    class _FakeSearcher:
        def search(self, *args, **kwargs):
            calls["force_refresh"] = kwargs.get("force_refresh")
            return []

        def close(self):
            return None

        def is_manual_mode(self):
            return False

    monkeypatch.setattr("ui.workers.FlightSearcher", _FakeSearcher)

    worker = SearchWorker("ICN", "NRT", "20260301", None, 1, max_results=10, force_refresh=True)
    worker.run()

    assert calls["force_refresh"] is True


def test_search_worker_emits_error_on_manual_mode_activation_failure(monkeypatch):
    class _FakeSearcher:
        def search(self, *args, **kwargs):
            raise ManualModeActivationError("manual activation failed")

        def close(self):
            return None

        def is_manual_mode(self):
            return False

    monkeypatch.setattr("ui.workers.FlightSearcher", _FakeSearcher)

    worker = SearchWorker("ICN", "NRT", "20260301", None, 1, max_results=10)
    errors = []
    worker.error.connect(lambda msg: errors.append(msg))
    worker.run()

    assert errors
    assert "manual activation failed" in errors[0]


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


def test_domestic_api_path_paginates_and_normalizes_results():
    class _FakePage:
        def __init__(self):
            self.fetch_calls = 0
            self.fetch_scripts = []

        def evaluate(self, script):
            if "performance.getEntriesByType('resource')" in script and "DOMESTIC::" in script:
                return ["DOMESTIC::outbound"]
            if "fetch(" in script and "/domestic/flights/search/DOMESTIC::outbound" in script:
                self.fetch_scripts.append(script)
                self.fetch_calls += 1
                if self.fetch_calls == 1:
                    return {
                        "page": {"currentPage": 1, "pageSize": 20, "totalCount": 45},
                        "items": [
                            {
                                "key": "F1",
                                "schedule": {
                                    "marketingCarrier": "7C",
                                    "flightNumber": "7C123",
                                    "departureAt": "2026-05-15T07:30:00",
                                    "arrivalAt": "2026-05-15T08:40:00",
                                },
                                "seatAvailability": 7,
                                "fares": [
                                    {
                                        "totalPrice": 35000,
                                        "benefits": [
                                            {
                                                "discountedPrice": 33000,
                                                "cardCashback": {
                                                    "cardName": "KB국민",
                                                    "rate": 10,
                                                },
                                            }
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                if self.fetch_calls == 2:
                    return {
                        "page": {"currentPage": 2, "pageSize": 20, "totalCount": 45},
                        "items": [
                            {
                                "key": "F2",
                                "schedule": {
                                    "marketingCarrier": "KE",
                                    "flightNumber": "KE1001",
                                    "departureAt": "2026-05-15T09:00:00",
                                    "arrivalAt": "2026-05-15T10:10:00",
                                },
                                "seatAvailability": 3,
                                "fares": [{"totalPrice": 42000, "benefits": []}],
                            }
                        ],
                    }
                return {
                    "page": {"currentPage": 3, "pageSize": 20, "totalCount": 45},
                    "items": [
                        {
                            "key": "F3",
                            "schedule": {
                                "marketingCarrier": "LJ",
                                "flightNumber": "LJ201",
                                "departureAt": "2026-05-15T11:15:00",
                                "arrivalAt": "2026-05-15T12:20:00",
                            },
                            "seatAvailability": 9,
                            "fares": [{"totalPrice": 39000, "benefits": []}],
                        }
                    ],
                }
            if "const candidates = document.querySelectorAll(" in script:
                raise AssertionError("DOM fallback should not run when domestic API succeeds")
            raise AssertionError(f"Unexpected script: {script[:120]}")

    scraper = PlaywrightScraper()
    page = _FakePage()
    cast(Any, scraper).page = page
    cast(Any, scraper)._last_search_context = {
        "origin": "GMP",
        "destination": "CJU",
        "departure_date": "20260515",
        "return_date": None,
        "adults": 1,
        "cabin_class": "ECONOMY",
        "child": 0,
        "infant": 0,
        "is_domestic": True,
    }

    results = scraper._extract_domestic_prices()

    assert [result.price for result in results] == [35000, 39000, 42000]
    assert page.fetch_scripts
    assert all('\\"byCabins\\": [\\"ECONOMY\\"]' in script for script in page.fetch_scripts)
    assert all("byAirline" not in script for script in page.fetch_scripts)
    assert all(result.extraction_source == "domestic_api" for result in results)
    assert results[0].airline == "제주항공"
    assert results[0].flight_number == "7C123"
    assert results[0].benefit_price == 33000
    assert results[0].benefit_label == "KB국민 10% 캐시백 적용 시"
    assert results[1].airline == "진에어"
    assert results[2].airline == "대한항공"
    assert scraper._search_metrics["api_total_count"] == 45
    assert scraper._search_metrics["fetched_pages"] == 3
    assert scraper._search_metrics["api_item_count"] == 3


def test_domestic_round_trip_return_key_missing_falls_back_to_dom(monkeypatch):
    class _FakePage:
        def evaluate(self, _script):
            return True

    scraper = PlaywrightScraper()
    cast(Any, scraper).page = _FakePage()
    outbound = [
        {
            "airline": "제주항공",
            "price": 30000,
            "depTime": "07:30",
            "arrTime": "08:40",
            "stops": 0,
            "flightNumber": "7C123",
        }
    ]
    inbound = [
        {
            "airline": "대한항공",
            "price": 45000,
            "depTime": "18:10",
            "arrTime": "19:20",
            "stops": 0,
            "flightNumber": "KE2001",
        }
    ]

    monkeypatch.setattr(
        "scraping.playwright_search.find_latest_search_key",
        lambda *_args, **_kwargs: "DOMESTIC::outbound",
    )
    monkeypatch.setattr(
        "scraping.playwright_search.wait_for_search_key",
        lambda *_args, **_kwargs: "",
    )
    monkeypatch.setattr(
        scraper,
        "_extract_domestic_api_flights_data",
        lambda **kwargs: (
            outbound,
            {"total_count": len(outbound), "fetched_pages": 1},
        ),
    )
    monkeypatch.setattr(scraper, "_wait_for_domestic_return_view", lambda: True)
    monkeypatch.setattr(scraper, "_extract_domestic_dom_flights_data", lambda: inbound)

    logs = []
    results = _handle_domestic_round_trip(
        scraper,
        logs.append,
        max_results=5,
        background_mode=False,
        time_module=SimpleNamespace(sleep=lambda *_args, **_kwargs: None),
    )

    assert results is not None
    assert len(results) == 1
    assert results[0].price == 75000
    assert results[0].return_airline == "대한항공"
    assert scraper._manual_reason == "domestic_return_key_missing"
    assert scraper._search_metrics["api_total_count"] == 2
    assert scraper._search_metrics["fetched_pages"] == 1
    assert scraper._search_metrics["api_item_count"] == 2
    assert scraper._search_metrics["outbound_clicked"] is True


def test_domestic_round_trip_retries_next_candidate_on_click_miss(monkeypatch):
    class _FakePage:
        def __init__(self):
            self.detail_clicks = 0

        def evaluate(self, script):
            # Detail-click scripts contain the scored matcher; generic fallback always fails.
            if "const scored" in script:
                self.detail_clicks += 1
                # First candidate misses, second candidate hits.
                return self.detail_clicks >= 2
            return False

    scraper = PlaywrightScraper()
    page = _FakePage()
    cast(Any, scraper).page = page
    outbound = [
        {
            "airline": "제주항공",
            "price": 30000,
            "depTime": "07:30",
            "arrTime": "08:40",
            "stops": 0,
            "flightNumber": "7C111",
        },
        {
            "airline": "진에어",
            "price": 32000,
            "depTime": "09:00",
            "arrTime": "10:10",
            "stops": 0,
            "flightNumber": "LJ222",
        },
    ]
    inbound = [
        {
            "airline": "대한항공",
            "price": 40000,
            "depTime": "18:10",
            "arrTime": "19:20",
            "stops": 0,
            "flightNumber": "KE2001",
        }
    ]

    monkeypatch.setattr(
        "scraping.playwright_search.find_latest_search_key",
        lambda *_args, **_kwargs: "DOMESTIC::outbound",
    )
    monkeypatch.setattr(
        "scraping.playwright_search.wait_for_search_key",
        lambda *_args, **_kwargs: "DOMESTIC::return",
    )
    monkeypatch.setattr(
        scraper,
        "_extract_domestic_api_flights_data",
        lambda **kwargs: (
            (outbound, {"total_count": 2, "fetched_pages": 1})
            if kwargs.get("search_key") == "DOMESTIC::outbound"
            else (inbound, {"total_count": 1, "fetched_pages": 1})
        ),
    )
    monkeypatch.setattr(scraper, "_wait_for_domestic_return_view", lambda: True)

    results = _handle_domestic_round_trip(
        scraper,
        lambda _msg: None,
        max_results=5,
        background_mode=False,
        time_module=SimpleNamespace(sleep=lambda *_args, **_kwargs: None),
    )

    assert results is not None
    # All outbound legs are still combined with the collected return leg.
    assert len(results) == 2
    assert results[0].price == 70000
    assert results[1].price == 72000
    assert scraper._search_metrics["outbound_click_attempts"] == 2
    assert scraper._search_metrics["outbound_clicked"] is True


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


def test_multi_search_worker_runs_with_parallelism(monkeypatch):
    lock = threading.Lock()
    state = {"active": 0, "max_active": 0}

    class _FakeSearcher:
        def search(self, *args, **kwargs):
            with lock:
                state["active"] += 1
                state["max_active"] = max(state["max_active"], state["active"])
            time.sleep(0.05)
            with lock:
                state["active"] -= 1
            return []

        def close(self):
            return None

        def is_manual_mode(self):
            return False

    monkeypatch.setattr("ui.workers.FlightSearcher", _FakeSearcher)

    worker = MultiSearchWorker(
        "ICN",
        ["NRT", "HND", "KIX", "FUK"],
        (datetime.now() + timedelta(days=7)).strftime("%Y%m%d"),
        None,
        1,
        max_results=10,
    )

    captured = {}
    worker.all_finished.connect(lambda data: captured.update(data))
    worker.run()

    assert len(captured) == 4
    assert state["max_active"] >= 2


def test_multi_search_worker_cancel_cancels_pending_futures(monkeypatch):
    state = {"started": 0}

    class _FakeSearcher:
        instances = []

        def __init__(self, *args, **kwargs):
            self.closed = False
            _FakeSearcher.instances.append(self)

        def search(self, *args, **kwargs):
            state["started"] += 1
            start = time.time()
            while time.time() - start < 2.0:
                if self.closed:
                    return []
                time.sleep(0.01)
            return []

        def close(self):
            self.closed = True

        def is_manual_mode(self):
            return False

    monkeypatch.setattr("ui.workers.FlightSearcher", _FakeSearcher)

    worker = MultiSearchWorker(
        "ICN",
        ["NRT", "HND", "KIX", "FUK", "CTS", "OKA", "TPE", "BKK"],
        (datetime.now() + timedelta(days=7)).strftime("%Y%m%d"),
        None,
        1,
        max_results=10,
    )

    t = threading.Thread(target=worker.run)
    start = time.time()
    t.start()
    time.sleep(0.05)
    worker.cancel()
    t.join(timeout=1.0)
    elapsed = time.time() - start

    assert t.is_alive() is False
    assert elapsed < 1.0
    assert state["started"] < len(worker.destinations)
    assert any(instance.closed for instance in _FakeSearcher.instances)


def test_multi_search_worker_passes_cabin_class(monkeypatch):
    observed = []
    background_modes = []

    class _FakeSearcher:
        def search(self, *args, **kwargs):
            observed.append(kwargs.get("cabin_class") or (args[5] if len(args) > 5 else None))
            background_modes.append(kwargs.get("background_mode"))
            return []

        def close(self):
            return None

        def is_manual_mode(self):
            return False

    monkeypatch.setattr("ui.workers.FlightSearcher", _FakeSearcher)

    worker = MultiSearchWorker(
        "ICN",
        ["NRT", "HND"],
        (datetime.now() + timedelta(days=7)).strftime("%Y%m%d"),
        None,
        1,
        "BUSINESS",
        max_results=10,
    )
    worker.run()
    assert observed
    assert set(observed) == {"BUSINESS"}
    assert set(background_modes) == {True}


def test_date_range_worker_passes_cabin_class(monkeypatch):
    observed = []
    background_modes = []

    class _FakeSearcher:
        def search(self, *args, **kwargs):
            observed.append(kwargs.get("cabin_class") or (args[5] if len(args) > 5 else None))
            background_modes.append(kwargs.get("background_mode"))
            return []

        def close(self):
            return None

        def is_manual_mode(self):
            return False

    monkeypatch.setattr("ui.workers.FlightSearcher", _FakeSearcher)
    dep = (datetime.now() + timedelta(days=7)).strftime("%Y%m%d")
    worker = DateRangeWorker("ICN", "NRT", [dep], 0, 1, "FIRST", max_results=10)
    worker.run()
    assert observed == ["FIRST"]
    assert background_modes == [True]


def test_date_range_worker_cancel_cancels_pending_futures(monkeypatch):
    state = {"started": 0}

    class _FakeSearcher:
        instances = []

        def __init__(self, *args, **kwargs):
            self.closed = False
            _FakeSearcher.instances.append(self)

        def search(self, *args, **kwargs):
            state["started"] += 1
            start = time.time()
            while time.time() - start < 2.0:
                if self.closed:
                    return []
                time.sleep(0.01)
            return []

        def close(self):
            self.closed = True

        def is_manual_mode(self):
            return False

    monkeypatch.setattr("ui.workers.FlightSearcher", _FakeSearcher)

    dep = datetime.now() + timedelta(days=7)
    dates = [(dep + timedelta(days=i)).strftime("%Y%m%d") for i in range(8)]
    worker = DateRangeWorker("ICN", "NRT", dates, 0, 1, max_results=10)

    t = threading.Thread(target=worker.run)
    start = time.time()
    t.start()
    time.sleep(0.05)
    worker.cancel()
    t.join(timeout=1.0)
    elapsed = time.time() - start

    assert t.is_alive() is False
    assert elapsed < 1.0
    assert state["started"] < len(dates)
    assert any(instance.closed for instance in _FakeSearcher.instances)


def test_alert_auto_check_worker_uses_alert_cabin_and_emits_hit(monkeypatch):
    class _Alert:
        def __init__(self):
            self.id = 1
            self.origin = "ICN"
            self.destination = "NRT"
            self.departure_date = (datetime.now() + timedelta(days=7)).strftime("%Y%m%d")
            self.return_date = None
            self.target_price = 150000
            self.cabin_class = "BUSINESS"
            self.adults = 2

    observed_cabins = []
    observed_adults = []
    background_modes = []
    cache_modes = []

    class _FakeSearcher:
        def search(self, *args, **kwargs):
            observed_cabins.append(kwargs.get("cabin_class"))
            observed_adults.append(kwargs.get("adults"))
            background_modes.append(kwargs.get("background_mode"))
            cache_modes.append(kwargs.get("cache_mode"))
            return [FlightResult(airline="A", price=120000, departure_time="10:00", arrival_time="12:00")]

        def close(self):
            return None

        def is_manual_mode(self):
            return False

    monkeypatch.setattr("ui.workers.FlightSearcher", _FakeSearcher)

    worker = AlertAutoCheckWorker([_Alert()])
    hits = []
    worker.alert_hit.connect(lambda *args: hits.append(args))
    worker.run()

    assert observed_cabins == ["BUSINESS"]
    assert observed_adults == [2]
    assert background_modes == [True]
    assert cache_modes == ["alert"]
    assert len(hits) == 1


def test_alert_auto_check_worker_emits_failure_signal(monkeypatch):
    class _Alert:
        def __init__(self):
            self.id = 9
            self.origin = "ICN"
            self.destination = "NRT"
            self.departure_date = (datetime.now() + timedelta(days=7)).strftime("%Y%m%d")
            self.return_date = None
            self.target_price = 150000
            self.cabin_class = "ECONOMY"
            self.adults = 1

    class _FakeSearcher:
        def search(self, *args, **kwargs):
            raise RuntimeError("boom")

        def close(self):
            return None

        def is_manual_mode(self):
            return False

    monkeypatch.setattr("ui.workers.FlightSearcher", _FakeSearcher)

    worker = AlertAutoCheckWorker([_Alert()])
    failures = []
    checked = []
    worker.alert_check_failed.connect(lambda *args: failures.append(args))
    worker.alert_checked.connect(lambda *args: checked.append(args))
    worker.run()

    assert checked == []
    assert len(failures) == 1
    assert failures[0][0] == 9
    assert failures[0][1] == "ICN"


def test_alert_auto_check_worker_emits_no_result_signal(monkeypatch):
    class _Alert:
        def __init__(self):
            self.id = 10
            self.origin = "ICN"
            self.destination = "NRT"
            self.departure_date = (datetime.now() + timedelta(days=7)).strftime("%Y%m%d")
            self.return_date = None
            self.target_price = 150000
            self.cabin_class = "ECONOMY"
            self.adults = 1

    class _FakeSearcher:
        def search(self, *args, **kwargs):
            return []

        def close(self):
            return None

        def is_manual_mode(self):
            return False

    monkeypatch.setattr("ui.workers.FlightSearcher", _FakeSearcher)

    worker = AlertAutoCheckWorker([_Alert()])
    no_results = []
    checked = []
    worker.alert_no_result.connect(lambda *args: no_results.append(args))
    worker.alert_checked.connect(lambda *args: checked.append(args))
    worker.run()

    assert checked == []
    assert no_results == [(10, "ICN", "NRT")]


def test_alert_auto_check_worker_cancel_closes_active_searcher():
    class _FakeSearcher:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    worker = AlertAutoCheckWorker([])
    fake = _FakeSearcher()
    worker._set_active_searcher(fake)
    worker.cancel()
    assert fake.closed is True


def test_domestic_round_trip_dedup_preserves_distinct_flight_numbers():
    scraper = PlaywrightScraper()
    outbound = [
        {
            "key": "OUT-1",
            "airline": "A",
            "price": 50000,
            "depTime": "07:00",
            "arrTime": "08:00",
            "stops": 0,
            "flightNumber": "A100",
        },
        {
            "key": "OUT-2",
            "airline": "A",
            "price": 50000,
            "depTime": "07:00",
            "arrTime": "08:10",
            "stops": 0,
            "flightNumber": "A101",
        },
    ]
    inbound = [
        {
            "key": "IN-1",
            "airline": "B",
            "price": 60000,
            "depTime": "18:00",
            "arrTime": "19:00",
            "stops": 0,
            "flightNumber": "B200",
        }
    ]

    combined = scraper._combine_domestic_round_trip(outbound, inbound, max_results=10)

    assert len(combined) == 2
    assert {flight.flight_number for flight in combined} == {"A100", "A101"}


def test_playwright_search_retries_on_network_error(monkeypatch):
    class _FakePage(_PlaywrightPageStubMixin):
        def __init__(self):
            self.calls = 0

        def goto(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise Exception("temporary network failure")

    class _FakeContext:
        def __init__(self, page):
            self._page = page

        def new_page(self):
            return self._page

        def close(self):
            return None

    page = _FakePage()
    scraper = PlaywrightScraper()

    def _fake_init_browser(*_args, **_kwargs):
        cast(Any, scraper).context = _FakeContext(page)

    monkeypatch.setattr(scraper, "_init_browser", _fake_init_browser)
    monkeypatch.setattr(scraper, "_wait_for_results", lambda *_args, **_kwargs: {"found": True, "selector": "li[data-index]"})
    monkeypatch.setattr(
        scraper,
        "_extract_prices",
        lambda: [FlightResult(airline="A", price=100000, departure_time="10:00", arrival_time="12:00")],
    )
    monkeypatch.setattr(scraper, "close", lambda: None)
    monkeypatch.setattr("scraper_v2.time.sleep", lambda *_args, **_kwargs: None)

    results = scraper.search("ICN", "NRT", "20260301", None, adults=1, cabin_class="ECONOMY", max_results=10)

    assert len(results) == 1
    assert page.calls == 2


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


def test_domestic_one_way_search_uses_api_first_extractor(monkeypatch):
    class _FakePage(_PlaywrightPageStubMixin):
        def __init__(self):
            self.urls = []

        def goto(self, url, *_args, **_kwargs):
            self.urls.append(url)

    class _FakeContext:
        def __init__(self, page):
            self._page = page

        def new_page(self):
            return self._page

        def close(self):
            return None

    page = _FakePage()
    scraper = PlaywrightScraper()
    calls = {"domestic": 0}
    domestic_results = [
        FlightResult(
            airline="테스트항공",
            price=30000 + i,
            departure_time=f"{i % 24:02d}:{(i * 5) % 60:02d}",
            arrival_time=f"{(i + 1) % 24:02d}:{(i * 5 + 30) % 60:02d}",
            extraction_source="domestic_api",
            confidence=0.9,
        )
        for i in range(25)
    ]

    def _fake_init_browser(*_args, **_kwargs):
        cast(Any, scraper).context = _FakeContext(page)

    def _fake_domestic_extract():
        calls["domestic"] += 1
        return domestic_results

    monkeypatch.setattr(scraper, "_init_browser", _fake_init_browser)
    monkeypatch.setattr(scraper, "_wait_for_results", lambda *_args, **_kwargs: {"found": True, "selector": 'button:has-text("원")'})
    monkeypatch.setattr(scraper, "_extract_domestic_prices", _fake_domestic_extract)
    monkeypatch.setattr(scraper, "close", lambda: None)
    monkeypatch.setattr("scraping.playwright_scraper.time.sleep", lambda *_args, **_kwargs: None)

    results = scraper.search("GMP", "CJU", "2026-03-01", None, adults=1, cabin_class="ECONOMY", max_results=50)

    assert calls["domestic"] == 1
    assert len(results) == 25
    assert all(result.extraction_source == "domestic_api" for result in results)
    assert page.urls
    assert "20260301" in page.urls[0]
    assert "2026-03-01" not in page.urls[0]


def test_playwright_search_closes_between_network_retries(monkeypatch):
    class _FakePage(_PlaywrightPageStubMixin):
        def __init__(self):
            self.calls = 0

        def goto(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise Exception("temporary network failure")

    class _FakeContext:
        def __init__(self, page):
            self._page = page

        def new_page(self):
            return self._page

        def close(self):
            return None

    page = _FakePage()
    scraper = PlaywrightScraper()
    close_calls = {"count": 0}

    def _fake_init_browser(*_args, **_kwargs):
        cast(Any, scraper).context = _FakeContext(page)

    def _fake_close():
        close_calls["count"] += 1
        scraper.page = None
        scraper.context = None
        scraper.browser = None
        scraper.playwright = None
        scraper.manual_mode = False

    monkeypatch.setattr(scraper, "_init_browser", _fake_init_browser)
    monkeypatch.setattr(scraper, "_wait_for_results", lambda *_args, **_kwargs: {"found": True, "selector": "li[data-index]"})
    monkeypatch.setattr(
        scraper,
        "_extract_prices",
        lambda: [FlightResult(airline="A", price=100000, departure_time="10:00", arrival_time="12:00")],
    )
    monkeypatch.setattr(scraper, "close", _fake_close)
    monkeypatch.setattr("scraper_v2.time.sleep", lambda *_args, **_kwargs: None)

    results = scraper.search("ICN", "NRT", "20260301", None, adults=1, cabin_class="ECONOMY", max_results=10)

    assert len(results) == 1
    assert page.calls == 2
    assert close_calls["count"] >= 2


def test_playwright_background_mode_disables_manual_fallback(monkeypatch):
    class _FakePage:
        def goto(self, *_args, **_kwargs):
            return None

    class _FakeContext:
        def __init__(self):
            self._page = _FakePage()

        def new_page(self):
            return self._page

        def close(self):
            return None

    scraper = PlaywrightScraper()

    def _fake_init_browser(_log=None, _user_data_dir=None, headless=False):
        cast(Any, scraper).context = _FakeContext()

    monkeypatch.setattr(scraper, "_init_browser", _fake_init_browser)
    monkeypatch.setattr(scraper, "_wait_for_results", lambda *_args, **_kwargs: {"found": False, "selector": ""})
    monkeypatch.setattr(scraper, "close", lambda: None)

    results = scraper.search(
        "ICN",
        "NRT",
        "20260301",
        None,
        adults=1,
        cabin_class="ECONOMY",
        max_results=10,
        background_mode=True,
    )

    assert results == []
    assert scraper.manual_mode is False


def test_parallel_searcher_smoke_runs_without_nameerror(monkeypatch):
    class _FakeScraper:
        def search(self, *args, **kwargs):
            emit = kwargs.get("emit")
            if emit:
                emit("ok")
            return []

    class _FakeSearcher:
        def __init__(self):
            self.scraper = _FakeScraper()

        def close(self):
            return None

    monkeypatch.setattr("scraping.parallel.FlightSearcher", _FakeSearcher)

    searcher = ParallelSearcher(max_concurrent=1)
    result = searcher.search_multiple_destinations(
        "ICN",
        ["NRT"],
        (datetime.now() + timedelta(days=7)).strftime("%Y%m%d"),
    )

    assert result == {"NRT": []}
