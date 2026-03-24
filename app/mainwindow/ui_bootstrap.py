"""UiBootstrapMixin methods extracted from MainWindow."""

from typing import TYPE_CHECKING, Any

from app.mainwindow.shared import *
from app.mainwindow.ui_bootstrap_sections import (
    add_filter_progress_section,
    add_header_section,
    add_manual_mode_section,
    add_results_section,
    add_search_panel_section,
    create_scroll_container,
    finalize_window_layout,
)

if TYPE_CHECKING:
    from app.main_window import MainWindow


class UiBootstrapMixin:
    def _init_ui(self: Any):
        scroll, container, main_layout = create_scroll_container()
        add_header_section(self, main_layout)
        add_search_panel_section(self, main_layout)
        add_filter_progress_section(self, main_layout)
        add_results_section(self, main_layout)
        add_manual_mode_section(self, main_layout)
        finalize_window_layout(self, scroll, container)

    def _toggle_search_panel(self: Any):
        """검색 패널 접기/펼치기 토글"""
        is_visible = self.search_panel.isVisible()
        self.search_panel.setVisible(not is_visible)
        self.btn_toggle_search.setText("▶ 검색 설정" if is_visible else "▼ 검색 설정")

    def _setup_shortcuts(self: Any):
        """키보드 단축키 설정"""
        shortcut_search = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut_search.activated.connect(self.search_panel._on_search)

        shortcut_refresh = QShortcut(QKeySequence("F5"), self)
        shortcut_refresh.activated.connect(self._apply_filter)

        shortcut_esc = QShortcut(QKeySequence("Escape"), self)
        shortcut_esc.activated.connect(self._on_escape)

        shortcut_filter = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut_filter.activated.connect(
            lambda: self.filter_panel.cb_airline_category.setFocus()
        )

    def _on_table_double_click(self: Any, row, col):
        """테이블 더블클릭 - 현재 조건 검색 페이지 다시 열기."""
        flight = self.table.get_flight_at_row(row)
        if not flight:
            return

        origin = self.current_search_params.get("origin", "ICN")
        dest = self.current_search_params.get("dest", "NRT")
        dep = self.current_search_params.get("dep", "")
        ret = self.current_search_params.get("ret", "")
        cabin = (self.current_search_params.get("cabin_class") or "ECONOMY").upper()
        if cabin not in {"ECONOMY", "BUSINESS", "FIRST"}:
            cabin = "ECONOMY"

        try:
            adults = int(self.current_search_params.get("adults", 1))
        except Exception:
            adults = 1
        adults = max(1, adults)

        url = scraper_config.build_interpark_search_url(
            origin,
            dest,
            dep,
            ret or None,
            cabin=cabin,
            adults=adults,
            infant=0,
            child=0,
        )

        webbrowser.open(url)
        self.log_viewer.append_log(f"브라우저에서 현재 조건 검색 열기: {flight.airline}")

    # --- Favorites Tab ---
