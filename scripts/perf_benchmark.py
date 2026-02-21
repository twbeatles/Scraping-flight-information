"""
Lightweight performance smoke benchmark for Flight Bot.

Usage:
    python scripts/perf_benchmark.py
"""

from __future__ import annotations

import statistics
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PyQt6.QtWidgets import QApplication

from database import FlightDatabase
from gui_v2 import MAX_PRICE_FILTER, MainWindow
from scraper_v2 import FlightResult, FlightSearcher
from ui.components import ResultTable
from ui.workers import MultiSearchWorker
import ui.workers as workers_module
import scraper_config


def make_results(count: int) -> list[FlightResult]:
    return [
        FlightResult(
            airline=f"Air{i % 25}",
            price=100_000 + (i * 31) % 900_000,
            departure_time=f"{(i % 24):02d}:{(i * 7) % 60:02d}",
            arrival_time=f"{((i + 2) % 24):02d}:{(i * 11) % 60:02d}",
            stops=i % 3,
            is_round_trip=bool(i % 2),
            return_departure_time=f"{((i + 5) % 24):02d}:{(i * 13) % 60:02d}",
            return_arrival_time=f"{((i + 7) % 24):02d}:{(i * 17) % 60:02d}",
            return_stops=(i + 1) % 3,
            outbound_price=50_000 + i,
            return_price=60_000 + i,
            return_airline=f"Ret{i % 10}",
            source="bench",
        )
        for i in range(count)
    ]


def benchmark_result_table(app: QApplication, rows: int = 1000, runs: int = 7) -> dict:
    table = ResultTable()
    data = make_results(rows)
    samples = []
    for _ in range(runs):
        t0 = time.perf_counter()
        table.update_data(data)
        app.processEvents()
        samples.append(time.perf_counter() - t0)
    return {
        "rows": rows,
        "median": statistics.median(samples),
        "min": min(samples),
        "max": max(samples),
    }


def benchmark_apply_filter(rows: int = 1000, runs: int = 10) -> dict:
    class _DummyTable:
        def __init__(self):
            self.last_count = 0

        def update_data(self, data):
            self.last_count = len(data)

    class _DummyPrefs:
        @staticmethod
        def get_preferred_time():
            return {"departure_start": 0, "departure_end": 24}

    class _DummyStatusBar:
        @staticmethod
        def showMessage(_):
            return None

    class _DummyLog:
        @staticmethod
        def append_log(_):
            return None

    class _DummyContext:
        def __init__(self):
            self.all_results = make_results(rows)
            self.table = _DummyTable()
            self.prefs = _DummyPrefs()
            self.log_viewer = _DummyLog()
            self._last_filter_log_msg = ""
            self._last_filter_log_ts = 0.0

        def statusBar(self):
            return _DummyStatusBar()

        def _append_filter_log(self, _):
            return None

    ctx = _DummyContext()
    base_filter = {
        "direct_only": False,
        "include_layover": True,
        "airline_category": "ALL",
        "max_stops": 3,
        "ret_start_time": 0,
        "ret_end_time": 24,
        "min_price": 0,
        "max_price": MAX_PRICE_FILTER,
    }
    samples = []
    for i in range(runs):
        f = {**base_filter, "start_time": i % 10, "end_time": 24}
        t0 = time.perf_counter()
        MainWindow._apply_filter(ctx, f)
        samples.append(time.perf_counter() - t0)
    return {
        "rows": rows,
        "median": statistics.median(samples),
        "min": min(samples),
        "max": max(samples),
        "filtered_rows": ctx.table.last_count,
    }


def benchmark_db_cache(rows: int = 1000, runs: int = 5) -> dict:
    data = make_results(rows)
    save_samples = []
    load_samples = []
    db_path = Path(tempfile.gettempdir()) / f"flight_bench_{int(time.time() * 1000)}.db"
    db = FlightDatabase(db_path=str(db_path))

    search_params = {
        "origin": "ICN",
        "dest": "NRT",
        "dep": "20260301",
        "ret": "20260305",
        "adults": 1,
        "cabin_class": "ECONOMY",
    }

    for _ in range(runs):
        t0 = time.perf_counter()
        db.save_last_search_results(search_params, data)
        save_samples.append(time.perf_counter() - t0)

        t1 = time.perf_counter()
        _, restored, _, _ = db.get_last_search_results()
        load_samples.append(time.perf_counter() - t1)
        assert len(restored) == rows

    return {
        "rows": rows,
        "save_median": statistics.median(save_samples),
        "load_median": statistics.median(load_samples),
    }


def benchmark_worker_parallelism() -> dict:
    original_searcher = workers_module.FlightSearcher

    class _FakeSearcher:
        def search(self, *args, **kwargs):
            time.sleep(0.08)
            return [FlightResult(airline="Mock", price=123_000, departure_time="10:00", arrival_time="12:00")]

        def close(self):
            return None

        def is_manual_mode(self):
            return False

    workers_module.FlightSearcher = _FakeSearcher
    try:
        destinations = ["NRT", "HND", "KIX", "FUK", "TPE", "BKK"]
        dep = (datetime.now() + timedelta(days=10)).strftime("%Y%m%d")

        # Sequential baseline
        t0 = time.perf_counter()
        for dest in destinations:
            s = _FakeSearcher()
            s.search("ICN", dest, dep, None, 1, max_results=20)
            s.close()
        sequential = time.perf_counter() - t0

        # Worker (parallel=2)
        worker = MultiSearchWorker("ICN", destinations, dep, None, 1, max_results=20)
        captured = {}
        worker.all_finished.connect(lambda data: captured.update(data))
        t1 = time.perf_counter()
        worker.run()
        parallel = time.perf_counter() - t1

        return {
            "destinations": len(destinations),
            "sequential": sequential,
            "parallel": parallel,
            "speedup": (sequential / parallel) if parallel > 0 else 0.0,
            "result_keys": len(captured),
        }
    finally:
        workers_module.FlightSearcher = original_searcher


def benchmark_search_cache_hit(runs: int = 20) -> dict:
    original_cache_enabled = scraper_config.ENABLE_SEARCH_CACHE

    class _FakeScraper:
        def __init__(self):
            self.calls = 0

        def search(self, *args, **kwargs):
            self.calls += 1
            return [FlightResult(airline="CacheAir", price=111_000, departure_time="09:00", arrival_time="11:00")]

        def close(self):
            return None

        def is_manual_mode(self):
            return False

    try:
        scraper_config.ENABLE_SEARCH_CACHE = True
        FlightSearcher.clear_cache()
        searcher = FlightSearcher()
        fake_scraper = _FakeScraper()
        searcher.scraper = fake_scraper

        dep = (datetime.now() + timedelta(days=10)).strftime("%Y%m%d")
        searcher.search("ICN", "NRT", dep, None, 1, "ECONOMY", max_results=20, progress_callback=None)

        samples = []
        for _ in range(runs):
            t0 = time.perf_counter()
            results = searcher.search("ICN", "NRT", dep, None, 1, "ECONOMY", max_results=20, progress_callback=None)
            samples.append(time.perf_counter() - t0)
            assert results

        return {
            "runs": runs,
            "median": statistics.median(samples),
            "min": min(samples),
            "max": max(samples),
            "scraper_calls": fake_scraper.calls,
        }
    finally:
        FlightSearcher.clear_cache()
        scraper_config.ENABLE_SEARCH_CACHE = original_cache_enabled


def main():
    app = QApplication.instance() or QApplication([])
    print("=== Flight Bot Performance Smoke Benchmark ===")

    table_stats = benchmark_result_table(app)
    print(
        f"[UI] ResultTable.update_data({table_stats['rows']}) "
        f"median={table_stats['median']:.4f}s "
        f"(min={table_stats['min']:.4f}s max={table_stats['max']:.4f}s)"
    )

    filter_stats = benchmark_apply_filter()
    print(
        f"[UI] MainWindow._apply_filter({filter_stats['rows']}) "
        f"median={filter_stats['median']:.4f}s "
        f"(min={filter_stats['min']:.4f}s max={filter_stats['max']:.4f}s)"
    )

    db_stats = benchmark_db_cache()
    print(
        f"[DB] last_search {db_stats['rows']} rows "
        f"save_median={db_stats['save_median']:.4f}s "
        f"load_median={db_stats['load_median']:.4f}s"
    )

    worker_stats = benchmark_worker_parallelism()
    print(
        f"[Workers] destinations={worker_stats['destinations']} "
        f"sequential={worker_stats['sequential']:.4f}s "
        f"parallel={worker_stats['parallel']:.4f}s "
        f"speedup={worker_stats['speedup']:.2f}x "
        f"results={worker_stats['result_keys']}"
    )

    cache_stats = benchmark_search_cache_hit()
    print(
        f"[Cache] runs={cache_stats['runs']} "
        f"median={cache_stats['median']:.6f}s "
        f"(min={cache_stats['min']:.6f}s max={cache_stats['max']:.6f}s) "
        f"scraper_calls={cache_stats['scraper_calls']}"
    )


if __name__ == "__main__":
    main()
