"""TelemetryMixin methods extracted from MainWindow."""

from app.mainwindow.shared import *


class TelemetryMixin:
    def _emit_telemetry_event(self, payload: dict):
        """워커/스크래퍼 텔레메트리 이벤트를 DB+JSONL로 저장."""
        if not payload:
            return
        try:
            self.db.log_telemetry_event(
                event_type=payload.get("event_type", "unknown"),
                success=bool(payload.get("success", True)),
                error_code=payload.get("error_code", ""),
                route=payload.get("route", ""),
                manual_mode=bool(payload.get("manual_mode", False)),
                selector_name=payload.get("selector_name", ""),
                extraction_source=payload.get("extraction_source", ""),
                confidence=float(payload.get("confidence", 0.0) or 0.0),
                duration_ms=payload.get("duration_ms"),
                result_count=payload.get("result_count"),
                details=payload.get("details", {}),
            )
        except Exception as e:
            logger.debug(f"Telemetry logging failed: {e}")
