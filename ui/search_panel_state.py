"""Search panel preset/profile/state mixin."""

from ui.search_panel_shared import *


class SearchPanelStateMixin(SearchPanelMixinBase):
    def _refresh_profiles(self) -> None:
        self.cb_profiles.blockSignals(True)
        self.cb_profiles.clear()
        self.cb_profiles.addItem("- 프로필 선택 -", None)
        profiles = self.prefs.get_all_profiles()
        for name in profiles.keys():
            self.cb_profiles.addItem(name, name)
        self.cb_profiles.blockSignals(False)

    def _save_current_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "프로필 저장", "프로필 이름 (예: 제주 가족여행):")
        if ok and name:
            params = {
                "origin": self.cb_origin.currentData() or self.cb_origin.currentText(),
                "dest": self.cb_dest.currentData() or self.cb_dest.currentText(),
                "dep": self.date_dep.date().toString("yyyyMMdd"),
                "ret": self.date_ret.date().toString("yyyyMMdd") if self.rb_round.isChecked() else None,
                "adults": self.spin_adults.value(),
                "cabin_class": self.cb_cabin_class.currentData() or "ECONOMY",
            }
            self.prefs.save_profile(name, params)
            self._refresh_profiles()
            QMessageBox.information(self, "저장 완료", f"'{name}' 프로필이 저장되었습니다.")

    def _load_selected_profile(self) -> None:
        name = self.cb_profiles.currentData()
        if not name: return
        
        data = self.prefs.get_profile(name)
        if not data: return
        
        # Same logic as history restore
        try:
            # Origin
            idx_o = self.cb_origin.findData(data['origin'])
            if idx_o >= 0: self.cb_origin.setCurrentIndex(idx_o)
            
            # Dest
            idx_d = self.cb_dest.findData(data['dest'])
            if idx_d >= 0: self.cb_dest.setCurrentIndex(idx_d)
            
            # Date
            qt_date = QDate.fromString(data['dep'], "yyyyMMdd")
            self.date_dep.setDate(qt_date)
            
            if data['ret']:
                self.rb_round.setChecked(True)
                self.date_ret.setEnabled(True)
                self.date_ret.setDate(QDate.fromString(data['ret'], "yyyyMMdd"))
            else:
                self.rb_oneway.setChecked(True)
                self._toggle_return_date()
                
            self.spin_adults.setValue(data['adults'])

            cabin = data.get("cabin_class")
            if cabin:
                idx_c = self.cb_cabin_class.findData(cabin)
                if idx_c >= 0:
                    self.cb_cabin_class.setCurrentIndex(idx_c)
            
        except Exception as e:
            QMessageBox.warning(self, "오류", f"프로필 로드 중 오류: {e}")

    def _open_settings(self) -> None:
        from ui.dialogs import SettingsDialog
        top = self.window()
        dlg = SettingsDialog(self, self.prefs, getattr(top, "db", None))
        dlg.exec()
        # Refresh UI after settings close (presets might have changed)
        self._refresh_combos()
        self._refresh_profiles()
        main_win = cast(Any, top)
        if hasattr(main_win, "_configure_alert_auto_timer"):
            main_win._configure_alert_auto_timer()
    
    def save_settings(self) -> None:
        """입력값을 QSettings에 저장 (프로그램 종료 시 호출)"""
        settings = QSettings("FlightBot", "FlightComparisonBot")
        settings.setValue("origin", self.cb_origin.currentText())
        settings.setValue("dest", self.cb_dest.currentText())
        settings.setValue("dep_date", self.date_dep.date().toString("yyyyMMdd"))
        if hasattr(self, 'date_ret') and self.date_ret.isEnabled():
            settings.setValue("ret_date", self.date_ret.date().toString("yyyyMMdd"))
        settings.setValue("adults", self.spin_adults.value())
        settings.setValue("cabin_class", self.cb_cabin_class.currentData() or "ECONOMY")
        settings.setValue("is_roundtrip", self.rb_round.isChecked())
        if hasattr(self, 'rb_domestic'):
            settings.setValue("is_domestic", self.rb_domestic.isChecked())
    
    def restore_settings(self) -> None:
        """저장된 입력값 복원 (프로그램 시작 시 호출)"""
        settings = QSettings("FlightBot", "FlightComparisonBot")
        
        # Origin
        origin = settings.value("origin", "")
        if origin:
            idx = self.cb_origin.findText(origin, Qt.MatchFlag.MatchContains)
            if idx >= 0:
                self.cb_origin.setCurrentIndex(idx)
        
        # Destination
        dest = settings.value("dest", "")
        if dest:
            idx = self.cb_dest.findText(dest, Qt.MatchFlag.MatchContains)
            if idx >= 0:
                self.cb_dest.setCurrentIndex(idx)
        
        # Dates
        dep_date = settings.value("dep_date", "")
        if dep_date:
            qdate = QDate.fromString(dep_date, "yyyyMMdd")
            if qdate.isValid() and qdate >= QDate.currentDate():
                self.date_dep.setDate(qdate)
        
        ret_date = settings.value("ret_date", "")
        if ret_date and hasattr(self, 'date_ret'):
            qdate = QDate.fromString(ret_date, "yyyyMMdd")
            if qdate.isValid() and qdate >= QDate.currentDate():
                self.date_ret.setDate(qdate)
        
        # Adults
        adults = settings.value("adults", 1, type=int)
        self.spin_adults.setValue(adults)

        cabin = settings.value("cabin_class", "ECONOMY")
        idx_c = self.cb_cabin_class.findData(cabin)
        if idx_c >= 0:
            self.cb_cabin_class.setCurrentIndex(idx_c)
        
        # Trip type
        is_roundtrip = settings.value("is_roundtrip", True, type=bool)
        self.rb_round.setChecked(is_roundtrip)
        self.rb_oneway.setChecked(not is_roundtrip)
        
        # Domestic/International
        is_domestic = settings.value("is_domestic", False, type=bool)
        if hasattr(self, 'rb_domestic') and hasattr(self, 'rb_intl'):
            self.rb_domestic.setChecked(is_domestic)
            self.rb_intl.setChecked(not is_domestic)
            self._on_flight_type_changed()
