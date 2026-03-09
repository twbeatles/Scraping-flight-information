"""CalendarMixin methods extracted from MainWindow."""

from app.mainwindow.shared import *
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.main_window import MainWindow


class CalendarMixin:
    def _show_calendar_view(self: Any):
        """날짜별 가격 캘린더 뷰 표시"""
        # 저장된 날짜별 가격 데이터가 있는지 확인
        if not hasattr(self, 'date_range_results') or not self.date_range_results:
            QMessageBox.information(
                self, "캘린더 뷰", 
                "날짜별 가격 데이터가 없습니다.\n\n'📅 날짜 범위' 버튼을 눌러 먼저 날짜별 최저가를 검색해주세요."
            )
            return
        
        # 캘린더 다이얼로그 표시
        dlg = CalendarViewDialog(self.date_range_results, self)
        dlg.date_selected.connect(self._on_calendar_date_selected)
        dlg.exec()
    def _on_calendar_date_selected(self: Any, date_str):
        """캘린더에서 날짜 선택 시 해당 날짜로 검색 조건 설정"""
        try:
            qdate = QDate.fromString(date_str, "yyyyMMdd")
            if qdate.isValid():
                self.search_panel.date_dep.setDate(qdate)
                self.log_viewer.append_log(f"📅 출발일 변경: {qdate.toString('yyyy-MM-dd')}")
        except Exception as e:
            logger.debug(f"Calendar date selection error: {e}")



