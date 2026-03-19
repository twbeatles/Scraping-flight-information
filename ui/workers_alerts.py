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

class AlertAutoCheckWorker(QThread):
    """가격 알림 자동 점검 워커"""
    progress = pyqtSignal(str)
    alert_checked = pyqtSignal(int, int)  # alert_id, current_price
    alert_check_failed = pyqtSignal(int, str, str, str)  # alert_id, origin, dest, error
    alert_hit = pyqtSignal(int, int, int, str, str, str)  # alert_id, price, target, origin, dest, cabin
    done = pyqtSignal(int, int)  # checked_count, hit_count

    def __init__(self, alerts, max_results=50, telemetry_callback=None):
        super().__init__()
        self.alerts = alerts
        self.max_results = max_results
        self.telemetry_callback = telemetry_callback
        self._cancelled = False
        self._cancel_lock = threading.Lock()
        self._active_searcher = None

    def _set_active_searcher(self, searcher):
        with self._cancel_lock:
            self._active_searcher = searcher

    def _clear_active_searcher(self, searcher):
        with self._cancel_lock:
            if self._active_searcher is searcher:
                self._active_searcher = None

    def cancel(self):
        with self._cancel_lock:
            self._cancelled = True
            active = self._active_searcher
        self.requestInterruption()
        if active:
            try:
                active.close()
            except Exception as e:
                logger.debug(f"자동 알림 취소 중 브라우저 정리 오류 (무시됨): {e}")

    def is_cancelled(self):
        with self._cancel_lock:
            return self._cancelled or self.isInterruptionRequested()

    def run(self):
        checked = 0
        hits = 0

        for alert in self.alerts:
            if self.is_cancelled():
                break

            origin = (getattr(alert, "origin", "") or "").upper()
            dest = (getattr(alert, "destination", "") or "").upper()
            dep_date = getattr(alert, "departure_date", "")
            ret_date = getattr(alert, "return_date", None)
            target_price = int(getattr(alert, "target_price", 0) or 0)
            adults = int(getattr(alert, "adults", 1) or 1)
            cabin_class = (getattr(alert, "cabin_class", "ECONOMY") or "ECONOMY").upper()
            alert_id = int(getattr(alert, "id", 0) or 0)

            self.progress.emit(f"🔔 자동점검: {origin}->{dest} {dep_date} ({cabin_class}, 성인 {adults}명)")
            searcher_cls = _searcher_cls()
            try:
                searcher = searcher_cls(telemetry_callback=self.telemetry_callback)
            except TypeError:
                searcher = searcher_cls()
            self._set_active_searcher(searcher)
            current_price = 0
            failure_message = ""
            try:
                results = searcher.search(
                    origin,
                    dest,
                    dep_date,
                    ret_date,
                    adults=adults,
                    cabin_class=cabin_class,
                    max_results=self.max_results,
                    progress_callback=lambda _msg: None,
                    background_mode=True,
                )
                if results:
                    current_price = min(r.price for r in results)
            except Exception as e:
                failure_message = str(e)
                logger.debug(f"Alert auto-check error for {origin}->{dest}: {e}")
            finally:
                checked += 1
                if failure_message:
                    self.alert_check_failed.emit(alert_id, origin, dest, failure_message)
                else:
                    self.alert_checked.emit(alert_id, current_price)
                self._clear_active_searcher(searcher)
                try:
                    searcher.close()
                except Exception:
                    pass

            if self.is_cancelled():
                break
            if current_price > 0 and target_price > 0 and current_price <= target_price:
                hits += 1
                self.alert_hit.emit(alert_id, current_price, target_price, origin, dest, cabin_class)

        self.done.emit(checked, hits)
