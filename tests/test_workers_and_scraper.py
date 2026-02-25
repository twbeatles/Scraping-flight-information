import threading
import time
from datetime import datetime, timedelta

import scraper_config
from scraper_v2 import FlightResult, PlaywrightScraper
from ui.workers import AlertAutoCheckWorker, DateRangeWorker, MultiSearchWorker


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


def test_multi_search_worker_passes_cabin_class(monkeypatch):
    observed = []

    class _FakeSearcher:
        def search(self, *args, **kwargs):
            observed.append(kwargs.get("cabin_class") or (args[5] if len(args) > 5 else None))
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


def test_date_range_worker_passes_cabin_class(monkeypatch):
    observed = []

    class _FakeSearcher:
        def search(self, *args, **kwargs):
            observed.append(kwargs.get("cabin_class") or (args[5] if len(args) > 5 else None))
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

    observed_cabins = []

    class _FakeSearcher:
        def search(self, *args, **kwargs):
            observed_cabins.append(kwargs.get("cabin_class"))
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
    assert len(hits) == 1


def test_playwright_search_retries_on_network_error(monkeypatch):
    class _FakePage:
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

    def _fake_init_browser(_log=None, _user_data_dir=None):
        scraper.context = _FakeContext(page)

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
