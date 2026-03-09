"""ManualModeMixin methods extracted from MainWindow."""

from app.mainwindow.shared import *
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.main_window import MainWindow


class ManualModeMixin:
    def _activate_manual_mode(self: Any, searcher):
        self.active_searcher = searcher
        self.search_panel.set_searching(False)
        if hasattr(self, "_emit_telemetry_event"):
            self._emit_telemetry_event(
                {
                    "event_type": "manual_mode_activated",
                    "success": False,
                    "route": f"{self.current_search_params.get('origin', '')}->{self.current_search_params.get('dest', '')}",
                    "manual_mode": True,
                    "error_code": "AUTO_EXTRACTION_FAILED",
                }
            )
        
        self.manual_frame.setVisible(True)
        if hasattr(self, "manual_status_label"):
            self.manual_status_label.setText("🖐️ <b>수동 모드 활성화됨</b> - 브라우저가 유지됩니다")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(50)
        self.progress_bar.setFormat("수동 모드 대기 중...")
        self.log_viewer.append_log("수동 모드로 전환됨.")
        
        QMessageBox.warning(self, "수동 모드 전환", 
                            "자동 추출에 실패했습니다.\n"
                            "브라우저창이 유지됩니다. 직접 검색 후 '데이터 추출하기' 버튼을 누르세요.")
    def _manual_extract(self: Any):
        if not self.active_searcher:
            return

        route = f"{self.current_search_params.get('origin', '')}->{self.current_search_params.get('dest', '')}"
        try:
            self.log_viewer.append_log("수동 추출 시도...")
            results = self.active_searcher.extract_manual()
            if results:
                if hasattr(self, "_emit_telemetry_event"):
                    self._emit_telemetry_event(
                        {
                            "event_type": "ui_manual_extract_finished",
                            "success": True,
                            "route": route,
                            "manual_mode": True,
                            "result_count": len(results),
                            "extraction_source": getattr(results[0], "extraction_source", ""),
                            "confidence": getattr(results[0], "confidence", 0.0),
                        }
                    )
                self._search_finished(results)
            else:
                if hasattr(self, "_emit_telemetry_event"):
                    self._emit_telemetry_event(
                        {
                            "event_type": "ui_manual_extract_finished",
                            "success": False,
                            "route": route,
                            "manual_mode": True,
                            "result_count": 0,
                            "error_code": "MANUAL_NO_RESULT",
                        }
                    )
                self.log_viewer.append_log("수동 추출 실패: 데이터 없음")
                QMessageBox.warning(self, "실패", "데이터를 찾을 수 없습니다.")
        except Exception as e:
            if hasattr(self, "_emit_telemetry_event"):
                self._emit_telemetry_event(
                    {
                        "event_type": "ui_manual_extract_finished",
                        "success": False,
                        "route": route,
                        "manual_mode": True,
                        "result_count": 0,
                        "error_code": "MANUAL_EXTRACT_ERROR",
                        "details": {"message": str(e)},
                    }
                )
            QMessageBox.critical(self, "오류", str(e))
        finally:
            if hasattr(self, "manual_status_label"):
                self.manual_status_label.setText("🖐️ <b>수동 모드 유지 중</b> - 필요 시 다시 추출 가능합니다")
    def _close_active_browser(self: Any, confirm: bool = True):
        if not self.active_searcher:
            return
        if confirm:
            reply = QMessageBox.question(
                self,
                "브라우저 닫기",
                "수동 모드 브라우저를 닫으시겠습니까?\n(열려있는 페이지는 종료됩니다)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        try:
            self.active_searcher.close()
            self.log_viewer.append_log("✅ 수동 모드 브라우저를 닫았습니다.")
        except Exception as e:
            logger.debug(f"Failed to close manual browser: {e}")
        finally:
            self.active_searcher = None
            self.manual_frame.setVisible(False)



