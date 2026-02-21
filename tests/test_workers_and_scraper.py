import threading
import time
from datetime import datetime, timedelta

import scraper_config
from scraper_v2 import PlaywrightScraper, FlightSearcher, FlightResult, ManualModeActivationError
from ui.workers import DateRangeWorker, MultiSearchWorker, SearchWorker


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

    assert _FakeSearcher.instances
    assert _FakeSearcher.instances[0].closed is True
    assert worker._active_searchers == set()


def test_international_dedup_key_preserves_distinct_return_details():
    class _FakePage:
        def evaluate(self, script):
            if script == "document.body.scrollHeight":
                return 100
            if script.startswith("window.scrollTo("):
                return None
            if "const cards = document.querySelectorAll('li[data-index]');" in script:
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
    scraper.page = _FakePage()

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

    class _FakePage:
        def goto(self, *args, **kwargs):
            calls["goto"] += 1

    class _FakeContext:
        def new_page(self):
            return _FakePage()

    def _fake_init_browser(*args, **kwargs):
        calls["init"] += 1
        scraper.context = _FakeContext()
        scraper.browser = object()

    monkeypatch.setattr(scraper, "_init_browser", _fake_init_browser)
    monkeypatch.setattr(scraper, "_wait_for_results", lambda *args, **kwargs: True)
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


def test_flight_searcher_uses_cache_for_same_query(monkeypatch):
    monkeypatch.setattr(scraper_config, "ENABLE_SEARCH_CACHE", True)
    FlightSearcher.clear_cache()

    class _FakeScraper:
        def __init__(self):
            self.calls = 0

        def search(self, *args, **kwargs):
            self.calls += 1
            return [FlightResult(airline="CacheAir", price=150000, departure_time="10:00", arrival_time="12:00")]

        def close(self):
            return None

        def is_manual_mode(self):
            return False

    searcher = FlightSearcher()
    fake_scraper = _FakeScraper()
    searcher.scraper = fake_scraper
    dep = (datetime.now() + timedelta(days=7)).strftime("%Y%m%d")

    first = searcher.search("ICN", "NRT", dep, None, 1, "ECONOMY", max_results=20, progress_callback=None)
    second = searcher.search("ICN", "NRT", dep, None, 1, "ECONOMY", max_results=20, progress_callback=None)

    assert first and second
    assert fake_scraper.calls == 1
    assert second[0].price == first[0].price

    FlightSearcher.clear_cache()


def test_flight_searcher_cache_expires_after_ttl(monkeypatch):
    monkeypatch.setattr(scraper_config, "ENABLE_SEARCH_CACHE", True)
    monkeypatch.setattr(scraper_config, "SEARCH_CACHE_TTL_SECONDS", 1)
    FlightSearcher.clear_cache()

    class _FakeScraper:
        def __init__(self):
            self.calls = 0

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

        def close(self):
            return None

        def is_manual_mode(self):
            return False

    searcher = FlightSearcher()
    fake_scraper = _FakeScraper()
    searcher.scraper = fake_scraper
    dep = (datetime.now() + timedelta(days=8)).strftime("%Y%m%d")

    first = searcher.search("ICN", "NRT", dep, None, 1, "ECONOMY", max_results=20, progress_callback=None)

    with FlightSearcher._cache_lock:
        for key, (saved_at, payload) in list(FlightSearcher._search_cache.items()):
            FlightSearcher._search_cache[key] = (saved_at - 5, payload)

    second = searcher.search("ICN", "NRT", dep, None, 1, "ECONOMY", max_results=20, progress_callback=None)

    assert first and second
    assert fake_scraper.calls == 2
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
            raise ManualModeActivationError("테스트 수동 전환 실패")

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
    assert "수동 모드 전환 실패" in errors[0]
