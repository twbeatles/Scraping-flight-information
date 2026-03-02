"""Facade exports for background workers."""

import logging
import threading
import traceback
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timedelta

from PyQt6.QtCore import QThread, pyqtSignal

from scraper_v2 import BrowserInitError, FlightSearcher, NetworkError
from ui.workers_search import SearchWorker
from ui.workers_parallel import (
    MAX_DATE_RANGE_SEARCHES,
    MAX_PARALLEL_WORKERS,
    DateRangeWorker,
    MultiSearchWorker,
)
from ui.workers_alerts import AlertAutoCheckWorker

logger = logging.getLogger(__name__)

__all__ = [
    "logging",
    "threading",
    "traceback",
    "FIRST_COMPLETED",
    "ThreadPoolExecutor",
    "wait",
    "datetime",
    "timedelta",
    "QThread",
    "pyqtSignal",
    "FlightSearcher",
    "BrowserInitError",
    "NetworkError",
    "logger",
    "MAX_DATE_RANGE_SEARCHES",
    "MAX_PARALLEL_WORKERS",
    "SearchWorker",
    "MultiSearchWorker",
    "DateRangeWorker",
    "AlertAutoCheckWorker",
]
