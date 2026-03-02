"""Background Workers for Flight Bot"""
import logging
import threading
import traceback
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timedelta
from PyQt6.QtCore import QThread, pyqtSignal

from scraper_v2 import FlightSearcher, BrowserInitError, NetworkError

logger = logging.getLogger(__name__)
MAX_DATE_RANGE_SEARCHES = 30
MAX_PARALLEL_WORKERS = 2


def _searcher_cls():
    """Resolve searcher class via facade for monkeypatch compatibility."""
    try:
        import ui.workers as workers_module

        return getattr(workers_module, "FlightSearcher", FlightSearcher)
    except Exception:
        return FlightSearcher

class MultiSearchWorker(QThread):
    """다중 목적지 병렬 검색 Worker (동시 2개)"""
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
        self._cancelled = False
        self._cancel_lock = threading.Lock()
        self._active_searchers = set()

    def cancel(self):
        with self._cancel_lock:
            if self._cancelled:
                return
            self._cancelled = True

        self.requestInterruption()
        self._close_all_active_searchers()

    def _register_active_searcher(self, searcher):
        with self._cancel_lock:
            self._active_searchers.add(searcher)

    def _unregister_active_searcher(self, searcher):
        with self._cancel_lock:
            self._active_searchers.discard(searcher)

    def _close_all_active_searchers(self):
        with self._cancel_lock:
            active_searchers = list(self._active_searchers)
            self._active_searchers.clear()
        for active_searcher in active_searchers:
            try:
                active_searcher.close()
            except Exception as e:
                logger.debug(f"다중 검색 취소 중 브라우저 정리 오류 (무시됨): {e}")

    def is_cancelled(self):
        with self._cancel_lock:
            return self._cancelled or self.isInterruptionRequested()
    
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

        executor = ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS)
        pending = list(enumerate(self.destinations, 1))
        futures = {}
        try:
            while pending or futures:
                if self.is_cancelled():
                    self._close_all_active_searchers()
                    for future in list(futures.keys()):
                        future.cancel()
                    executor.shutdown(wait=False, cancel_futures=True)
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
        finally:
            for future in list(futures.keys()):
                future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)

        ordered_results = {dest: all_results.get(dest, []) for dest in self.destinations}
        self.all_finished.emit(ordered_results)

class DateRangeWorker(QThread):
    """날짜 범위 검색 Worker"""
    progress = pyqtSignal(str)
    date_result = pyqtSignal(str, int, str)  # date, min_price, airline
    all_finished = pyqtSignal(dict)  # {date: (price, airline)}
    
    def __init__(
        self,
        origin,
        dest,
        dates,
        return_offset,
        adults,
        cabin_class="ECONOMY",
        max_results=1000,
        telemetry_callback=None,
    ):
        super().__init__()
        self.origin = origin
        self.dest = dest
        self.dates = dates  # list of date strings
        self.return_offset = return_offset  # days after departure for return
        self.adults = adults
        self.cabin_class = cabin_class
        self.max_results = max_results
        self.telemetry_callback = telemetry_callback
        self._cancelled = False
        self._cancel_lock = threading.Lock()
        self._active_searchers = set()

    def cancel(self):
        with self._cancel_lock:
            if self._cancelled:
                return
            self._cancelled = True

        self.requestInterruption()
        self._close_all_active_searchers()

    def _register_active_searcher(self, searcher):
        with self._cancel_lock:
            self._active_searchers.add(searcher)

    def _unregister_active_searcher(self, searcher):
        with self._cancel_lock:
            self._active_searchers.discard(searcher)

    def _close_all_active_searchers(self):
        with self._cancel_lock:
            active_searchers = list(self._active_searchers)
            self._active_searchers.clear()
        for active_searcher in active_searchers:
            try:
                active_searcher.close()
            except Exception as e:
                logger.debug(f"날짜 검색 취소 중 브라우저 정리 오류 (무시됨): {e}")

    def is_cancelled(self):
        with self._cancel_lock:
            return self._cancelled or self.isInterruptionRequested()
    
    def run(self):
        all_results = {}
        total = len(self.dates)

        # 최대 검색 날짜수 제한 (무한 루프 방지)
        if total > MAX_DATE_RANGE_SEARCHES:
            self.progress.emit(f"⚠️ 최대 {MAX_DATE_RANGE_SEARCHES}개 날짜만 검색됩니다.")
            self.dates = self.dates[:MAX_DATE_RANGE_SEARCHES]
            total = MAX_DATE_RANGE_SEARCHES

        if total == 0:
            self.all_finished.emit({})
            return

        def search_single(date):
            if self.is_cancelled():
                return date, (0, "취소됨"), "cancelled"

            ret_date = None
            try:
                dep_dt = datetime.strptime(date, "%Y%m%d")
                ret_date = (dep_dt + timedelta(days=self.return_offset)).strftime("%Y%m%d") if self.return_offset else None
            except Exception:
                pass

            searcher_cls = _searcher_cls()
            try:
                searcher = searcher_cls(telemetry_callback=self.telemetry_callback)
            except TypeError:
                searcher = searcher_cls()
            self._register_active_searcher(searcher)
            try:
                if self.is_cancelled():
                    return date, (0, "취소됨"), "cancelled"
                results = searcher.search(
                    self.origin, self.dest, date, ret_date, self.adults, self.cabin_class,
                    max_results=self.max_results,
                    progress_callback=lambda msg: self.progress.emit(msg),
                    background_mode=True,
                )

                if searcher.is_manual_mode():
                    return date, (0, "수동모드"), "manual"

                if results:
                    min_price = min(r.price for r in results)
                    min_airline = next(r.airline for r in results if r.price == min_price)
                    return date, (min_price, min_airline), "ok"
                return date, (0, "N/A"), "empty"
            except Exception as e:
                return date, (0, "Error"), str(e)
            finally:
                self._unregister_active_searcher(searcher)
                try:
                    searcher.close()
                except Exception as e:
                    logger.debug(f"날짜 검색 브라우저 정리 오류 (무시됨): {e}")

        executor = ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS)
        pending = list(self.dates)
        futures = {}
        completed = 0
        try:
            while pending or futures:
                if self.is_cancelled():
                    self._close_all_active_searchers()
                    for future in list(futures.keys()):
                        future.cancel()
                    executor.shutdown(wait=False, cancel_futures=True)
                    self.progress.emit(f"⚠️ 날짜 범위 검색이 취소되었습니다. ({len(all_results)}개 날짜 분석)")
                    return

                while pending and len(futures) < MAX_PARALLEL_WORKERS and not self.is_cancelled():
                    date = pending.pop(0)
                    self.progress.emit(f"📟 [{completed + len(futures) + 1}/{total}] {date} 검색 대기...")
                    futures[executor.submit(search_single, date)] = date

                if not futures:
                    continue

                done, _ = wait(list(futures.keys()), timeout=0.1, return_when=FIRST_COMPLETED)
                if not done:
                    continue

                for future in done:
                    date = futures.pop(future, None)
                    if not date:
                        continue

                    completed += 1
                    try:
                        dep_date, price_info, status = future.result()
                    except Exception as e:
                        dep_date, price_info, status = date, (0, "Error"), str(e)

                    all_results[dep_date] = price_info
                    price, airline = price_info

                    if status == "cancelled":
                        continue
                    if status == "manual":
                        self.progress.emit(f"⚠️ {dep_date} - 수동 모드 전환됨, 건너뜁니다. [{completed}/{total}]")
                        continue
                    if status == "ok":
                        self.date_result.emit(dep_date, price, airline)
                        self.progress.emit(f"✅ {dep_date}: {price:,}원 ({airline}) [{completed}/{total}]")
                        continue
                    if status == "empty":
                        self.progress.emit(f"⚠️ {dep_date}: 결과 없음 [{completed}/{total}]")
                        continue

                    self.progress.emit(f"⚠️ {dep_date} 검색 실패: {status} [{completed}/{total}]")
        finally:
            for future in list(futures.keys()):
                future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)

        self.progress.emit(f"🎾 검색 완료! 총 {len(all_results)}개 날짜 분석")
        ordered_results = {date: all_results.get(date, (0, "N/A")) for date in self.dates}
        self.all_finished.emit(ordered_results)
