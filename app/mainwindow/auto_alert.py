"""AutoAlertMixin methods extracted from MainWindow."""

from app.mainwindow.shared import (
    AlertAutoCheckWorker,
    QMessageBox,
    datetime,
    logger,
)
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.main_window import MainWindow


class AutoAlertMixin:
    def _configure_alert_auto_timer(self: Any):
        """가격 알림 자동 점검 타이머 구성."""
        cfg = self.prefs.get_alert_auto_check()
        enabled = cfg.get("enabled", False)
        interval_min = max(5, int(cfg.get("interval_min", 30)))
        self._alert_auto_timer.stop()
        if enabled:
            self._alert_auto_timer.start(interval_min * 60 * 1000)
            self.log_viewer.append_log(f"🔔 자동 알림 점검 활성화 ({interval_min}분 주기)")
        else:
            self.log_viewer.append_log("🔔 자동 알림 점검 비활성화")
    def _run_auto_alert_check(self: Any, force: bool = False):
        """QTimer 기반 자동 가격 알림 점검."""
        if self.alert_worker and self.alert_worker.isRunning():
            if force:
                self.log_viewer.append_log("🔔 자동 알림 점검이 이미 진행 중입니다.")
            return
        if self._get_running_workers():
            if force:
                self.log_viewer.append_log("🔔 다른 검색 작업이 진행 중이라 자동 알림 점검을 시작하지 않았습니다.")
            return

        try:
            alerts = self.db.get_active_alerts()
        except Exception as e:
            summary = str(e).strip().splitlines()[0] if str(e).strip() else "알 수 없는 오류"
            self._last_alert_auto_error = f"DB 조회 실패: {summary}"
            self.log_viewer.append_log(f"⚠️ 자동 알림 점검 DB 조회 실패: {summary}")
            self._emit_telemetry_event(
                {
                    "event_type": "auto_alert_cycle_start",
                    "success": False,
                    "error_code": "AUTO_ALERT_DB_READ_FAILED",
                    "details": {"message": summary},
                }
            )
            return
        if not alerts:
            if force:
                self.log_viewer.append_log("🔔 점검할 활성 가격 알림이 없습니다.")
            return
        self._last_alert_auto_check_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._last_alert_auto_error = ""
        self._emit_telemetry_event(
            {
                "event_type": "auto_alert_cycle_start",
                "success": True,
                "result_count": len(alerts),
            }
        )

        self.alert_worker = AlertAutoCheckWorker(
            alerts,
            max_results=max(50, min(self.prefs.get_max_results(), 200)),
            telemetry_callback=self._emit_telemetry_event,
        )
        self.alert_worker.progress.connect(lambda msg: self.log_viewer.append_log(msg))
        self.alert_worker.alert_checked.connect(self._on_auto_alert_checked)
        self.alert_worker.alert_check_failed.connect(self._on_auto_alert_check_failed)
        self.alert_worker.alert_no_result.connect(self._on_auto_alert_no_result)
        self.alert_worker.alert_hit.connect(self._on_auto_alert_hit)
        self.alert_worker.done.connect(self._on_auto_alert_done)
        self.alert_worker.start()
    def _on_auto_alert_checked(self: Any, alert_id: int, current_price: int):
        try:
            self.db.update_alert_check(alert_id, current_price, last_error="")
        except Exception as e:
            logger.debug(f"Failed to update auto alert check: {e}")
    def _on_auto_alert_check_failed(self: Any, alert_id: int, origin: str, dest: str, error_message: str):
        summary = (error_message or "").strip().splitlines()[0] if error_message else "알 수 없는 오류"
        self._last_alert_auto_error = f"{origin}->{dest}: {summary}"
        try:
            self.db.update_alert_check(alert_id, None, last_error=summary)
        except Exception as e:
            logger.debug(f"Failed to update auto alert failure: {e}")
        self.log_viewer.append_log(f"⚠️ 자동 알림 점검 실패: {origin}->{dest} - {summary}")
    def _on_auto_alert_no_result(self: Any, alert_id: int, origin: str, dest: str):
        message = "NO_RESULT: 검색 결과 없음"
        try:
            self.db.update_alert_check(alert_id, None, last_error=message)
        except Exception as e:
            logger.debug(f"Failed to update auto alert no-result: {e}")
        self.log_viewer.append_log(f"ℹ️ 자동 알림 결과 없음: {origin}->{dest}")
    def _on_auto_alert_hit(self: Any, alert_id: int, price: int, target: int, origin: str, dest: str, cabin: str):
        try:
            self.db.mark_alert_triggered(alert_id)
        except Exception as e:
            logger.debug(f"Failed to mark auto alert triggered: {e}")
        self.log_viewer.append_log(
            f"🔔 자동 알림 발동! {origin}->{dest} [{cabin}] {price:,}원 (목표 {target:,}원 이하)"
        )
        show_modal = True
        try:
            show_modal = bool(self.prefs.get_alert_hit_modal_enabled())
        except Exception:
            show_modal = True
        if show_modal:
            QMessageBox.information(
                self,
                "🔔 자동 가격 알림",
                f"노선: {origin} → {dest}\n좌석: {cabin}\n최저가: {price:,}원\n목표가: {target:,}원 이하",
            )
    def _on_auto_alert_done(self: Any, checked: int, hits: int):
        self._last_alert_auto_check_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_viewer.append_log(f"🔔 자동 점검 완료: {checked}건 확인, {hits}건 발동")
        self._emit_telemetry_event(
            {
                "event_type": "auto_alert_cycle_done",
                "success": True,
                "result_count": checked,
                "details": {"hits": hits},
            }
        )
        self.alert_worker = None

