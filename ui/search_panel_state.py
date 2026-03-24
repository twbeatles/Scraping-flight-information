"""Search panel preset/profile/state mixin."""

from ui.search_panel_shared import *
from ui.search_panel_params import apply_search_params_to_panel, get_panel_search_params


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
            self.prefs.save_profile(name, self.get_search_params())
            self._refresh_profiles()
            QMessageBox.information(self, "저장 완료", f"'{name}' 프로필이 저장되었습니다.")

    def _load_selected_profile(self) -> None:
        name = self.cb_profiles.currentData()
        if not name: return
        
        data = self.prefs.get_profile(name)
        if not data: return
        
        try:
            self.apply_search_params(data)
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

    def get_search_params(
        self,
        *,
        include_timestamp: bool = False,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        return get_panel_search_params(
            self,
            include_timestamp=include_timestamp,
            timestamp=timestamp,
        )

    def apply_search_params(self, params: dict[str, Any] | None) -> dict[str, Any]:
        return apply_search_params_to_panel(self, params)
    
    def save_settings(self) -> None:
        """입력값을 QSettings에 저장 (프로그램 종료 시 호출)"""
        settings = QSettings("FlightBot", "FlightComparisonBot")
        params = self.get_search_params()
        settings.setValue("schema_version", config.SEARCH_PARAMS_SCHEMA_VERSION)
        settings.setValue("origin", params.get("origin", ""))
        settings.setValue("dest", params.get("dest", ""))
        settings.setValue("dep_date", params.get("dep", ""))
        settings.setValue("ret_date", params.get("ret") or "")
        settings.setValue("adults", params.get("adults", 1))
        settings.setValue("cabin_class", params.get("cabin_class", "ECONOMY"))
        settings.setValue("is_roundtrip", bool(params.get("ret")))
        settings.setValue("is_domestic", params.get("is_domestic", False))
        settings.sync()
    
    def restore_settings(self) -> None:
        """저장된 입력값 복원 (프로그램 시작 시 호출)"""
        settings = QSettings("FlightBot", "FlightComparisonBot")
        payload = {
            "origin": settings.value("origin", ""),
            "dest": settings.value("dest", ""),
            "dep": settings.value("dep_date", ""),
            "ret": settings.value("ret_date", ""),
            "adults": settings.value("adults", 1, int),
            "cabin_class": settings.value("cabin_class", "ECONOMY"),
            "is_domestic": (
                settings.value("is_domestic", False, bool)
                if settings.contains("is_domestic")
                else None
            ),
        }
        normalized = config.normalize_search_params(payload)
        if not normalized.get("origin") or not normalized.get("dest") or not normalized.get("dep"):
            return
        self.apply_search_params(normalized)
