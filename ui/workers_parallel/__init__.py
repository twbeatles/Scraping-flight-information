"""Background parallel workers (package facade).

Split (SOLID/SRP) without breaking the public contract: every name
previously importable from `ui.workers_parallel` is re-exported here.
"""

from ui.workers_parallel.base import (
    EXECUTOR_CANCEL_DRAIN_SECONDS,
    MAX_PARALLEL_WORKERS,
    CancellableWorker,
    _cancel_and_shutdown_executor,
    _searcher_cls,
)
from ui.workers_parallel.dates import MAX_DATE_RANGE_SEARCHES, DateRangeWorker
from ui.workers_parallel.multi import MultiSearchWorker

__all__ = [
    "MAX_DATE_RANGE_SEARCHES",
    "MAX_PARALLEL_WORKERS",
    "EXECUTOR_CANCEL_DRAIN_SECONDS",
    "CancellableWorker",
    "MultiSearchWorker",
    "DateRangeWorker",
    "_searcher_cls",
    "_cancel_and_shutdown_executor",
]
