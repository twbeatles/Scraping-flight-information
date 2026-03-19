"""SessionMixin methods extracted from MainWindow."""

from app.mainwindow.shared import *
from typing import TYPE_CHECKING, Any
from app.session_manager import SessionManager

if TYPE_CHECKING:
    from app.main_window import MainWindow


class SessionMixin:
    def _save_session(self: Any):
        """현재 검색 결과를 파일로 저장"""
        if not self.all_results:
            QMessageBox.warning(self, "저장 실패", "저장할 검색 결과가 없습니다.\n먼저 검색을 수행해주세요.")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "세션 저장",
            f"flight_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json)"
        )
        
        if not filename:
            return
        
        if SessionManager.save_session(filename, self.current_search_params, self.all_results):
            QMessageBox.information(self, "저장 완료", f"세션이 저장되었습니다:\n{filename}")
            self.log_viewer.append_log(f"💾 세션 저장 완료: {filename}")
        else:
            QMessageBox.critical(self, "저장 실패", "세션 저장 중 오류가 발생했습니다.")
    def _load_session(self: Any):
        """저장된 세션 불러오기"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "세션 불러오기",
            "",
            "JSON Files (*.json)"
        )
        
        if not filename:
            return
        
        params, results, saved_at = SessionManager.load_session(filename)
        
        if not results:
            QMessageBox.warning(self, "불러오기 실패", "세션 파일을 읽을 수 없거나 결과가 없습니다.")
            return
        
        # 결과 표시
        self.all_results = results
        self.current_search_params = config.normalize_search_params(params)
        self._apply_filter()
        
        # 검색 조건 복원
        if params:
            try:
                self._restore_search_panel_from_params(params)
            except Exception as e:
                logger.debug(f"Failed to restore session params: {e}")
        
        saved_info = f" (저장: {saved_at[:16]})" if saved_at else ""
        QMessageBox.information(
            self, "불러오기 완료", 
            f"세션을 불러왔습니다{saved_info}\n\n결과: {len(results)}개 항공편"
        )
        self.log_viewer.append_log(f"📂 세션 불러오기 완료: {len(results)}개 결과")
    
    # --- Calendar View Methods ---
    def _restore_last_search(self: Any):
        """프로그램 시작 시 마지막 검색 결과 복원"""
        try:
            search_params, results, searched_at, hours_ago = self.db.get_last_search_results()
            
            if not results:
                self.log_viewer.append_log("ℹ️ 이전 검색 기록이 없습니다.")
                return
            
            # 검색 조건 복원
            self.current_search_params = config.normalize_search_params(search_params)
            self.all_results = results
            self.results = results
            
            # 검색 패널에 조건 복원
            try:
                self._restore_search_panel_from_params(search_params)
            except Exception as e:
                logger.debug(f"검색 조건 복원 실패: {e}")
            
            # 로그 및 상태 표시
            min_price = results[0].price if results else 0
            origin = self.current_search_params.get('origin', '?')
            dest = self.current_search_params.get('dest', '?')
            
            # 24시간 경과 여부는 비차단 안내만 표시
            if hours_ago >= 24:
                days_ago = int(hours_ago / 24)
                age_hours = int(hours_ago % 24)
                self.progress_bar.setFormat(f"⚠️ {days_ago}일 전 데이터 | 최저가: {min_price:,}원")
                status_bar = self.statusBar()
                if status_bar is not None:
                    status_bar.showMessage(
                        f"오래된 검색 데이터 복원됨 ({days_ago}일 {age_hours}시간 전) | 필요 시 새 검색 권장"
                    )
                self.log_viewer.append_log(
                    f"⚠️ 이전 검색 결과 복원 ({days_ago}일 {age_hours}시간 전): "
                    f"{origin}→{dest}, {len(results)}건, 최저가 {min_price:,}원"
                )
            else:
                # 24시간 이내 데이터
                hours_text = f"{int(hours_ago)}시간 전" if hours_ago >= 1 else f"{int(hours_ago * 60)}분 전"
                self.progress_bar.setFormat(f"📋 이전 검색 ({hours_text}) | 최저가: {min_price:,}원")
                self.log_viewer.append_log(
                    f"📋 이전 검색 결과 복원 ({hours_text}): "
                    f"{origin}→{dest}, {len(results)}건, 최저가 {min_price:,}원"
                )
            
            # 결과 탭으로 전환
            self.tabs.setCurrentIndex(0)
            self._apply_filter()
            
        except Exception as e:
            logger.error(f"마지막 검색 결과 복원 실패: {e}")
            self.log_viewer.append_log(f"ℹ️ 이전 검색 결과를 불러오지 못했습니다.")



