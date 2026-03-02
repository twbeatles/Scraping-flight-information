"""AppLifecycleMixin methods extracted from MainWindow."""

from app.mainwindow.shared import *


class AppLifecycleMixin:
    def _open_main_settings(self):
        dlg = SettingsDialog(self, self.prefs, self.db)
        dlg.exec()
        self.search_panel._refresh_combos()
        self.search_panel._refresh_profiles()
        self._configure_alert_auto_timer()
    def _show_shortcuts(self):
        """키보드 단축키 다이얼로그 표시"""
        dlg = ShortcutsDialog(self)
        dlg.exec()
    def _open_price_alert_dialog(self):
        """가격 알림 관리 다이얼로그 열기"""
        dlg = PriceAlertDialog(self, self.db, self.prefs)
        dlg.exec()
    def _toggle_theme(self):
        """라이트/다크 테마 전환 및 저장"""
        if self.is_dark_theme:
            # 다크 -> 라이트
            self.setStyleSheet(LIGHT_THEME)
            self.btn_theme.setText("☀️")
            self.is_dark_theme = False
            self.prefs.set_theme("light")
        else:
            # 라이트 -> 다크
            self.setStyleSheet(DARK_THEME)
            self.btn_theme.setText("🌙")
            self.is_dark_theme = True
            self.prefs.set_theme("dark")
    def closeEvent(self, event):
        """창 닫기 시 워커 스레드 및 리소스 정리"""
        self._alert_auto_timer.stop()
        # Worker threads 정리 (안전한 종료 패턴)
        workers = [self.worker, self.multi_worker, self.date_worker, self.alert_worker]
        has_pending = False
        for worker in workers:
            if worker and worker.isRunning():
                if hasattr(worker, 'cancel'):
                    worker.cancel()
                worker.requestInterruption()  # 안전한 중단 요청
                if not worker.wait(5000):
                    logger.warning("Worker 스레드 종료 지연 - 추가 대기 시도")
                    if worker.wait(2000):
                        continue
                    logger.warning("Worker 스레드가 여전히 종료되지 않았습니다.")
                    has_pending = True

        if has_pending:
            QMessageBox.warning(
                self,
                "종료 지연",
                "일부 백그라운드 작업이 아직 종료되지 않았습니다.\n"
                "잠시 후 다시 종료를 시도해주세요.",
            )
            event.ignore()
            return
        
        # Active searcher 브라우저 종료
        if self.active_searcher:
            try:
                self.active_searcher.close()
            except Exception as e:
                logger.debug(f"Failed to close searcher: {e}")
        
        # 설정 저장
        try:
            if hasattr(self, 'search_panel'):
                self.search_panel.save_settings()
            self.prefs.save()
            self.db.close_all_connections()
        except Exception as e:
            logger.warning(f"Failed to save settings on exit: {e}")
        
        event.accept()
