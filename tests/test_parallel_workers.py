import threading
import time
from datetime import datetime, timedelta
from scraper_v2 import (
    FlightResult,
    FlightSearcher,
    ManualModeActivationError,
    PlaywrightScraper,
    ParallelSearcher,
)
from ui.workers import AlertAutoCheckWorker, DateRangeWorker, MultiSearchWorker, SearchWorker

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

