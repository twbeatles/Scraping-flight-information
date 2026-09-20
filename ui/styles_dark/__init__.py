""""Dark theme QSS" (package facade).

Split (SOLID/SRP): one QSS section per module; `DARK_THEME` is composed
in the original order so the value stays byte-identical.
"""

from ui.styles_dark.base import BASE
from ui.styles_dark.typography import TYPOGRAPHY
from ui.styles_dark.cards import CARDS
from ui.styles_dark.input import INPUT
from ui.styles_dark.checkboxes import CHECKBOXES
from ui.styles_dark.radio import RADIO
from ui.styles_dark.buttons import BUTTONS
from ui.styles_dark.table import TABLE
from ui.styles_dark.scrollbars import SCROLLBARS
from ui.styles_dark.tab import TAB
from ui.styles_dark.log import LOG
from ui.styles_dark.progress import PROGRESS
from ui.styles_dark.tooltips import TOOLTIPS
from ui.styles_dark.list import LIST
from ui.styles_dark.message import MESSAGE
from ui.styles_dark.status import STATUS
from ui.styles_dark.groupbox import GROUPBOX
from ui.styles_dark.secondary import SECONDARY
from ui.styles_dark.icon import ICON
from ui.styles_dark.slider import SLIDER
from ui.styles_dark.separator import SEPARATOR
from ui.styles_dark.success_warning_error import SUCCESS_WARNING_ERROR
from ui.styles_dark.price import PRICE
from ui.styles_dark.badge import BADGE
from ui.styles_dark.enhanced import ENHANCED
from ui.styles_dark.animated import ANIMATED
from ui.styles_dark.stats import STATS

DARK_THEME = "".join(
    [
    BASE,
    TYPOGRAPHY,
    CARDS,
    INPUT,
    CHECKBOXES,
    RADIO,
    BUTTONS,
    TABLE,
    SCROLLBARS,
    TAB,
    LOG,
    PROGRESS,
    TOOLTIPS,
    LIST,
    MESSAGE,
    STATUS,
    GROUPBOX,
    SECONDARY,
    ICON,
    SLIDER,
    SEPARATOR,
    SUCCESS_WARNING_ERROR,
    PRICE,
    BADGE,
    ENHANCED,
    ANIMATED,
    STATS,
    ]
)

__all__ = [
    "DARK_THEME",
    "BASE",
    "TYPOGRAPHY",
    "CARDS",
    "INPUT",
    "CHECKBOXES",
    "RADIO",
    "BUTTONS",
    "TABLE",
    "SCROLLBARS",
    "TAB",
    "LOG",
    "PROGRESS",
    "TOOLTIPS",
    "LIST",
    "MESSAGE",
    "STATUS",
    "GROUPBOX",
    "SECONDARY",
    "ICON",
    "SLIDER",
    "SEPARATOR",
    "SUCCESS_WARNING_ERROR",
    "PRICE",
    "BADGE",
    "ENHANCED",
    "ANIMATED",
    "STATS",
]
