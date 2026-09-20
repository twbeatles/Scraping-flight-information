"""Shared cancellable worker machinery (SRP: cancel lifecycle only)."""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from PyQt6.QtCore import QThread

from scraper_v2 import FlightSearcher


logger = logging.getLogger(__name__)

MAX_PARALLEL_WORKERS = 2
EXECUTOR_CANCEL_DRAIN_SECONDS = 0.5


def _searcher_cls():
    """Resolve searcher class via facade for monkeypatch compatibility."""
    try:
        import ui.workers as workers_module

        return getattr(workers_module, "FlightSearcher", FlightSearcher)
    except Exception:
        return FlightSearcher


def _cancel_and_shutdown_executor(executor: ThreadPoolExecutor, futures) -> None:
    """Cancel queued futures and give running searches a short cleanup window."""
    future_list = list(futures.keys())
    for future in future_list:
        future.cancel()
    if future_list:
        wait(future_list, timeout=EXECUTOR_CANCEL_DRAIN_SECONDS)
    executor.shutdown(wait=False, cancel_futures=True)


class CancellableWorker(QThread):
    """QThread with cooperative cancel and active-searcher tracking."""

    _cancel_log_prefix = "병렬 검색"

    def __init__(self):
        super().__init__()
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
                logger.debug(f"{self._cancel_log_prefix} 취소 중 브라우저 정리 오류 (무시됨): {e}")

    def is_cancelled(self):
        with self._cancel_lock:
            return self._cancelled or self.isInterruptionRequested()
