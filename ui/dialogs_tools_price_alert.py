"""Dialogs for Flight Bot"""
import sys
import logging
from datetime import datetime, timedelta
from typing import Any, cast
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QCalendarWidget, QGroupBox, QListWidget, QListWidgetItem, QFrame,
    QMessageBox, QDateEdit, QSpinBox, QCheckBox, QScrollArea, QGridLayout,
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QTabWidget, QFileDialog, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QSettings
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QAction

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    openpyxl = None
    HAS_OPENPYXL = False

import config
from ui.styles import MODERN_THEME
from ui.components_primitives import NoWheelSpinBox, NoWheelComboBox, NoWheelDateEdit
from ui.dialogs_base import _validate_route_and_dates

logger = logging.getLogger(__name__)
class PriceAlertDialog(QDialog):
    """가격 알림 설정 다이얼로그"""
    
    def __init__(self, parent=None, db=None, prefs=None):
        super().__init__(parent)
        self.db: Any = db
        self.prefs: Any = prefs
        self.setWindowTitle("🔔 가격 알림 관리")
        self.setMinimumSize(700, 550)
        self.setStyleSheet(MODERN_THEME)
        self._init_ui()
        self._refresh_alerts()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 설명
        info = QLabel("목표 가격을 설정하면 가격이 그 이하로 떨어질 때 알림을 받을 수 있습니다.")
        info.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(info)
        
        # 새 알림 추가 그룹
        grp_new = QGroupBox("➕ 새 알림 추가")
        new_layout = QGridLayout(grp_new)
        
        # 출발지
        new_layout.addWidget(QLabel("출발지:"), 0, 0)
        self.cb_origin = QComboBox()
        for code, name in config.AIRPORTS.items():
            self.cb_origin.addItem(f"{code} ({name})", code)
        new_layout.addWidget(self.cb_origin, 0, 1)
        
        # 도착지
        new_layout.addWidget(QLabel("도착지:"), 0, 2)
        self.cb_dest = QComboBox()
        all_presets = self.prefs.get_all_presets() if self.prefs else config.AIRPORTS
        for code, name in all_presets.items():
            self.cb_dest.addItem(f"{code} ({name})", code)
        self.cb_dest.setCurrentIndex(1)
        new_layout.addWidget(self.cb_dest, 0, 3)
        
        # 가는 날
        new_layout.addWidget(QLabel("가는 날:"), 1, 0)
        self.date_dep = QDateEdit()
        self.date_dep.setCalendarPopup(True)
        self.date_dep.setDate(QDate.currentDate().addDays(7))
        new_layout.addWidget(self.date_dep, 1, 1)
        
        # 오는 날
        new_layout.addWidget(QLabel("오는 날:"), 1, 2)
        self.date_ret = QDateEdit()
        self.date_ret.setCalendarPopup(True)
        self.date_ret.setDate(QDate.currentDate().addDays(10))
        new_layout.addWidget(self.date_ret, 1, 3)

        # 편도 알림
        self.chk_oneway = QCheckBox("편도 알림")
        self.chk_oneway.setToolTip("체크하면 귀국일 없이 편도 노선만 기준으로 알림을 설정합니다.")
        self.chk_oneway.toggled.connect(self._toggle_alert_oneway)
        new_layout.addWidget(self.chk_oneway, 2, 0, 1, 2)

        # 성인 수
        new_layout.addWidget(QLabel("성인:"), 2, 2)
        self.spin_adults = QSpinBox()
        self.spin_adults.setRange(1, 9)
        self.spin_adults.setValue(1)
        self.spin_adults.setSuffix(" 명")
        new_layout.addWidget(self.spin_adults, 2, 3)
        
        # 목표 가격
        new_layout.addWidget(QLabel("목표 가격:"), 3, 0)
        self.spin_target = QSpinBox()
        self.spin_target.setRange(10000, 10000000)
        self.spin_target.setSingleStep(10000)
        self.spin_target.setValue(300000)
        self.spin_target.setSuffix(" 원")
        new_layout.addWidget(self.spin_target, 3, 1)

        # 좌석 등급
        new_layout.addWidget(QLabel("좌석 등급:"), 3, 2)
        self.cb_cabin_class = QComboBox()
        self.cb_cabin_class.addItem("💺 이코노미", "ECONOMY")
        self.cb_cabin_class.addItem("💼 비즈니스", "BUSINESS")
        self.cb_cabin_class.addItem("👑 일등석", "FIRST")
        new_layout.addWidget(self.cb_cabin_class, 3, 3)
        
        # 추가 버튼
        btn_add = QPushButton("🔔 알림 추가")
        btn_add.clicked.connect(self._add_alert)
        new_layout.addWidget(btn_add, 4, 0, 1, 4)
        
        layout.addWidget(grp_new)
        
        # 현재 알림 목록
        alert_label = QLabel("📋 설정된 알림 목록:")
        alert_label.setObjectName("section_title")
        layout.addWidget(alert_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "노선", "출발일", "귀국일", "인원", "좌석", "목표가", "현재가", "상태"
        ])
        self.table.setColumnHidden(0, True)  # ID 숨김
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        
        # 버튼 영역
        btn_layout = QHBoxLayout()
        
        btn_refresh = QPushButton("🔄 새로고침")
        btn_refresh.clicked.connect(self._refresh_alerts)
        btn_layout.addWidget(btn_refresh)
        
        btn_delete = QPushButton("🗑️ 선택 삭제")
        btn_delete.clicked.connect(self._delete_selected)
        btn_layout.addWidget(btn_delete)
        
        btn_layout.addStretch()
        
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)

    def _toggle_alert_oneway(self, checked: bool):
        self.date_ret.setEnabled(not checked)
    
    def _add_alert(self):
        """새 알림 추가"""
        origin = self.cb_origin.currentData()
        dest = self.cb_dest.currentData()
        dep_date = self.date_dep.date()
        ret_date = None if self.chk_oneway.isChecked() else self.date_ret.date()
        target = self.spin_target.value()
        adults = self.spin_adults.value()
        cabin_class = self.cb_cabin_class.currentData() or "ECONOMY"

        if not _validate_route_and_dates(self, origin, dest, dep_date, ret_date):
            return

        dep = dep_date.toString("yyyyMMdd")
        ret = ret_date.toString("yyyyMMdd") if ret_date is not None else None

        try:
            alert_id = self.db.add_price_alert(origin, dest, dep, ret, target, cabin_class, adults)
            QMessageBox.information(self, "완료", f"가격 알림이 추가되었습니다. (ID: {alert_id})")
            self._refresh_alerts()
        except Exception as e:
            QMessageBox.critical(self, "오류", f"알림 추가 실패: {e}")
    
    def _refresh_alerts(self):
        """알림 목록 새로고침"""
        if not self.db:
            return
        
        alerts = self.db.get_all_alerts()
        self.table.setRowCount(len(alerts))
        
        for i, alert in enumerate(alerts):
            self.table.setItem(i, 0, QTableWidgetItem(str(alert.id)))
            
            route = f"{alert.origin} → {alert.destination}"
            self.table.setItem(i, 1, QTableWidgetItem(route))
            
            # 날짜 포맷
            try:
                dep_dt = datetime.strptime(alert.departure_date, "%Y%m%d")
                dep_str = dep_dt.strftime("%Y-%m-%d")
            except:
                dep_str = alert.departure_date
            self.table.setItem(i, 2, QTableWidgetItem(dep_str))
            
            if alert.return_date:
                try:
                    ret_dt = datetime.strptime(alert.return_date, "%Y%m%d")
                    ret_str = ret_dt.strftime("%Y-%m-%d")
                except:
                    ret_str = alert.return_date
            else:
                ret_str = "-"
            self.table.setItem(i, 3, QTableWidgetItem(ret_str))

            adults = int(getattr(alert, "adults", 1) or 1)
            self.table.setItem(i, 4, QTableWidgetItem(f"{adults}명"))

            cabin_class = getattr(alert, "cabin_class", "ECONOMY") or "ECONOMY"
            cabin_text = {"ECONOMY": "이코노미", "BUSINESS": "비즈니스", "FIRST": "일등석"}.get(cabin_class, cabin_class)
            self.table.setItem(i, 5, QTableWidgetItem(cabin_text))
            
            # 목표 가격
            target_item = QTableWidgetItem(f"{alert.target_price:,}원")
            target_item.setForeground(QColor("#4cc9f0"))
            self.table.setItem(i, 6, target_item)
            
            # 현재 가격
            if alert.last_price:
                current_item = QTableWidgetItem(f"{alert.last_price:,}원")
                if alert.last_price <= alert.target_price:
                    current_item.setForeground(QColor("#22c55e"))
                else:
                    current_item.setForeground(QColor("#f59e0b"))
            else:
                current_item = QTableWidgetItem("미확인")
            self.table.setItem(i, 7, current_item)
            
            # 상태
            if alert.triggered:
                status = "✅ 발동됨"
                color = "#22c55e"
            elif getattr(alert, "last_error", ""):
                status = "⚠️ 점검 실패"
                color = "#f59e0b"
            elif alert.is_active:
                status = "🔔 활성"
                color = "#4cc9f0"
            else:
                status = "⏸️ 비활성"
                color = "#94a3b8"
            
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor(color))
            last_error = getattr(alert, "last_error", "") or ""
            if last_error:
                status_item.setToolTip(last_error)
            self.table.setItem(i, 8, status_item)
    
    def _delete_selected(self):
        """선택된 알림 삭제"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "선택 오류", "삭제할 알림을 선택하세요.")
            return
        
        alert_id_item = self.table.item(row, 0)
        if alert_id_item is None:
            QMessageBox.warning(self, "선택 오류", "선택된 알림 정보를 읽을 수 없습니다.")
            return
        alert_id = int(alert_id_item.text())
        reply = QMessageBox.question(
            self, "삭제 확인",
            "선택한 알림을 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.db.delete_alert(alert_id):
                self._refresh_alerts()
            else:
                QMessageBox.critical(self, "오류", "알림 삭제에 실패했습니다.")
