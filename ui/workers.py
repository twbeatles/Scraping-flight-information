
"""
Background Workers for Flight Bot
"""
import logging
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from PyQt6.QtCore import QThread, pyqtSignal

from scraper_v2 import FlightSearcher, BrowserInitError, NetworkError, ManualModeActivationError

# 로거 설정
logger = logging.getLogger(__name__)

# 상수 설정
MAX_DATE_RANGE_SEARCHES = 30
MAX_PARALLEL_WORKERS = 2

class SearchWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    manual_mode_signal = pyqtSignal(object)  # active_searcher

    def __init__(
        self,
        origin,
        destination,
        date,
        return_date,
        adults,
        cabin_class="ECONOMY",
        max_results=1000,
        force_refresh=False,
    ):
        super().__init__()
        self.origin = origin
        self.destination = destination
        self.date = date
        self.return_date = return_date
        self.adults = adults
        self.cabin_class = cabin_class
        self.max_results = max_results
        self.force_refresh = force_refresh
        self.searcher = FlightSearcher()
        self._cancelled = False
        self._cancel_lock = threading.Lock()  # 취소 플래그 스레드 안전성

    def cancel(self):
        """스레드 안전한 검색 취소 요청 및 브라우저 정리"""
        with self._cancel_lock:
            if self._cancelled:  # 중복 취소 방지
                return
            self._cancelled = True
        
        try:
            if self.searcher:
                self.searcher.close()
        except Exception as e:
            logging.debug(f"검색 취소 중 오류 (무시됨): {e}")
    
    def is_cancelled(self) -> bool:
        """스레드 안전하게 취소 상태 확인"""
        with self._cancel_lock:
            return self._cancelled or self.isInterruptionRequested()

    def run(self):
        try:
            results = self.searcher.search(
                self.origin, self.destination, self.date, 
                self.return_date, self.adults, self.cabin_class,
                max_results=self.max_results,
                progress_callback=lambda msg: self.progress.emit(msg),
                force_refresh=self.force_refresh,
            )
            
            if self.is_cancelled():
                self.progress.emit("검색이 취소되었습니다.")
                return
            
            if not results and self.searcher.is_manual_mode():
                self.manual_mode_signal.emit(self.searcher)
            else:
                self.finished.emit(results)
        except BrowserInitError as e:
            if not self.is_cancelled():
                self.error.emit(f"브라우저 오류:\n{e.message}")
        except NetworkError as e:
            if not self.is_cancelled():
                self.error.emit(f"네트워크 오류:\n{e.message}")
        except ManualModeActivationError as e:
            if not self.is_cancelled():
                self.error.emit(f"수동 모드 전환 실패:\n{e.message}")
        except Exception as e:
            if not self.is_cancelled():
                traceback.print_exc()
                self.error.emit(str(e))
        finally:
            # 항상 브라우저 정리 보장
            if self.is_cancelled() or not self.searcher.is_manual_mode():
                try:
                    self.searcher.close()
                except Exception:
                    pass


class MultiSearchWorker(QThread):
    """다중 목적지 병렬 검색 Worker (동시 2개)"""
    progress = pyqtSignal(str)
    single_finished = pyqtSignal(str, list)  # dest, results
    all_finished = pyqtSignal(dict)  # {dest: [results]}
    error = pyqtSignal(str)
    
    def __init__(self, origin, destinations, date, return_date, adults, max_results=1000):
        super().__init__()
        self.origin = origin
        self.destinations = destinations  # list of destination codes
        self.date = date
        self.return_date = return_date
        self.adults = adults
        self.max_results = max_results
        self._cancelled = False
        self._cancel_lock = threading.Lock()
        self._active_searchers = set()

    def cancel(self):
        with self._cancel_lock:
            if self._cancelled:
                return
            self._cancelled = True

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

            searcher = FlightSearcher()
            self._register_active_searcher(searcher)
            try:
                if self.is_cancelled():
                    return index, dest, [], "cancelled"
                results = searcher.search(
                    self.origin, dest, self.date, self.return_date, self.adults,
                    max_results=self.max_results,
                    progress_callback=lambda msg: self.progress.emit(f"[{dest}] {msg}")
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

        futures = {}
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
            for index, dest in enumerate(self.destinations, 1):
                self.progress.emit(f"🔍 [{index}/{total}] {dest} 검색 대기...")
                futures[executor.submit(search_single, index, dest)] = dest

            for future in as_completed(futures):
                dest = futures[future]
                if self.is_cancelled():
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

        if self.is_cancelled():
            self._close_all_active_searchers()
            self.progress.emit(f"⚠️ 다중 검색이 취소되었습니다. ({len(all_results)}/{total} 완료)")
            return

        ordered_results = {dest: all_results.get(dest, []) for dest in self.destinations}
        self.all_finished.emit(ordered_results)


class DateRangeWorker(QThread):
    """날짜 범위 검색 Worker"""
    progress = pyqtSignal(str)
    date_result = pyqtSignal(str, int, str)  # date, min_price, airline
    all_finished = pyqtSignal(dict)  # {date: (price, airline)}
    
    def __init__(self, origin, dest, dates, return_offset, adults, max_results=1000):
        super().__init__()
        self.origin = origin
        self.dest = dest
        self.dates = dates  # list of date strings
        self.return_offset = return_offset  # days after departure for return
        self.adults = adults
        self.max_results = max_results
        self._cancelled = False
        self._cancel_lock = threading.Lock()
        self._active_searchers = set()

    def cancel(self):
        with self._cancel_lock:
            if self._cancelled:
                return
            self._cancelled = True

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
        
        # 최대 검색 횟수 제한 (무한 루프 방지)
        if total > MAX_DATE_RANGE_SEARCHES:
            self.progress.emit(f"⚠️ 최대 {MAX_DATE_RANGE_SEARCHES}개 날짜만 검색합니다.")
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

            searcher = FlightSearcher()
            self._register_active_searcher(searcher)
            try:
                if self.is_cancelled():
                    return date, (0, "취소됨"), "cancelled"
                results = searcher.search(
                    self.origin, self.dest, date, ret_date, self.adults,
                    max_results=self.max_results,
                    progress_callback=lambda msg: self.progress.emit(msg)
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

        futures = {}
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
            for i, date in enumerate(self.dates, 1):
                self.progress.emit(f"📅 [{i}/{total}] {date} 검색 대기...")
                futures[executor.submit(search_single, date)] = date

            completed = 0
            for future in as_completed(futures):
                date = futures[future]
                if self.is_cancelled():
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
                    self.progress.emit(f"⏭️ {dep_date} - 수동 모드 전환됨, 건너뜁니다 [{completed}/{total}]")
                    continue
                if status == "ok":
                    self.date_result.emit(dep_date, price, airline)
                    self.progress.emit(f"✅ {dep_date}: {price:,}원 ({airline}) [{completed}/{total}]")
                    continue
                if status == "empty":
                    self.progress.emit(f"⚠️ {dep_date}: 결과 없음 [{completed}/{total}]")
                    continue

                self.progress.emit(f"⚠️ {dep_date} 검색 실패: {status} [{completed}/{total}]")
        
        if self.is_cancelled():
            self._close_all_active_searchers()
            self.progress.emit(f"⚠️ 날짜 범위 검색이 취소되었습니다. ({len(all_results)}개 날짜 분석됨)")
            return

        self.progress.emit(f"🏁 검색 완료! 총 {len(all_results)}개 날짜 분석됨")
        ordered_results = {date: all_results.get(date, (0, "N/A")) for date in self.dates}
        self.all_finished.emit(ordered_results)
