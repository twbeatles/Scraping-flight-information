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
        telemetry_callback=None,
    ):
        super().__init__()
        self.origin = origin
        self.destination = destination
        self.date = date
        self.return_date = return_date
        self.adults = adults
        self.cabin_class = cabin_class
        self.max_results = max_results
        searcher_cls = _searcher_cls()
        try:
            self.searcher = searcher_cls(telemetry_callback=telemetry_callback)
        except TypeError:
            self.searcher = searcher_cls()
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
                background_mode=False,
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
