"""HistoryMixin methods extracted from MainWindow."""

from app.mainwindow.shared import *
from typing import TYPE_CHECKING, Any
from ui.search_panel_params import apply_search_params_to_panel

if TYPE_CHECKING:
    from app.main_window import MainWindow


class HistoryMixin:
    def create_history_tab(self: Any):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.list_history = QListWidget()
        self.list_history.itemDoubleClicked.connect(self.restore_search_from_history)
        layout.addWidget(self.list_history)
        
        btn_refresh = QPushButton("기록 새로고침")
        btn_refresh.clicked.connect(self._refresh_history_tab)
        layout.addWidget(btn_refresh)
        
        self._refresh_history_tab()
        return widget
    def _refresh_history_tab(self: Any):
        if not hasattr(self, 'list_history'):
            return
        self.list_history.clear()
        history = self.prefs.get_history()
        for item in history:
            display = f"[{item.get('timestamp')}] {item.get('origin')} ➝ {item.get('dest')} ({item.get('dep')})"
            list_item = QListWidgetItem(display)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.list_history.addItem(list_item)
    def _restore_search_panel_from_params(self: Any, params: dict):
        """검색 파라미터를 검색 패널 UI에 복원"""
        if not params:
            return {}
        return apply_search_params_to_panel(self.search_panel, params)
    def restore_search_from_history(self: Any, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        try:
            self._restore_search_panel_from_params(data)
            QMessageBox.information(self, "복원 완료", "검색 조건이 복원되었습니다.")
            
        except Exception as e:
            QMessageBox.warning(self, "오류", f"복원 중 오류: {e}")
    
    # --- Session Management Methods ---



