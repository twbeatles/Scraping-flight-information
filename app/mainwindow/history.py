"""HistoryMixin methods extracted from MainWindow."""

from app.mainwindow.shared import *
from typing import TYPE_CHECKING, Any

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
            return

        sp = self.search_panel

        origin = params.get('origin')
        if origin:
            idx = sp.cb_origin.findData(origin)
            if idx >= 0:
                sp.cb_origin.setCurrentIndex(idx)

        dest = params.get('dest')
        if dest:
            idx = sp.cb_dest.findData(dest)
            if idx >= 0:
                sp.cb_dest.setCurrentIndex(idx)

        dep = params.get('dep')
        if dep:
            dep_date = QDate.fromString(dep, "yyyyMMdd")
            if dep_date.isValid():
                sp.date_dep.setDate(dep_date)

        ret = params.get('ret')
        if ret:
            sp.rb_round.setChecked(True)
            sp._toggle_return_date()
            ret_date = QDate.fromString(ret, "yyyyMMdd")
            if ret_date.isValid():
                sp.date_ret.setDate(ret_date)
        else:
            sp.rb_oneway.setChecked(True)
            sp._toggle_return_date()

        adults = params.get('adults')
        if adults:
            sp.spin_adults.setValue(int(adults))

        cabin = params.get('cabin_class')
        if cabin:
            idx = sp.cb_cabin_class.findData(cabin)
            if idx >= 0:
                sp.cb_cabin_class.setCurrentIndex(idx)
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



