"""Settings dialog general tab (SRP: general-tab assembly only)."""

from typing import Any

from PyQt6.QtWidgets import (
    QCheckBox, QGroupBox, QHBoxLayout, QLabel, QPushButton, QSpinBox,
    QVBoxLayout, QWidget,
)


def build_general_tab(dialog: Any) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)

    # Preferred Time
    grp_time = QGroupBox("기본 선호 시간대")
    gt_layout = QHBoxLayout(grp_time)

    dialog.spin_start = QSpinBox()
    dialog.spin_start.setRange(0, 23)
    dialog.spin_end = QSpinBox()
    dialog.spin_end.setRange(1, 24)

    pt = dialog.prefs.get_preferred_time()
    dialog.spin_start.setValue(pt.get("departure_start", 0))
    dialog.spin_end.setValue(pt.get("departure_end", 24))

    gt_layout.addWidget(QLabel("출발:"))
    gt_layout.addWidget(dialog.spin_start)
    gt_layout.addWidget(QLabel("~"))
    gt_layout.addWidget(dialog.spin_end)
    gt_layout.addWidget(QLabel("시"))

    # Max Results
    grp_limit = QGroupBox("검색 결과 제한")
    gl_layout = QHBoxLayout(grp_limit)

    dialog.spin_limit = QSpinBox()
    dialog.spin_limit.setRange(50, 2000)
    dialog.spin_limit.setSingleStep(50)
    dialog.spin_limit.setValue(dialog.prefs.get_max_results())
    dialog.spin_limit.setSuffix(" 개")
    dialog.spin_limit.setToolTip("한 번의 검색에서 표시할 최대 결과 수 (기본: 1000)")

    gl_layout.addWidget(QLabel("최대 표시 개수:"))
    gl_layout.addWidget(dialog.spin_limit)
    gl_layout.addStretch()

    # Save Button (Combined)
    btn_save_time = QPushButton("설정 저장")
    btn_save_time.setFixedWidth(100)  # Increased width for visibility
    btn_save_time.setFixedHeight(30)
    btn_save_time.clicked.connect(dialog._save_time_pref)

    gt_layout.addWidget(btn_save_time)

    layout.addWidget(grp_time)
    layout.addWidget(grp_limit)

    # Alert auto-check settings
    grp_alert = QGroupBox("🔔 자동 가격 알림 점검")
    ga_layout = QVBoxLayout(grp_alert)
    row_alert = QHBoxLayout()
    dialog.chk_alert_auto = QCheckBox("자동 점검 활성화")
    auto_cfg = dialog.prefs.get_alert_auto_check()
    dialog.chk_alert_auto.setChecked(auto_cfg.get("enabled", False))
    dialog.spin_alert_interval = QSpinBox()
    dialog.spin_alert_interval.setRange(5, 1440)
    dialog.spin_alert_interval.setValue(auto_cfg.get("interval_min", 30))
    dialog.spin_alert_interval.setSuffix(" 분")
    btn_save_alert = QPushButton("자동점검 저장")
    btn_save_alert.clicked.connect(dialog._save_alert_auto_check)
    btn_run_alert = QPushButton("지금 검사")
    btn_run_alert.clicked.connect(dialog._run_alert_auto_check_now)
    row_alert.addWidget(dialog.chk_alert_auto)
    row_alert.addWidget(QLabel("주기:"))
    row_alert.addWidget(dialog.spin_alert_interval)
    row_alert.addWidget(btn_save_alert)
    row_alert.addWidget(btn_run_alert)
    row_alert.addStretch()
    ga_layout.addLayout(row_alert)
    dialog.chk_alert_hit_modal = QCheckBox("알림 발동 시 모달 표시")
    dialog.chk_alert_hit_modal.setChecked(bool(auto_cfg.get("hit_modal_enabled", True)))
    dialog.chk_alert_hit_modal.setToolTip("끄면 로그/목록 상태만 갱신하고 팝업을 띄우지 않습니다.")
    ga_layout.addWidget(dialog.chk_alert_hit_modal)
    layout.addWidget(grp_alert)

    dialog.lbl_alert_auto_status = QLabel("")
    dialog.lbl_alert_auto_status.setWordWrap(True)
    dialog.lbl_alert_auto_status.setStyleSheet("font-size: 12px; color: #cbd5e1;")
    layout.addWidget(dialog.lbl_alert_auto_status)

    # Diagnostics
    grp_diag = QGroupBox("🩺 진단 (최근 24시간)")
    gd_layout = QVBoxLayout(grp_diag)
    dialog.lbl_diag = QLabel("진단 데이터를 불러오는 중...")
    dialog.lbl_diag.setWordWrap(True)
    dialog.lbl_diag.setStyleSheet("font-size: 12px; color: #cbd5e1;")
    btn_refresh_diag = QPushButton("진단 새로고침")
    btn_refresh_diag.clicked.connect(dialog._refresh_diagnostics)
    gd_layout.addWidget(dialog.lbl_diag)
    gd_layout.addWidget(btn_refresh_diag)
    layout.addWidget(grp_diag)

    dialog._refresh_diagnostics()
    dialog._refresh_alert_auto_status()
    layout.addStretch()
    return widget
