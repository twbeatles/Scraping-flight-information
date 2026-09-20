""""Light theme QSS" (package facade).

Split (SOLID/SRP): one QSS section per module; `LIGHT_THEME` is composed
in the original order so the value stays byte-identical.
"""

from ui.styles_light.base import BASE
from ui.styles_light.typography import TYPOGRAPHY
from ui.styles_light.cards import CARDS
from ui.styles_light.input import INPUT
from ui.styles_light.checkboxes import CHECKBOXES
from ui.styles_light.radio import RADIO
from ui.styles_light.buttons import BUTTONS
from ui.styles_light.table import TABLE
from ui.styles_light.scrollbars import SCROLLBARS
from ui.styles_light.tab import TAB
from ui.styles_light.log import LOG
from ui.styles_light.progress import PROGRESS
from ui.styles_light.tooltips import TOOLTIPS
from ui.styles_light.list import LIST
from ui.styles_light.message import MESSAGE
from ui.styles_light.status import STATUS
from ui.styles_light.groupbox import GROUPBOX

LIGHT_THEME = "".join(
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
    ]
)

__all__ = [
    "LIGHT_THEME",
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
]
