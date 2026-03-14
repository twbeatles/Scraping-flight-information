"""Search panel widget entry point."""

from __future__ import annotations

from ui.search_panel_shared import QFrame, SearchPanelPrefs, pyqtSignal
from ui.search_panel_actions import SearchPanelActionsMixin
from ui.search_panel_build import SearchPanelBuildMixin
from ui.search_panel_state import SearchPanelStateMixin


class SearchPanel(SearchPanelStateMixin, SearchPanelActionsMixin, SearchPanelBuildMixin, QFrame):
    search_requested = pyqtSignal(str, str, str, str, int, str)

    def __init__(self, prefs: SearchPanelPrefs) -> None:
        super().__init__()
        self.prefs = prefs
        self.setObjectName("card")
        self._init_ui()
