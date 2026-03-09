"""SearchDateRangeMixin methods extracted from MainWindow."""

from app.mainwindow.shared import *
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.main_window import MainWindow


class SearchDateRangeMixin:
    def _open_date_range_search(self: Any):
        dialog = DateRangeDialog(self, self.prefs)
        dialog.search_requested.connect(self._start_date_search)
        dialog.exec()
    def _start_date_search(self: Any, origin, dest, dates, duration, adults, cabin_class):
        self._stop_alert_worker_if_running()
        if not self._ensure_no_running_search():
            return

        if not self._guard_manual_browser_for_new_search("날짜 범위 검색"):
            return

        self.log_viewer.clear()
        self.log_viewer.append_log(f"📅 날짜 범위 검색 시작: {dates[0]} ~ {dates[-1]} [{cabin_class}]")
        
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat("날짜별 검색 중...")
        self.tabs.setCurrentIndex(2)  # Logs tab
        
        max_results = self.prefs.get_max_results()
        self.date_worker = DateRangeWorker(
            origin,
            dest,
            dates,
            duration,
            adults,
            cabin_class,
            max_results,
            telemetry_callback=self._emit_telemetry_event,
        )
        self.date_worker.progress.connect(self._update_progress)
        self.date_worker.date_result.connect(self._on_date_range_result)
        self.date_worker.all_finished.connect(self._date_search_finished)
        self.date_worker.start()
    def _on_date_range_result(self: Any, date, min_price, airline):
        self.log_viewer.append_log(f"📌 [{date}] 중간 결과: {min_price:,}원 ({airline})")
    def _date_search_finished(self: Any, results):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("날짜 검색 완료")
        
        # 캘린더 뷰용 데이터 저장
        self.date_range_results = results
        
        # Show results dialog
        dialog = DateRangeResultDialog(results, self)
        dialog.exec()
        
        self.log_viewer.append_log(f"✅ 날짜 범위 검색 완료: {len(results)}일 (캘린더뷰 사용 가능)")

    # --- Standard Search ---



