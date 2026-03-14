"""Compatibility exports for search dialogs."""

from ui.dialogs_search_date_range import DateRangeDialog
from ui.dialogs_search_multi import MultiDestDialog
from ui.dialogs_search_results import DateRangeResultDialog, MultiDestResultDialog

__all__ = [
    "MultiDestDialog",
    "DateRangeDialog",
    "MultiDestResultDialog",
    "DateRangeResultDialog",
]
