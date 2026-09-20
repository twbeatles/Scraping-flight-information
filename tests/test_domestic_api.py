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
from scraping.playwright_search import _handle_domestic_round_trip
from scraping.domestic.results import extract_domestic_flights_data
from scraping.domestic.api import extract_domestic_api_flights_data

class _PlaywrightPageStubMixin:
    def on(self, _event, _handler):
        return None

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

