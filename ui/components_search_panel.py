"""
Custom UI Components for Flight Bot
"""
import sys
import csv
import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QPushButton, QCheckBox,
    QSpinBox, QComboBox, QDateEdit, QTabWidget, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMenu, QMessageBox, QFileDialog, QApplication, QTextEdit,
    QRadioButton, QButtonGroup, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QDate, QSettings
from PyQt6.QtGui import QColor, QFont, QTextCharFormat

# Try importing openpyxl
try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

import config

logger = logging.getLogger(__name__)

from ui.components_primitives import NoWheelSpinBox, NoWheelComboBox, NoWheelDateEdit

class SearchPanel(QFrame):
    search_requested = pyqtSignal(str, str, str, str, int, str)  # origin, dest, dep, ret, adults, cabin_class

    def __init__(self, prefs):
        super().__init__()
        self.prefs = prefs
        self.setObjectName("card")
        self._init_ui()

    def _init_ui(self):
        # Use GridLayout for better alignment
        layout = QGridLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # --- Row 0: Header & Controls ---
        head_layout = QHBoxLayout()
        
        # Trip Type
        self.rb_round = QRadioButton("왕복")
        self.rb_oneway = QRadioButton("편도")
        self.rb_round.setChecked(True)
        self.rb_group = QButtonGroup()
        self.rb_group.addButton(self.rb_round)
        self.rb_group.addButton(self.rb_oneway)
        self.rb_group.buttonClicked.connect(self._toggle_return_date)
        
        head_layout.addWidget(QLabel("여정:"))
        head_layout.addWidget(self.rb_round)
        head_layout.addWidget(self.rb_oneway)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #30475e; margin: 0 10px;")
        head_layout.addWidget(sep)
        
        # Flight Type (Domestic/International)
        self.rb_domestic = QRadioButton("🇰🇷 국내선")
        self.rb_intl = QRadioButton("✈️ 국제선")
        self.rb_intl.setChecked(True)  # 기본값: 국제선
        self.flight_type_group = QButtonGroup()
        self.flight_type_group.addButton(self.rb_domestic)
        self.flight_type_group.addButton(self.rb_intl)
        self.flight_type_group.buttonClicked.connect(self._on_flight_type_changed)
        
        head_layout.addWidget(QLabel("노선:"))
        head_layout.addWidget(self.rb_domestic)
        head_layout.addWidget(self.rb_intl)
        
        head_layout.addStretch()

        
        # Profile Controls (Aligned Right)
        self.cb_profiles = NoWheelComboBox()
        self.cb_profiles.setPlaceholderText("프로필 선택")
        self.cb_profiles.setMinimumWidth(150)
        self.cb_profiles.currentIndexChanged.connect(self._load_selected_profile)
        self._refresh_profiles()
        
        btn_save_profile = QPushButton("💾 저장")
        btn_save_profile.setToolTip("현재 검색 조건 프로필로 저장")
        btn_save_profile.setObjectName("tool_btn")
        btn_save_profile.clicked.connect(self._save_current_profile)
        
        btn_settings = QPushButton("⚙️ 설정")
        btn_settings.setToolTip("설정 메뉴 열기")
        btn_settings.setObjectName("tool_btn")
        btn_settings.clicked.connect(self._open_settings)
        
        head_layout.addWidget(self.cb_profiles)
        head_layout.addWidget(btn_save_profile)
        head_layout.addWidget(btn_settings)
        
        layout.addLayout(head_layout, 0, 0, 1, 3)
        
        # --- Row 1: Origin & Destination ---
        # Origin
        self.cb_origin = self._create_airport_combo(include_presets=True)
        btn_preset_origin = QPushButton("➕")
        btn_preset_origin.setToolTip("직접 공항 코드 추가/관리")
        btn_preset_origin.setObjectName("tool_btn")
        btn_preset_origin.setFixedWidth(40)
        btn_preset_origin.clicked.connect(lambda: self._manage_preset(self.cb_origin))
        
        origin_layout = QHBoxLayout()
        origin_layout.setContentsMargins(0,0,0,0)
        origin_layout.setSpacing(5)
        origin_layout.addWidget(self.cb_origin)
        origin_layout.addWidget(btn_preset_origin)
        origin_container = QWidget()
        origin_container.setLayout(origin_layout)
        
        layout.addWidget(self._labeled_widget("출발지 (Origin)", origin_container), 1, 0)
        
        # Arrow
        arrow_lbl = QLabel("✈️")
        arrow_lbl.setStyleSheet("font-size: 18px; color: #4cc9f0;")
        arrow_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(arrow_lbl, 1, 1)
        
        # Destination
        self.cb_dest = self._create_airport_combo("NRT", include_presets=True)
        btn_preset_dest = QPushButton("➕")
        btn_preset_dest.setToolTip("직접 공항 코드 추가/관리")
        btn_preset_dest.setObjectName("tool_btn")
        btn_preset_dest.setFixedWidth(40)
        btn_preset_dest.clicked.connect(lambda: self._manage_preset(self.cb_dest))
        
        dest_layout = QHBoxLayout()
        dest_layout.setContentsMargins(0,0,0,0)
        dest_layout.setSpacing(5)
        dest_layout.addWidget(self.cb_dest)
        dest_layout.addWidget(btn_preset_dest)
        dest_container = QWidget()
        dest_container.setLayout(dest_layout)
        
        layout.addWidget(self._labeled_widget("도착지 (Destination)", dest_container), 1, 2)
        
        # --- Row 2: Dates ---
        self.date_dep = NoWheelDateEdit()
        self.date_dep.setCalendarPopup(True)
        self.date_dep.setDisplayFormat("yyyy-MM-dd")
        self.date_dep.setDate(QDate.currentDate().addDays(7))
        layout.addWidget(self._labeled_widget("가는 날 (Departure)", self.date_dep), 2, 0)
        
        self.date_ret = NoWheelDateEdit()
        self.date_ret.setCalendarPopup(True)
        self.date_ret.setDisplayFormat("yyyy-MM-dd")
        self.date_ret.setDate(QDate.currentDate().addDays(10))
        layout.addWidget(self._labeled_widget("오는 날 (Return)", self.date_ret), 2, 2)

        # --- Row 3: Passengers, Cabin Class & Time ---
        # Passengers
        self.spin_adults = NoWheelSpinBox()
        self.spin_adults.setRange(1, 9)
        self.spin_adults.setSuffix("명")
        layout.addWidget(self._labeled_widget("성인 (Adults)", self.spin_adults), 3, 0)
        
        # Cabin Class (좌석등급)
        self.cb_cabin_class = NoWheelComboBox()
        self.cb_cabin_class.addItem("💺 이코노미", "ECONOMY")
        self.cb_cabin_class.addItem("💼 비즈니스", "BUSINESS")
        self.cb_cabin_class.addItem("👑 일등석", "FIRST")
        self.cb_cabin_class.setToolTip("좌석 등급을 선택하세요 (가격이 다릅니다)")
        
        # Time Range
        time_layout = QHBoxLayout()
        self.spin_time_start = NoWheelSpinBox()
        self.spin_time_start.setRange(0, 23)
        self.spin_time_start.setSuffix("시")
        
        self.spin_time_end = NoWheelSpinBox()
        self.spin_time_end.setRange(1, 24)
        self.spin_time_end.setValue(24)
        self.spin_time_end.setSuffix("시")
        
        time_layout.addWidget(self.cb_cabin_class)
        time_layout.addWidget(QLabel("|"))
        time_layout.addWidget(self.spin_time_start)
        time_layout.addWidget(QLabel("~"))
        time_layout.addWidget(self.spin_time_end)
        time_container = QWidget()
        time_container.setLayout(time_layout)
        
        layout.addWidget(self._labeled_widget("좌석등급 / 선호시간", time_container), 3, 2)

        # --- Row 4: Search Button ---
        self.btn_search = QPushButton("🔍 최저가 항공권 검색하기")
        self.btn_search.setFixedHeight(54)
        self.btn_search.setToolTip("Ctrl+Enter로도 검색할 수 있습니다")
        self.btn_search.setStyleSheet("""
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #667eea, stop:0.5 #764ba2, stop:1 #22d3ee);
                font-size: 16px; 
                border-radius: 14px; 
                font-weight: 700;
                letter-spacing: 0.5px;
                border: none;
            }
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #818cf8, stop:0.5 #a78bfa, stop:1 #67e8f9);
                border: 2px solid rgba(99, 102, 241, 0.4);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #4f46e5, stop:0.5 #6d28d9, stop:1 #0891b2);
            }
        """)
        self.btn_search.clicked.connect(self._on_search)
        layout.addWidget(self.btn_search, 4, 0, 1, 3) 
        
        # Load previous preferred time if any
        pt = self.prefs.get_preferred_time()
        self.spin_time_start.setValue(pt.get("departure_start", 0))
        self.spin_time_end.setValue(pt.get("departure_end", 24))

        # Column stretch
        layout.setColumnStretch(0, 10)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 10)
        layout.setColumnMinimumWidth(1, 30)

    def _create_airport_combo(self, default_code="ICN", include_presets=False):
        cb = QComboBox()
        cb.setEditable(True) 
        
        # Standard Airports
        for code, name in config.AIRPORTS.items():
            cb.addItem(f"{code} ({name})", code)
            
        # Custom Presets
        if include_presets:
            try:
                presets = self.prefs.get_all_presets()
                # cb.clear()  <-- Don't clear, append. But avoid duplicates.
                # Already added standard airports above.
                for code, name in presets.items():
                     if code not in config.AIRPORTS:
                        cb.addItem(f"{code} ({name})", code)
            except Exception as e:
                logger.warning(f"Failed to load presets: {e}")

        index = cb.findData(default_code)
        if index >= 0:
            cb.setCurrentIndex(index)
        return cb

    def _labeled_widget(self, label_text, widget):
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        vbox.addWidget(lbl)
        vbox.addWidget(widget)
        return container

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
        ret = ret_date.toString("yyyyMMdd") if ret_date else None
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
        
        if ret_date and ret_date < dep_date:
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

        
    def _refresh_profiles(self):
        self.cb_profiles.blockSignals(True)
        self.cb_profiles.clear()
        self.cb_profiles.addItem("- 프로필 선택 -", None)
        profiles = self.prefs.get_all_profiles()
        for name in profiles.keys():
            self.cb_profiles.addItem(name, name)
        self.cb_profiles.blockSignals(False)

    def _save_current_profile(self):
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

    def _load_selected_profile(self):
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

    def _open_settings(self):
        from ui.dialogs import SettingsDialog
        top = self.window()
        dlg = SettingsDialog(self, self.prefs, getattr(top, "db", None))
        dlg.exec()
        # Refresh UI after settings close (presets might have changed)
        self._refresh_combos()
        self._refresh_profiles()
        if hasattr(top, "_configure_alert_auto_timer"):
            top._configure_alert_auto_timer()
    
    def save_settings(self):
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
    
    def restore_settings(self):
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
