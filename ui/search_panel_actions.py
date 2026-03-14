"""Search panel action/validation mixin."""

from ui.search_panel_shared import *


class SearchPanelActionsMixin:
    def _manage_preset(self, combo_widget=None):
        if not combo_widget:
            combo_widget = self.cb_dest
            
        current_text = combo_widget.currentText()
        
        menu = QMenu(self)
        add_action = menu.addAction("새로운 공항 추가 (Custom)")
        del_action = menu.addAction("선택된 공항 삭제 (Custom)")
        
        action = menu.exec(combo_widget.mapToGlobal(combo_widget.rect().bottomRight()))
        
        if action == add_action:
            # Default text: extract code if possible
            code = combo_widget.currentData() or ""
            if not code and " " in current_text:
                code = current_text.split(' ')[0]
                
            code, ok = QInputDialog.getText(self, "공항 추가", "공항/도시 코드 (예: JFK):", text=code)
            if ok and code:
                code = code.upper().strip()
                if not config.validate_airport_code(code):
                    QMessageBox.warning(self, "입력 오류", "공항/도시 코드는 3자리 영문이어야 합니다.")
                    return
                name, ok2 = QInputDialog.getText(self, "공항 추가", f"{code}의 한글 명칭:")
                if ok2:
                    self.prefs.add_preset(code, name)
                    self._refresh_combos()
                    QMessageBox.information(self, "추가 완료", f"{code} ({name}) 공항이 추가되었습니다.")
                    
        elif action == del_action:
            code = combo_widget.currentData()
            if not code:
                 QMessageBox.warning(self, "선택 없음", "삭제할 공항을 선택하세요.")
                 return

            if code in config.AIRPORTS:
                QMessageBox.warning(self, "삭제 불가", "기본 제공 공항은 삭제할 수 없습니다.\\n사용자가 추가한 공항만 삭제 가능합니다.")
            else:
                ret = QMessageBox.question(self, "삭제 확인", f"정말 {code} 공항을 목록에서 삭제하시겠습니까?", 
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if ret == QMessageBox.StandardButton.Yes:
                    self.prefs.remove_preset(code)
                    self._refresh_combos()

    def _refresh_combos(self):
        """출발/도착 콤보박스 모두 갱신"""
        for cb in [self.cb_origin, self.cb_dest]:
            current = cb.currentData()
            cb.clear()
            
            # 1. Standard Airports
            for code, name in config.AIRPORTS.items():
                cb.addItem(f"{code} ({name})", code)
                
            # 2. Custom Presets
            presets = self.prefs.get_all_presets()
            for code, name in presets.items():
                if code not in config.AIRPORTS:
                    cb.addItem(f"{code} ({name})", code)

            idx = cb.findData(current)
            if idx >= 0: cb.setCurrentIndex(idx)

    def _toggle_return_date(self):
        is_round = self.rb_round.isChecked()
        self.date_ret.setEnabled(is_round)
        if not is_round:
            self.date_ret.setStyleSheet("color: #555; background-color: #222;")
        else:
            self.date_ret.setStyleSheet("")

    def _on_search(self):
        # Save time preference
        self.prefs.set_preferred_time(self.spin_time_start.value(), self.spin_time_end.value())
        
        origin_raw = self.cb_origin.currentData() or self.cb_origin.currentText().split(' ')[0].strip()
        dest_raw = self.cb_dest.currentData() or self.cb_dest.currentText().split(' ')[0].strip()
        origin_code = origin_raw.strip().upper()
        dest_code = dest_raw.strip().upper()
        
        dep_date = self.date_dep.date()
        ret_date = self.date_ret.date() if self.rb_round.isChecked() else None
        
        dep = dep_date.toString("yyyyMMdd")
        ret = ret_date.toString("yyyyMMdd") if ret_date is not None else None
        adults = self.spin_adults.value()
        cabin_class = self.cb_cabin_class.currentData() or "ECONOMY"
        
        # 입력 유효성 검사
        if not origin_code or not dest_code:
            QMessageBox.warning(self, "입력 오류", "출발지와 도착지를 선택하세요.")
            return
        
        if not config.validate_airport_code(origin_code):
            QMessageBox.warning(self, "입력 오류", "출발지 코드가 올바르지 않습니다.\n예: ICN, GMP, SEL")
            return

        if not config.validate_airport_code(dest_code):
            QMessageBox.warning(self, "입력 오류", "도착지 코드가 올바르지 않습니다.\n예: NRT, HND, TYO")
            return

        if self.rb_domestic.isChecked():
            if (
                origin_code not in config.DOMESTIC_AIRPORT_CODES
                or dest_code not in config.DOMESTIC_AIRPORT_CODES
            ):
                QMessageBox.warning(
                    self,
                    "입력 오류",
                    "국내선 모드에서는 국내 공항/도시 코드만 사용할 수 있습니다.\n"
                    "예: GMP, CJU, PUS, TAE, ICN, SEL",
                )
                return

        if origin_code == dest_code:
            QMessageBox.warning(self, "입력 오류", "출발지와 도착지가 같습니다.")
            return
        
        # 날짜 유효성 검사
        today = QDate.currentDate()
        if dep_date < today:
            QMessageBox.warning(self, "날짜 오류", "출발일이 오늘보다 이전입니다.")
            return
        
        if ret_date is not None and ret_date < dep_date:
            QMessageBox.warning(self, "날짜 오류", "귀국일이 출발일보다 이전입니다.")
            return

        self.search_requested.emit(origin_code, dest_code, dep, ret, adults, cabin_class)


    def set_searching(self, searching):
        self.btn_search.setText("⏳ 검색 중..." if searching else "🔍 최저가 검색 시작")
        self.btn_search.setEnabled(not searching)
        self.cb_origin.setEnabled(not searching)
        self.cb_dest.setEnabled(not searching)
    
    def _on_flight_type_changed(self):
        """국내선/국제선 전환시 공항 목록 업데이트"""
        is_domestic = self.rb_domestic.isChecked()
        
        # 현재 선택 기억
        current_origin = self.cb_origin.currentData()
        current_dest = self.cb_dest.currentData()
        
        # 공항 목록 초기화
        self.cb_origin.clear()
        self.cb_dest.clear()
        
        if is_domestic:
            # 국내선: 한국 공항만
            domestic_airports = config.DOMESTIC_AIRPORTS
            for code, name in domestic_airports.items():
                self.cb_origin.addItem(f"{code} ({name})", code)
                self.cb_dest.addItem(f"{code} ({name})", code)
            
            # 기본값 설정 (김포-제주)
            self.cb_origin.setCurrentIndex(self.cb_origin.findData("GMP"))
            self.cb_dest.setCurrentIndex(self.cb_dest.findData("CJU"))
        else:
            # 국제선: 전체 공항
            for code, name in config.AIRPORTS.items():
                self.cb_origin.addItem(f"{code} ({name})", code)
                self.cb_dest.addItem(f"{code} ({name})", code)
            
            # 커스텀 프리셋도 출발지/도착지에 모두 추가 (중복 방지)
            try:
                presets = self.prefs.get_all_presets()
                for code, name in presets.items():
                    if code not in config.AIRPORTS:
                        if self.cb_origin.findData(code) < 0:
                            self.cb_origin.addItem(f"{code} ({name})", code)
                        if self.cb_dest.findData(code) < 0:
                            self.cb_dest.addItem(f"{code} ({name})", code)
            except Exception as e:
                logger.debug(f"Failed to add custom presets: {e}")
            
            # 기본값 설정 (인천-도쿄 나리타)
            self.cb_origin.setCurrentIndex(self.cb_origin.findData("ICN"))
            self.cb_dest.setCurrentIndex(self.cb_dest.findData("NRT"))
        
        # 이전 선택 복원 시도
        if current_origin:
            idx = self.cb_origin.findData(current_origin)
            if idx >= 0:
                self.cb_origin.setCurrentIndex(idx)
        if current_dest:
            idx = self.cb_dest.findData(current_dest)
            if idx >= 0:
                self.cb_dest.setCurrentIndex(idx)
