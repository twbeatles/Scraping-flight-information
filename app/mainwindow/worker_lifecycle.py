"""WorkerLifecycleMixin methods extracted from MainWindow."""

from app.mainwindow.shared import *
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.main_window import MainWindow


class WorkerLifecycleMixin:
    def _get_running_workers(self: Any):
        """현재 실행 중인 워커 목록 반환"""
        running_workers = []
        if self.worker and self.worker.isRunning():
            running_workers.append(("일반 검색", self.worker))
        if self.multi_worker and self.multi_worker.isRunning():
            running_workers.append(("다중 목적지 검색", self.multi_worker))
        if self.date_worker and self.date_worker.isRunning():
            running_workers.append(("날짜 범위 검색", self.date_worker))
        if self.alert_worker and self.alert_worker.isRunning():
            running_workers.append(("자동 가격 알림 점검", self.alert_worker))
        return running_workers
    def _ensure_no_running_search(self: Any):
        """새 검색 시작 전 동시 실행 여부 확인"""
        running_workers = self._get_running_workers()
        if not running_workers:
            return True

        running_names = ", ".join(name for name, _ in running_workers)
        QMessageBox.warning(
            self,
            "검색 진행 중",
            f"이미 검색이 진행 중입니다: {running_names}\n\n"
            "Esc로 현재 검색을 취소하거나 완료 후 다시 시도해주세요."
        )
        return False
    def _stop_alert_worker_if_running(self: Any):
        if self.alert_worker and self.alert_worker.isRunning():
            self.alert_worker.cancel()
            self.alert_worker.requestInterruption()
            self.alert_worker.wait(3000)
    def _on_escape(self: Any):
        """Escape 키 처리 - 검색 취소 및 브라우저 정리"""
        running_workers = self._get_running_workers()

        if not running_workers:
            if self.active_searcher:
                self._close_active_browser(confirm=True)
            return

        # 중복 취소 방지
        if self._cancelling:
            return
        self._cancelling = True

        try:
            reply = QMessageBox.question(
                self, "검색 취소", "진행 중인 검색 작업을 취소하시겠습니까?\n(브라우저가 안전하게 종료됩니다)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            for worker_name, worker in running_workers:
                if hasattr(worker, 'cancel'):
                    worker.cancel()
                worker.requestInterruption()
                if not worker.wait(5000):
                    self.log_viewer.append_log(f"⚠️ {worker_name} 종료 지연 - 추가 대기 중")
                    if not worker.wait(2000):
                        QMessageBox.warning(
                            self,
                            "종료 지연",
                            f"{worker_name} 작업이 아직 종료되지 않았습니다.\n"
                            "잠시 후 다시 Esc를 눌러 취소를 재시도해주세요.",
                        )
                        self.log_viewer.append_log(f"⚠️ {worker_name} 종료 미완료 - 강제 종료는 수행하지 않습니다.")
                self.log_viewer.append_log(f"⚠️ {worker_name} 취소 요청 완료")

            self.search_panel.set_searching(False)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("검색 취소됨")
            self.log_viewer.append_log("⚠️ 사용자가 검색을 취소했습니다. 브라우저가 정리되었습니다.")
        finally:
            self._cancelling = False



