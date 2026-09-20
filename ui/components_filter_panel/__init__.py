"""Flight filter panel (package facade).

Split (SOLID/SRP) without breaking the public contract: `FilterPanel`
is still importable from `ui.components_filter_panel`, with state and
validation logic in `state.py`.
"""

from ui.components_filter_panel.panel import FilterPanel
from ui.components_filter_panel.state import DEFAULT_FILTERS, adjust_time_range, build_filter_dict

__all__ = [
    "FilterPanel",
    "DEFAULT_FILTERS",
    "adjust_time_range",
    "build_filter_dict",
]
