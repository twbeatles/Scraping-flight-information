"""AutoAlertMixin methods extracted from MainWindow."""

from app.mainwindow.shared import *
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
    def _run_auto_alert_check(self: Any):
        """QTimer 기반 자동 가격 알림 점검."""
        if self.alert_worker and self.alert_worker.isRunning():
            return
        if self._get_running_workers():
            return

        alerts = self.db.get_active_alerts()
        if not alerts:
            return
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
        self.alert_worker.alert_hit.connect(self._on_auto_alert_hit)
        self.alert_worker.done.connect(self._on_auto_alert_done)
        self.alert_worker.start()
    def _on_auto_alert_checked(self: Any, alert_id: int, current_price: int):
        try:
            self.db.update_alert_check(alert_id, current_price)
        except Exception as e:
            logger.debug(f"Failed to update auto alert check: {e}")
    def _on_auto_alert_hit(self: Any, alert_id: int, price: int, target: int, origin: str, dest: str, cabin: str):
        try:
            self.db.mark_alert_triggered(alert_id)
        except Exception as e:
            logger.debug(f"Failed to mark auto alert triggered: {e}")
        self.log_viewer.append_log(
            f"🔔 자동 알림 발동! {origin}->{dest} [{cabin}] {price:,}원 (목표 {target:,}원 이하)"
        )
        QMessageBox.information(
            self,
            "🔔 자동 가격 알림",
            f"노선: {origin} → {dest}\n좌석: {cabin}\n최저가: {price:,}원\n목표가: {target:,}원 이하",
        )
    def _on_auto_alert_done(self: Any, checked: int, hits: int):
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



