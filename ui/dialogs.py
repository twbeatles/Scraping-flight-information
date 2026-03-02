"""Facade exports for UI dialogs."""

from ui.dialogs_base import (
    MAX_MULTI_DESTINATIONS,
    MAX_DATE_RANGE_DAYS,
    _validate_route_and_dates,
)
from ui.dialogs_calendar import CalendarViewDialog
from ui.dialogs_combination import CombinationSelectorDialog
from ui.dialogs_search import (
    MultiDestDialog,
    DateRangeDialog,
    MultiDestResultDialog,
    DateRangeResultDialog,
)
from ui.dialogs_tools import (
    ShortcutsDialog,
    PriceAlertDialog,
    SettingsDialog,
)

__all__ = [
    "MAX_MULTI_DESTINATIONS",
    "MAX_DATE_RANGE_DAYS",
    "_validate_route_and_dates",
    "CalendarViewDialog",
    "CombinationSelectorDialog",
    "MultiDestDialog",
    "DateRangeDialog",
    "MultiDestResultDialog",
    "DateRangeResultDialog",
    "ShortcutsDialog",
    "PriceAlertDialog",
    "SettingsDialog",
]
