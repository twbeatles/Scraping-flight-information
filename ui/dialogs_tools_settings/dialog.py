"""Settings dialog shell (SRP: assembly and slot delegation only).

Tab content lives in `general_tab.py`, `presets_tab.py`, `data_tab.py`;
status text computation lives in `status_texts.py`.
"""

import logging
from typing import Any, cast

from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QLabel, QListWidget, QMessageBox, QPushButton,
    QSpinBox, QTabWidget, QVBoxLayout,
)

from ui.dialogs_tools_settings import data_tab, general_tab, presets_tab
from ui.dialogs_tools_settings.status_texts import (
    build_alert_auto_status_text,
    build_diagnostics_text,
)
from ui.styles import MODERN_THEME


logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Settings dialog; tab widgets are built by sibling tab modules."""

    spin_start: QSpinBox
    spin_end: QSpinBox
    spin_limit: QSpinBox
    chk_alert_auto: QCheckBox
    spin_alert_interval: QSpinBox
    chk_alert_hit_modal: QCheckBox
    lbl_alert_auto_status: QLabel
    lbl_diag: QLabel
    list_presets: QListWidget

    def __init__(self, parent=None, prefs=None, db=None):
        super().__init__(parent)
        self.prefs: Any = prefs
        self.db: Any = db if db is not None else getattr(parent, "db", None)
        self.setWindowTitle("⚙️ 설정 (Settings)")
        self.setMinimumSize(600, 500)  # Increased size for better content display
        self.setStyleSheet(MODERN_THEME)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(general_tab.build_general_tab(self), "일반")
        tabs.addTab(presets_tab.build_presets_tab(self), "목적지 관리")
        tabs.addTab(data_tab.build_data_tab(self), "데이터 관리")

        layout.addWidget(tabs)

        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _save_time_pref(self):
        self.prefs.set_preferred_time(self.spin_start.value(), self.spin_end.value())
        self.prefs.set_max_results(self.spin_limit.value())
        QMessageBox.information(self, "저장", "설정이 저장되었습니다.")

    def _save_alert_auto_check(self):
        self.prefs.set_alert_auto_check(
            self.chk_alert_auto.isChecked(),
            self.spin_alert_interval.value(),
        )
        if hasattr(self.prefs, "set_alert_hit_modal_enabled"):
            self.prefs.set_alert_hit_modal_enabled(self.chk_alert_hit_modal.isChecked())
        self._refresh_alert_auto_status()
        QMessageBox.information(self, "저장", "자동 알림 점검 설정이 저장되었습니다.")

    def _run_alert_auto_check_now(self):
        parent = cast(Any, self.parent())
        if not hasattr(parent, "_run_auto_alert_check"):
            QMessageBox.warning(self, "실행 불가", "자동 알림 점검을 실행할 수 없습니다.")
            return
        parent._run_auto_alert_check(force=True)
        self._refresh_alert_auto_status()

    def _refresh_alert_auto_status(self):
        cfg = self.prefs.get_alert_auto_check()
        summary = self.db.get_alert_check_summary() if self.db else {}
        self.lbl_alert_auto_status.setText(
            build_alert_auto_status_text(
                bool(cfg.get("enabled", False)),
                int(cfg.get("interval_min", 30)),
                summary if isinstance(summary, dict) else {},
            )
        )

    def _refresh_diagnostics(self):
        if not self.db:
            self.lbl_diag.setText("진단 데이터베이스를 사용할 수 없습니다.")
            return
        try:
            summary = self.db.get_telemetry_summary(hours=24)
            selector = self.db.get_selector_health()
            self.lbl_diag.setText(build_diagnostics_text(summary, selector))
        except Exception as e:
            self.lbl_diag.setText(f"진단 조회 실패: {e}")

    def _refresh_presets(self):
        presets_tab.refresh_presets(self)

    def _delete_preset(self):
        presets_tab.delete_selected_preset(self)

    def _export_all_settings(self):
        data_tab.export_all_settings(self)

    def _import_all_settings(self):
        data_tab.import_all_settings(self)

    def _import_excel(self):
        data_tab.import_excel(self)

    def _export_excel(self):
        data_tab.export_excel(self)
