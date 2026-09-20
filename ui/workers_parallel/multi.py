"""Multi-destination parallel search worker (SRP: multi-dest fan-out only)."""

import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from PyQt6.QtCore import pyqtSignal

import scraper_config
from ui.workers_parallel.base import (
    MAX_PARALLEL_WORKERS,
    CancellableWorker,
    _cancel_and_shutdown_executor,
    _searcher_cls,
)


class MultiSearchWorker(CancellableWorker):
    """다중 목적지 병렬 검색 Worker (동시 2개)"""

    _cancel_log_prefix = "다중 검색"

    progress = pyqtSignal(str)
    single_finished = pyqtSignal(str, list)  # dest, results
    all_finished = pyqtSignal(dict)  # {dest: [results]}
    error = pyqtSignal(str)

    def __init__(
        self,
        origin,
        destinations,
        date,
        return_date,
        adults,
        cabin_class="ECONOMY",
        max_results=1000,
        telemetry_callback=None,
        child=0,
        infant=0,
    ):
        super().__init__()
        self.origin = origin
        self.destinations = destinations  # list of destination codes
        self.date = date
        self.return_date = return_date
        self.adults = adults
        self.cabin_class = cabin_class
        self.max_results = max_results
        self.telemetry_callback = telemetry_callback
        self.child = max(0, int(child or 0))
        self.infant = max(0, int(infant or 0))

    def run(self):
        all_results = {}
        total = len(self.destinations)

        if total == 0:
            self.all_finished.emit({})
            return

        def search_single(index, dest):
            if self.is_cancelled():
                return index, dest, [], "cancelled"

            searcher_cls = _searcher_cls()
            try:
                searcher = searcher_cls(telemetry_callback=self.telemetry_callback)
            except TypeError:
                searcher = searcher_cls()
            self._register_active_searcher(searcher)
            try:
                if self.is_cancelled():
                    return index, dest, [], "cancelled"
                results = searcher.search(
                    self.origin, dest, self.date, self.return_date, self.adults, self.cabin_class,
                    max_results=self.max_results,
                    progress_callback=lambda msg: self.progress.emit(f"[{dest}] {msg}"),
                    background_mode=True,
                    cancel_check=self.is_cancelled,
                    child=self.child,
                    infant=self.infant,
                )
                return index, dest, results, None
            except Exception as e:
                return index, dest, [], str(e)
            finally:
                self._unregister_active_searcher(searcher)
                try:
                    searcher.close()
                except Exception:
                    pass

        launch_delay = max(
            float(getattr(scraper_config, "PARALLEL_SEARCH_LAUNCH_DELAY_SECONDS", 0.75)),
            0.0,
        )
        executor = ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS)
        pending = list(enumerate(self.destinations, 1))
        futures = {}
        try:
            while pending or futures:
                if self.is_cancelled():
                    self._close_all_active_searchers()
                    _cancel_and_shutdown_executor(executor, futures)
                    self.progress.emit(f"⚠️ 다중 검색이 취소되었습니다. ({len(all_results)}/{total} 완료)")
                    return

                while pending and len(futures) < MAX_PARALLEL_WORKERS and not self.is_cancelled():
                    index, dest = pending.pop(0)
                    self.progress.emit(f"🔍 [{index}/{total}] {dest} 검색 대기...")
                    futures[executor.submit(search_single, index, dest)] = dest

                if not futures:
                    continue

                done, _ = wait(list(futures.keys()), timeout=0.1, return_when=FIRST_COMPLETED)
                if not done:
                    continue

                for future in done:
                    dest = futures.pop(future, None)
                    if not dest:
                        continue

                    try:
                        _, done_dest, results, error_msg = future.result()
                    except Exception as e:
                        done_dest, results, error_msg = dest, [], str(e)

                    if error_msg == "cancelled":
                        all_results[done_dest] = []
                        continue

                    if error_msg:
                        self.progress.emit(f"⚠️ {done_dest} 검색 실패: {error_msg}")
                        all_results[done_dest] = []
                        continue

                    all_results[done_dest] = results
                    self.single_finished.emit(done_dest, results)

                if launch_delay > 0 and pending and futures:
                    time.sleep(launch_delay)
        finally:
            if futures:
                _cancel_and_shutdown_executor(executor, futures)
            else:
                executor.shutdown(wait=False, cancel_futures=True)

        ordered_results = {dest: all_results.get(dest, []) for dest in self.destinations}
        self.all_finished.emit(ordered_results)
