"""SearchMultiMixin methods extracted from MainWindow."""

from app.mainwindow.shared import *
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.main_window import MainWindow


class SearchMultiMixin:
    def _open_multi_dest_search(self: Any):
        dialog = MultiDestDialog(self, self.prefs)
        dialog.search_requested.connect(self._start_multi_search)
        dialog.exec()
    def _guard_manual_browser_for_new_search(self: Any, action_name: str) -> bool:
        """수동 모드 브라우저가 열려 있을 때 새 검색 진행 여부를 확인"""
        if not self.active_searcher:
            return True

        reply = QMessageBox.question(
            self,
            "수동 모드 브라우저 유지",
            f"수동 모드 브라우저가 열려 있습니다.\n닫고 {action_name}을(를) 시작할까요?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._close_active_browser(confirm=False)
            return True

        self.log_viewer.append_log(f"ℹ️ {action_name} 취소: 수동 모드 브라우저를 유지했습니다.")
        return False
    def _start_multi_search(self: Any, origin, destinations, dep, ret, adults, cabin_class):
        self._stop_alert_worker_if_running()
        if not self._ensure_no_running_search():
            return

        if not self._guard_manual_browser_for_new_search("다중 검색"):
            return

        self.log_viewer.clear()
        self.log_viewer.append_log(f"🌍 다중 목적지 검색 시작: {', '.join(destinations)} [{cabin_class}]")
        
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat("다중 목적지 검색 중...")
        self.tabs.setCurrentIndex(2)  # Logs tab
        
        max_results = self.prefs.get_max_results()
        self.multi_worker = MultiSearchWorker(
            origin,
            destinations,
            dep,
            ret,
            adults,
            cabin_class,
            max_results,
            telemetry_callback=self._emit_telemetry_event,
        )
        self.multi_worker.progress.connect(self._update_progress)
        self.multi_worker.single_finished.connect(self._on_multi_single_finished)
        self.multi_worker.all_finished.connect(self._multi_search_finished)
        self.multi_worker.start()
    def _on_multi_single_finished(self: Any, dest, results):
        if results:
            best = min(results, key=lambda x: x.price)
            self.log_viewer.append_log(
                f"📌 [{dest}] 중간 결과: {len(results)}건, 최저가 {best.price:,}원 ({best.airline})"
            )
        else:
            self.log_viewer.append_log(f"📌 [{dest}] 중간 결과: 검색 결과 없음")
    def _multi_search_finished(self: Any, results):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("다중 검색 완료")
        
        # Show results dialog
        dialog = MultiDestResultDialog(results, self)
        dialog.exec()
        
        self.log_viewer.append_log(f"✅ 다중 목적지 검색 완료: {len(results)}개 목적지")

    # --- Date Range Search ---



