"""SearchSingleMixin methods extracted from MainWindow."""

from app.mainwindow.shared import (
    QMessageBox,
    SearchWorker,
    config,
    datetime,
    logger,
    scraper_config,
    time,
)
from typing import TYPE_CHECKING, Any

from app.mainwindow.filtering import lowest_effective_price

if TYPE_CHECKING:
    from app.main_window import MainWindow


class SearchSingleMixin:
    def _start_search(self: Any, origin, dest, dep, ret, adults, cabin_class="ECONOMY", force_refresh=False):
        self._stop_alert_worker_if_running()
        if not self._ensure_no_running_search():
            return

        if not self._guard_manual_browser_for_new_search("새 검색"):
            return

        if hasattr(self, "search_panel") and hasattr(self.search_panel, "consume_force_refresh"):
            force_refresh = bool(force_refresh or self.search_panel.consume_force_refresh())

        # Save search params for later use
        panel_params = {}
        if hasattr(self.search_panel, "spin_child"):
            panel_params["child"] = self.search_panel.spin_child.value()
        if hasattr(self.search_panel, "spin_infant"):
            panel_params["infant"] = self.search_panel.spin_infant.value()
        self.current_search_params = config.normalize_search_params(
            {
                "origin": origin,
                "dest": dest,
                "dep": dep,
                "ret": ret,
                "adults": adults,
                "cabin_class": cabin_class,
                "is_domestic": bool(self.search_panel.rb_domestic.isChecked()),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                **panel_params,
            }
        )
        
        # Save to History
        self.prefs.add_history(self.current_search_params)
        self.prefs.save_last_search(self.current_search_params)
        
        # Refresh History Tab
        if hasattr(self, 'list_history'):
            self._refresh_history_tab()

        # Reset UI
        self.search_panel.set_searching(True)
        self.progress_bar.setRange(0, 0)
        cabin_label = {"ECONOMY": "이코노미", "BUSINESS": "비즈니스", "FIRST": "일등석"}.get(cabin_class, "이코노미")
        self.progress_bar.setFormat(f"항공권 검색 중... ({cabin_label})")
        self.table.setRowCount(0)
        # 표를 비웠으니 이전 결과도 비운다. 남겨두면 검색 중 필터 조작 시
        # 새 조건의 요약 아래에 이전 검색 결과가 다시 나타난다.
        self.all_results = []
        self._last_search_truncated = False
        summary_label = getattr(self, "result_summary_label", None)
        if summary_label is not None:
            summary_label.setText(f"{origin} → {dest} 검색 중...")
        manual_browser_open = self.active_searcher is not None
        if manual_browser_open and hasattr(self, "manual_status_label"):
            self.manual_status_label.setText("🖐️ <b>수동 모드 유지 중</b> - 브라우저 닫기 가능")
        self.manual_frame.setVisible(manual_browser_open)
        self.log_viewer.clear()
        if force_refresh:
            self.statusBar().showMessage("캐시 무시 재조회 실행 중...")
            self.log_viewer.append_log("강제 재조회: 캐시를 무시하고 새로 검색합니다.")
        self.log_viewer.append_log(f"검색 프로세스 시작... (좌석등급: {cabin_label})")
        self.tabs.setCurrentIndex(2)  # Switch to logs
        
        # Start Worker
        max_results = self.prefs.get_max_results()
        self.worker = SearchWorker(
            origin,
            dest,
            dep,
            ret,
            adults,
            cabin_class,
            max_results,
            telemetry_callback=self._emit_telemetry_event,
            force_refresh=force_refresh,
            child=self.current_search_params.get("child", 0),
            infant=self.current_search_params.get("infant", 0),
        )
        self.worker.progress.connect(self._update_progress)
        self.worker.finished.connect(self._search_finished)
        self.worker.error.connect(self._search_error)
        self.worker.manual_mode_signal.connect(self._activate_manual_mode)
        self.worker.start()
    def _update_progress(self: Any, msg):
        now = time.monotonic()
        dedup_window = max(
            0, int(getattr(scraper_config, "PROGRESS_LOG_DEDUP_WINDOW_MS", 300))
        ) / 1000.0
        if msg == self._last_progress_msg and (now - self._last_progress_ts) < dedup_window:
            return
        self._last_progress_msg = msg
        self._last_progress_ts = now
        status_bar = self.statusBar()
        if status_bar is not None:
            status_bar.showMessage(msg)
        self.progress_bar.setFormat(msg)
        self.log_viewer.append_log(msg)
    def _search_finished(self: Any, results):
        self.search_panel.set_searching(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        
        if results:
            self.all_results = results
            self.results = results
            if hasattr(self, "_emit_telemetry_event"):
                self._emit_telemetry_event(
                    {
                        "event_type": "ui_search_finished",
                        "success": True,
                        "route": f"{self.current_search_params.get('origin', '')}->{self.current_search_params.get('dest', '')}",
                        "result_count": len(results),
                        "extraction_source": getattr(results[0], "extraction_source", ""),
                        "confidence": getattr(results[0], "confidence", 0.0),
                        "manual_mode": bool(getattr(self, "active_searcher", None)),
                    }
                )
            
            # Save price history
            if self.current_search_params:
                self._persist_successful_search(results)
            
            # 결과는 기본가 순이므로 첫 항목이 아니라 비교가(혜택 반영) 최솟값을 쓴다
            best_price = lowest_effective_price(results)
            self.progress_bar.setFormat(f"✨ 검색 완료! 최저가: {best_price:,}원 🏆")
            self.log_viewer.append_log(f"✅ 검색 완료. {len(results)}건 발견, 최저가: {best_price:,}원")
            self._last_search_truncated = False
            if hasattr(self, "worker") and self.worker and hasattr(self.worker, "searcher"):
                metrics = self.worker.searcher.get_search_metrics()
                if metrics.get("api_pages_truncated"):
                    # 요약 바에도 경고를 띄운다 (로그 탭은 결과 탭 전환 후 보이지 않는다)
                    self._last_search_truncated = True
                    self.log_viewer.append_log(
                        "⚠️ Interpark API 페이지 상한에 도달해 일부 결과가 누락됐을 수 있습니다."
                    )
                poll_attempts = metrics.get("api_status_poll_attempts")
                if metrics.get("api_failure_reason") == "international_api_status_timeout":
                    self.log_viewer.append_log(
                        f"⚠️ 국제선 API 상태 대기 시간 초과 (poll {poll_attempts}회)"
                    )
            self._apply_filter()
            self.tabs.setCurrentIndex(0)  # Switch to results
        else:
            self.progress_bar.setFormat("💭 검색 결과 없음")
            self.log_viewer.append_log("⚠️ 검색 결과가 없습니다.")
            if hasattr(self, "_emit_telemetry_event"):
                self._emit_telemetry_event(
                    {
                        "event_type": "ui_search_finished",
                        "success": False,
                        "route": f"{self.current_search_params.get('origin', '')}->{self.current_search_params.get('dest', '')}",
                        "result_count": 0,
                        "manual_mode": bool(getattr(self, "active_searcher", None)),
                        "error_code": "NO_RESULT",
                    }
                )
            # 이전 검색 결과를 비워 필터 조작으로 되살아나지 않게 한다
            self.all_results = []
            self.results = []
            self._last_search_truncated = False
            if hasattr(self.table, "set_empty_message"):
                self.table.set_empty_message(None)
            self.table.update_data([])
            if hasattr(self, "_update_result_summary"):
                self._update_result_summary([])
            self.tabs.setCurrentIndex(0)
            QMessageBox.information(
                self,
                "결과 없음",
                "이 조건으로 조회된 항공권이 없습니다.\n날짜나 공항을 바꿔 다시 검색해 보세요.",
            )
    def _record_persistence_warning(self: Any, action_name: str, error: Exception):
        logger.warning("%s failed after successful search: %s", action_name, error)
        try:
            self.log_viewer.append_log(f"⚠️ {action_name} 실패: {error}")
        except Exception:
            pass

    def _persist_successful_search(self: Any, results):
        origin = self.current_search_params.get('origin', '')
        dest = self.current_search_params.get('dest', '')
        dep = self.current_search_params.get('dep', '')

        try:
            self.db.add_price_history_batch(origin, dest, dep, results)
        except Exception as e:
            self._record_persistence_warning("가격 기록 저장", e)

        try:
            self.db.log_search(
                origin,
                dest,
                dep,
                self.current_search_params.get('ret'),
                self.current_search_params.get('adults', 1),
                len(results),
                results[0].price if results else None
            )
        except Exception as e:
            self._record_persistence_warning("검색 로그 저장", e)

        try:
            self.db.save_last_search_results(self.current_search_params, results)
        except Exception as e:
            self._record_persistence_warning("마지막 검색 결과 저장", e)

        try:
            self._check_price_alerts(results)
        except Exception as e:
            self._record_persistence_warning("가격 알림 확인", e)

    def _check_price_alerts(self: Any, results):
        """검색 완료 후 활성 가격 알림 체크"""
        if not results or not self.current_search_params:
            return
        
        try:
            alerts = self.db.get_active_alerts()
            origin = self.current_search_params.get('origin', '').upper()
            dest = self.current_search_params.get('dest', '').upper()
            dep = self.current_search_params.get('dep', '')
            ret = self.current_search_params.get('ret')
            adults = int(self.current_search_params.get('adults', 1) or 1)
            cabin = (self.current_search_params.get('cabin_class', 'ECONOMY') or 'ECONOMY').upper()
            min_price = results[0].price if results else 0
            
            for alert in alerts:
                # 노선 및 날짜 일치 확인
                if alert.origin.upper() != origin or alert.destination.upper() != dest:
                    continue
                if alert.departure_date and alert.departure_date != dep:
                    continue
                alert_ret = alert.return_date if alert.return_date else None
                if alert_ret and alert_ret != ret:
                    continue
                alert_cabin = (getattr(alert, "cabin_class", "ECONOMY") or "ECONOMY").upper()
                if alert_cabin != cabin:
                    continue
                alert_adults = int(getattr(alert, "adults", 1) or 1)
                if alert_adults != adults:
                    continue
                
                # 알림 마지막 체크 시간 및 가격 업데이트
                self.db.update_alert_check(alert.id, min_price)
                
                # 목표 가격 이하인 경우 알림 발생
                if min_price <= alert.target_price:
                    self.db.mark_alert_triggered(alert.id)
                    self.log_viewer.append_log(
                        f"🔔 가격 알림 발동! {origin}→{dest} [{cabin}] 최저가 {min_price:,}원 "
                        f"(목표: {alert.target_price:,}원 이하)"
                    )
                    QMessageBox.information(
                        self, "🔔 가격 알림",
                        f"목표 가격에 도달했습니다!\n\n"
                        f"노선: {origin} → {dest}\n"
                        f"좌석: {cabin}\n"
                        f"최저가: {min_price:,}원\n"
                        f"목표 가격: {alert.target_price:,}원 이하"
                    )
        except Exception as e:
            logger.debug(f"가격 알림 체크 중 오류 (무시됨): {e}")
    def _search_error(self: Any, err_msg):
        self.search_panel.set_searching(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("❌ 오류 발생")
        self.log_viewer.append_log(f"❌ 오류 발생: {err_msg}")
        if hasattr(self, "_emit_telemetry_event"):
            self._emit_telemetry_event(
                {
                    "event_type": "ui_search_error",
                    "success": False,
                    "route": f"{self.current_search_params.get('origin', '')}->{self.current_search_params.get('dest', '')}",
                    "error_code": "UI_SEARCH_ERROR",
                    "details": {"message": err_msg},
                }
            )

        msg_lower = err_msg.lower()
        if "브라우저 오류" in err_msg or "browser" in msg_lower or "playwright" in msg_lower:
            QMessageBox.critical(
                self,
                "브라우저 오류",
                "브라우저를 시작할 수 없습니다.\n\n"
                "해결 방법:\n"
                "1. Chrome 또는 Edge 설치\n"
                "2. 또는: playwright install chromium\n\n"
                f"상세 오류:\n{err_msg}"
            )
        elif "네트워크 오류" in err_msg or "network" in msg_lower:
            QMessageBox.critical(
                self,
                "네트워크 오류",
                "네트워크 연결에 실패했습니다.\n"
                "인터넷 연결 상태를 확인한 뒤 다시 시도해주세요.\n\n"
                f"상세 오류:\n{err_msg}"
            )
        else:
            QMessageBox.critical(self, "오류", f"검색 중 오류 발생:\n{err_msg}")
