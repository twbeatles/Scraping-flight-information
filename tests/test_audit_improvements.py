from typing import Any, Callable, cast

import pytest
import scraper_config

from core.search_params import normalize_search_params
from scraping.domestic.results import build_domestic_results
from scraping.errors import SearchCancelledError
from scraping.models import FlightResult, effective_flight_price
from scraping.interpark.adapter import InterparkAdapterConfig, get_interpark_adapter
from scraping.interpark.network_listener import attach_interpark_response_listener
from scraping.playwright_api import (
    cache_search_key,
    extract_search_key_from_payload,
    extract_search_key_from_url,
    find_search_keys,
    resolve_search_key,
)
from scraper_v2 import FlightSearcher
from scraping.playwright_scraper import PlaywrightScraper
from scraping.search_cancel import raise_if_search_cancelled, set_cancel_check
from scraping.search_sources import InterparkAirSource


def test_normalize_search_params_rejects_invalid_date():
    normalized = normalize_search_params({"origin": "ICN", "dest": "NRT", "dep": "not-a-date"})
    assert normalized["dep"] == ""


def test_effective_flight_price_prefers_benefit_when_lower():
    flight = FlightResult(airline="제주항공", price=31500, benefit_price=31200)
    assert effective_flight_price(flight) == 31200


def test_domestic_one_way_dedup_preserves_distinct_benefit_prices():
    items = [
        {
            "key": "A",
            "airline": "제주항공",
            "price": 31500,
            "benefitPrice": 31200,
            "benefitLabel": "카드 1%",
            "depTime": "07:00",
            "arrTime": "08:05",
            "flightNumber": "7C101",
            "stops": 0,
        },
        {
            "key": "B",
            "airline": "제주항공",
            "price": 31500,
            "benefitPrice": 30000,
            "benefitLabel": "카드 3%",
            "depTime": "07:00",
            "arrTime": "08:05",
            "flightNumber": "7C101",
            "stops": 0,
        },
    ]
    results = build_domestic_results(items)
    assert len(results) == 2


def test_cache_search_key_merged_with_performance_keys():
    class _FakePage:
        def evaluate(self, script):
            assert "performance.getEntriesByType('resource')" in script
            return ["INTERNATIONAL::perf-key"]

    scraper = PlaywrightScraper()
    cast(Any, scraper).page = _FakePage()
    cache_search_key(scraper, trip_kind="international", key="INTERNATIONAL::cached-key")

    assert find_search_keys(scraper, trip_kind="international") == [
        "INTERNATIONAL::cached-key",
        "INTERNATIONAL::perf-key",
    ]
    assert resolve_search_key(scraper, trip_kind="international") == "INTERNATIONAL::perf-key"


def test_extract_search_key_from_payload_supports_common_fields():
    assert extract_search_key_from_payload({"key": "INTERNATIONAL::abc"}) == "INTERNATIONAL::abc"
    assert extract_search_key_from_payload({"searchKey": "DOMESTIC::xyz"}) == "DOMESTIC::xyz"


def test_raise_if_search_cancelled_raises():
    scraper = PlaywrightScraper()
    set_cancel_check(scraper, lambda: True)
    with pytest.raises(SearchCancelledError):
        raise_if_search_cancelled(scraper)


def test_extract_search_key_from_url_parses_domestic_and_international_paths():
    adapter = get_interpark_adapter()
    domestic_url = (
        f"{adapter.air_api_base}{adapter.domestic_search_api_path}"
        "DOMESTIC::abc123/extra"
    )
    international_url = (
        f"{adapter.air_api_base}{adapter.international_search_api_path}"
        "INTERNATIONAL::xyz789"
    )

    assert extract_search_key_from_url(domestic_url, adapter=adapter) == (
        "domestic",
        "DOMESTIC::abc123",
    )
    assert extract_search_key_from_url(international_url, adapter=adapter) == (
        "international",
        "INTERNATIONAL::xyz789",
    )
    assert extract_search_key_from_url("", adapter=adapter) == ("", "")


def test_get_interpark_adapter_exposes_canonical_api_paths():
    adapter = get_interpark_adapter()

    assert adapter.search_url_base == "https://travel.interpark.com/air/search"
    assert adapter.air_api_base.endswith("/inpark-air-web-api")
    assert adapter.domestic_search_api_path == "/domestic/flights/search/"
    assert adapter.international_search_api_path.endswith("/")
    assert adapter.status_path_suffix == "/status"
    assert "items" in adapter.domestic_result_buckets
    assert "bestFares" in adapter.international_result_buckets
    assert "key" in adapter.search_key_fields
    assert adapter.build_international_status_url("INTERNATIONAL::abc").endswith(
        "/INTERNATIONAL::abc/status"
    )
    assert adapter.build_domestic_result_url("DOMESTIC::abc").endswith("/DOMESTIC::abc")


class _FakeNetworkResponse:
    def __init__(self, url: str, *, ok: bool = True, payload: dict | None = None):
        self.url = url
        self.ok = ok
        self.headers = {"content-type": "application/json"}
        self._payload = payload or {}

    def json(self):
        return self._payload


class _FakeNetworkPage:
    def __init__(self):
        self._handlers: dict[str, Callable[[_FakeNetworkResponse], None]] = {}

    def on(self, event: str, handler: Callable[[_FakeNetworkResponse], None]):
        self._handlers[event] = handler

    def emit_response(self, response: _FakeNetworkResponse):
        handler = self._handlers.get("response")
        if handler is not None:
            handler(response)


def test_network_listener_caches_key_from_url_and_json_payload():
    adapter = get_interpark_adapter()
    scraper = PlaywrightScraper()
    page = _FakeNetworkPage()
    attach_interpark_response_listener(scraper, cast(Any, page), adapter=adapter)

    url_key_url = (
        f"{adapter.air_api_base}{adapter.domestic_search_api_path}"
        "DOMESTIC::url-key"
    )
    page.emit_response(_FakeNetworkResponse(url_key_url))
    assert resolve_search_key(scraper, trip_kind="domestic") == "DOMESTIC::url-key"
    assert scraper._search_metrics["api_key_sources"]["domestic"] == "network_url"

    json_key_url = f"{adapter.air_api_base}{adapter.international_search_api_path}page-1"
    page.emit_response(
        _FakeNetworkResponse(
            json_key_url,
            payload={"key": "INTERNATIONAL::json-key"},
        )
    )
    assert resolve_search_key(scraper, trip_kind="international") == "INTERNATIONAL::json-key"
    assert scraper._search_metrics["api_key_sources"]["international"] == "network_json"


def test_network_listener_attaches_once_per_page():
    adapter = get_interpark_adapter()
    scraper = PlaywrightScraper()
    page = _FakeNetworkPage()
    attach_interpark_response_listener(scraper, cast(Any, page), adapter=adapter)
    attach_interpark_response_listener(scraper, cast(Any, page), adapter=adapter)

    assert len(scraper._network_listener_page_ids) == 1


def test_wait_for_search_key_returns_existing_key_without_page_wait():
    from scraping.playwright_api import wait_for_search_key

    scraper = PlaywrightScraper()
    cast(Any, scraper).page = object()
    cache_search_key(scraper, trip_kind="domestic", key="DOMESTIC::ready")

    assert wait_for_search_key(scraper, trip_kind="domestic") == "DOMESTIC::ready"


def test_wait_for_search_key_excludes_known_keys():
    from scraping.playwright_api import wait_for_search_key

    scraper = PlaywrightScraper()
    cast(Any, scraper).page = object()
    cache_search_key(scraper, trip_kind="domestic", key="DOMESTIC::outbound")
    cache_search_key(scraper, trip_kind="domestic", key="DOMESTIC::return")

    assert (
        wait_for_search_key(
            scraper,
            trip_kind="domestic",
            exclude_keys={"DOMESTIC::outbound"},
        )
        == "DOMESTIC::return"
    )


def test_wait_for_search_key_returns_empty_on_stub_page_without_keys():
    from scraping.playwright_api import wait_for_search_key

    scraper = PlaywrightScraper()
    cast(Any, scraper).page = object()

    assert wait_for_search_key(scraper, trip_kind="domestic", timeout_seconds=1) == ""


def test_international_api_normalizer_maps_airport_baggage_and_meta():
    from scraping.international.normalizer import _normalize_international_api_item

    item = {
        "recommendationTag": "LOWEST_PRICE",
        "adultPrice": 144500,
        "schedules": [
            {
                "totalFlightTime": "PT2H10M",
                "addDay": 0,
                "stop": 0,
                "freeBaggage": {"unit": "WEIGHT_KG", "allowance": 15},
                "carrier": {"code": "WE", "name": "파라타항공"},
                "segments": [
                    {
                        "departure": {
                            "airport": {"code": "ICN"},
                            "at": "2026-09-11T09:50:00",
                        },
                        "arrival": {
                            "airport": {"code": "NRT"},
                            "at": "2026-09-11T12:00:00",
                        },
                    }
                ],
            }
        ],
        "fares": [
            {
                "adultPrice": 144500,
                "avail": 2,
                "items": [
                    {
                        "promotionPrinciple": {
                            "promotionName": "우리카드",
                        }
                    }
                ],
            }
        ],
    }

    result = _normalize_international_api_item(item)
    assert result is not None
    assert result.departure_airport == "ICN"
    assert result.arrival_airport == "NRT"
    assert result.baggage == "15kg"
    assert result.seat_availability == 2
    assert result.recommendation_tag == "LOWEST_PRICE"
    assert result.duration == "02시간 10분"
    assert "우리카드" in result.benefit_label


def test_export_includes_extended_airport_and_baggage_columns():
    from ui.export_helpers import flight_export_headers, flight_to_export_row

    flight = FlightResult(
        airline="대한항공",
        price=200000,
        departure_time="10:00",
        arrival_time="12:00",
        departure_airport="ICN",
        arrival_airport="HND",
        baggage="1개",
        seat_availability=4,
        recommendation_tag="LOWEST_PRICE",
        flight_number="KE701",
        duration="02시간 20분",
    )
    headers = flight_export_headers()
    row = dict(zip(headers, flight_to_export_row(flight)))
    assert row["출발공항"] == "ICN"
    assert row["도착공항"] == "HND"
    assert row["수하물"] == "1개"
    assert row["잔여석"] == 4
    assert row["편명"] == "KE701"


def test_result_table_shows_extended_fields_and_effective_price_badge(qapp):
    from ui.components_result_table import ResultTable

    del qapp
    table = ResultTable()
    cheap_benefit = FlightResult(
        airline="A",
        price=200000,
        benefit_price=100000,
        departure_time="10:00",
        arrival_time="12:00",
        departure_airport="ICN",
        arrival_airport="NRT",
        baggage="15kg",
        seat_availability=3,
    )
    expensive = FlightResult(
        airline="B",
        price=150000,
        departure_time="11:00",
        arrival_time="13:00",
        departure_airport="ICN",
        arrival_airport="HND",
        baggage="1개",
        seat_availability=1,
    )
    table.update_data([expensive, cheap_benefit])

    assert table.columnCount() == 12

    def _cell(row: int, col: int) -> str:
        item = table.item(row, col)
        return item.text() if item is not None else ""

    # effective price ranks cheap_benefit (100k) as best even if base price is higher
    assert "🏆" in _cell(0, 1) or "🏆" in _cell(1, 1)
    airport_cells = [_cell(r, 8) for r in range(2)]
    assert any("ICN" in cell and "NRT" in cell for cell in airport_cells)
    bag_cells = [_cell(r, 9) for r in range(2)]
    assert "15kg" in bag_cells
    seat_cells = [_cell(r, 10) for r in range(2)]
    assert "3" in seat_cells


def test_preference_alert_hit_modal_flag(tmp_path):
    from core.preferences import PreferenceManager

    prefs = PreferenceManager(filepath=str(tmp_path / "prefs.json"))
    assert prefs.get_alert_hit_modal_enabled() is True
    prefs.set_alert_hit_modal_enabled(False)
    assert prefs.get_alert_hit_modal_enabled() is False
    cfg = prefs.get_alert_auto_check()
    assert cfg.get("hit_modal_enabled") is False


def test_resolve_cache_mode_maps_background_and_explicit_alert():
    assert FlightSearcher._resolve_cache_mode(False) == "foreground"
    assert FlightSearcher._resolve_cache_mode(True) == "background"
    assert FlightSearcher._resolve_cache_mode(True, "alert") == "alert"


def test_cache_key_includes_child_and_infant_counts():
    base = FlightSearcher._build_cache_key("ICN", "NRT", "20260415", None, 1, "ECONOMY", 20)
    with_child = FlightSearcher._build_cache_key(
        "ICN", "NRT", "20260415", None, 1, "ECONOMY", 20, child=1, infant=0
    )
    assert base != with_child


def test_cache_ttl_policy_differs_by_mode(monkeypatch):
    monkeypatch.setattr(scraper_config, "ENABLE_SEARCH_CACHE", True)
    monkeypatch.setattr(scraper_config, "SEARCH_CACHE_TTL_SECONDS", 180)
    monkeypatch.setattr(scraper_config, "SEARCH_CACHE_TTL_BACKGROUND_SECONDS", 90)
    monkeypatch.setattr(scraper_config, "SEARCH_CACHE_TTL_ALERT_SECONDS", 45)
    FlightSearcher.clear_cache()

    cache_key = FlightSearcher._build_cache_key(
        "ICN", "NRT", "20260415", None, 1, "ECONOMY", 20, child=0, infant=0
    )
    cached = [FlightResult(airline="CacheAir", price=150000, departure_time="10:00", arrival_time="12:00")]
    FlightSearcher._store_cached_results(cache_key, cached)

    with FlightSearcher._cache_lock:
        saved_at, payload = FlightSearcher._search_cache[cache_key]
        FlightSearcher._search_cache[cache_key] = (saved_at - 60, payload)

    assert FlightSearcher._get_cached_results(cache_key, cache_mode="foreground") is not None
    assert FlightSearcher._get_cached_results(cache_key, cache_mode="background") is not None
    assert FlightSearcher._get_cached_results(cache_key, cache_mode="alert") is None
    FlightSearcher.clear_cache()


def test_interpark_air_source_normalizes_dest_key():
    source = InterparkAirSource()
    url = source.build_search_url(
        {
            "origin": "ICN",
            "dest": "NRT",
            "dep": "20260415",
            "adults": 2,
            "cabin_class": "BUSINESS",
        }
    )
    assert "c:SEL-c:TYO-20260415" in url
    assert "adult=2" in url
    assert "cabin=BUSINESS" in url