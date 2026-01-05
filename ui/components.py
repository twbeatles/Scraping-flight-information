
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

# --- Custom Widgets (Scroll Wheel Disabled) ---

class NoWheelSpinBox(QSpinBox):
    """스크롤 휠에 반응하지 않는 SpinBox"""
    def wheelEvent(self, event):
        event.ignore()

class NoWheelComboBox(QComboBox):
    """스크롤 휠에 반응하지 않는 ComboBox"""
    def wheelEvent(self, event):
        event.ignore()

class NoWheelDateEdit(QDateEdit):
    """스크롤 휠에 반응하지 않는 DateEdit"""
    def wheelEvent(self, event):
        event.ignore()

class NoWheelTabWidget(QTabWidget):
    """스크롤 휠에 반응하지 않는 TabWidget"""
    def wheelEvent(self, event):
        event.ignore()


class FilterPanel(QFrame):
    filter_changed = pyqtSignal(dict)  # {direct_only, include_layover, airline_category, max_stops}

    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        layout.addWidget(QLabel("필터:"))
        
        # Direct flights only
        self.chk_direct = QCheckBox("직항만")
        self.chk_direct.setToolTip("경유 없이 직항 노선만 표시합니다")
        self.chk_direct.stateChanged.connect(self._emit_filter)
        layout.addWidget(self.chk_direct)
        
        # Include layovers
        self.chk_layover = QCheckBox("경유 포함")
        self.chk_layover.setToolTip("경유 노선도 함께 표시합니다")
        self.chk_layover.setChecked(True)
        self.chk_layover.stateChanged.connect(self._emit_filter)
        layout.addWidget(self.chk_layover)
        
        layout.addWidget(self._create_separator())
        
        # Airline Category Filter
        layout.addWidget(QLabel("항공사:"))
        self.cb_airline_category = NoWheelComboBox()
        self.cb_airline_category.setToolTip("LCC: 저비용항공사 (제주항공, 진에어 등)\nFSC: 일반항공사 (대한항공, 아시아나)")
        self.cb_airline_category.addItem("전체", "ALL")
        self.cb_airline_category.addItem("🏷️ LCC (저비용)", "LCC")
        self.cb_airline_category.addItem("✈️ FSC (일반)", "FSC")
        self.cb_airline_category.setMinimumWidth(130)
        self.cb_airline_category.currentIndexChanged.connect(self._emit_filter)
        layout.addWidget(self.cb_airline_category)
        
        layout.addWidget(self._create_separator())
        
        # Styles for better visibility
        label_style = "font-weight: bold; color: #e0e0e0; font-size: 13px;"
        spin_style = """
            QSpinBox {
                min-width: 70px;
                min-height: 28px;
                font-size: 13px;
                padding: 2px;
                font-weight: bold;
            }
        """
        self.setStyleSheet(spin_style)

        # Time Filter (Outbound)
        lbl_out = QLabel("가는편:")
        lbl_out.setStyleSheet(label_style)
        layout.addWidget(lbl_out)
        
        self.spin_start_time = NoWheelSpinBox()
        self.spin_start_time.setRange(0, 23)
        self.spin_start_time.setSuffix("시")
        self.spin_start_time.valueChanged.connect(self._on_time_changed)
        
        layout.addWidget(self.spin_start_time)
        layout.addWidget(QLabel("~"))
        
        self.spin_end_time = NoWheelSpinBox()
        self.spin_end_time.setRange(1, 24)
        self.spin_end_time.setValue(24)
        self.spin_end_time.setSuffix("시")
        self.spin_end_time.valueChanged.connect(self._on_time_changed)
        layout.addWidget(self.spin_end_time)
        
        layout.addWidget(self._create_separator())
        
        # Time Filter (Inbound)
        lbl_in = QLabel("오는편:")
        lbl_in.setStyleSheet(label_style)
        layout.addWidget(lbl_in)
        
        self.spin_ret_start = NoWheelSpinBox()
        self.spin_ret_start.setRange(0, 23)
        self.spin_ret_start.setSuffix("시")
        self.spin_ret_start.valueChanged.connect(self._on_time_changed)
        layout.addWidget(self.spin_ret_start)
        
        layout.addWidget(QLabel("~"))
        
        self.spin_ret_end = NoWheelSpinBox()
        self.spin_ret_end.setRange(1, 24)
        self.spin_ret_end.setValue(24)
        self.spin_ret_end.setSuffix("시")
        self.spin_ret_end.valueChanged.connect(self._on_time_changed)
        layout.addWidget(self.spin_ret_end)
        
        layout.addWidget(self._create_separator())
        
        # Max Stops Filter
        layout.addWidget(QLabel("경유:"))
        self.spin_max_stops = NoWheelSpinBox()
        self.spin_max_stops.setRange(0, 5)
        self.spin_max_stops.setValue(3)
        self.spin_max_stops.setSuffix("회")
        self.spin_max_stops.setFixedWidth(50)
        self.spin_max_stops.setToolTip("허용할 최대 경유 횟수")
        self.spin_max_stops.valueChanged.connect(self._emit_filter)
        layout.addWidget(self.spin_max_stops)
        
        layout.addWidget(self._create_separator())
        
        # Price Range Filter (Advanced)
        layout.addWidget(QLabel("가격:"))
        self.spin_min_price = NoWheelSpinBox()
        self.spin_min_price.setRange(0, 9999)
        self.spin_min_price.setValue(0)
        self.spin_min_price.setSuffix("만")
        self.spin_min_price.setFixedWidth(65)
        self.spin_min_price.setToolTip("최소 가격 (만원 단위)")
        self.spin_min_price.valueChanged.connect(self._emit_filter)
        layout.addWidget(self.spin_min_price)
        
        layout.addWidget(QLabel("~"))
        
        self.spin_max_price = NoWheelSpinBox()
        self.spin_max_price.setRange(0, 9999)
        self.spin_max_price.setValue(9999)
        self.spin_max_price.setSuffix("만")
        self.spin_max_price.setFixedWidth(65)
        self.spin_max_price.setToolTip("최대 가격 (만원 단위, 9999=무제한)")
        self.spin_max_price.valueChanged.connect(self._emit_filter)
        layout.addWidget(self.spin_max_price)
        
        layout.addStretch()
        
        # Reset Button
        btn_reset = QPushButton("↺")
        btn_reset.setToolTip("필터 초기화")
        btn_reset.setObjectName("tool_btn")
        btn_reset.setFixedWidth(30)
        btn_reset.clicked.connect(self._reset_filters)
        layout.addWidget(btn_reset)
    
    def _create_separator(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #30475e;")
        return sep
    
    def _on_time_changed(self):
        """시간 변경 시 유효성 검사 후 시그널 발생"""
        # 가는편
        start = self.spin_start_time.value()
        end = self.spin_end_time.value()
        if start >= end:
            if self.sender() == self.spin_start_time:
                self.spin_end_time.setValue(start + 1)
            else:
                self.spin_start_time.setValue(end - 1)
        
        # 오는편
        r_start = self.spin_ret_start.value()
        r_end = self.spin_ret_end.value()
        if r_start >= r_end:
            if self.sender() == self.spin_ret_start:
                self.spin_ret_end.setValue(r_start + 1)
            else:
                self.spin_ret_start.setValue(r_end - 1)
                
        self._emit_filter()

    def _emit_filter(self):
        filters = self.get_current_filters()
        self.filter_changed.emit(filters)

    def _reset_filters(self):
        self.chk_direct.setChecked(False)
        self.chk_layover.setChecked(True)
        self.cb_airline_category.setCurrentIndex(0)  # ALL
        self.spin_max_stops.setValue(3)
        self.spin_start_time.setValue(0)
        self.spin_end_time.setValue(24)
        self.spin_ret_start.setValue(0)
        self.spin_ret_end.setValue(24)
        self.spin_min_price.setValue(0)
        self.spin_max_price.setValue(9999)

    def get_current_filters(self):
        return {
            "direct_only": self.chk_direct.isChecked(),
            "include_layover": self.chk_layover.isChecked(),
            "airline_category": self.cb_airline_category.currentData(),
            "max_stops": self.spin_max_stops.value(),
            "start_time": self.spin_start_time.value(),
            "end_time": self.spin_end_time.value(),
            "ret_start_time": self.spin_ret_start.value(),
            "ret_end_time": self.spin_ret_end.value(),
            "min_price": self.spin_min_price.value() * 10000,  # 만원 -> 원
            "max_price": self.spin_max_price.value() * 10000   # 만원 -> 원
        }


class ResultTable(QTableWidget):
    favorite_requested = pyqtSignal(int)  # row index
    
    def __init__(self):
        super().__init__()
        self.results_data = []  # Store flight results for access
        
        self.setColumnCount(9)
        self.setHorizontalHeaderLabels([
            "항공사", "가격", "가는편 출발", "가는편 도착", "경유",
            "오는편 출발", "오는편 도착", "경유", "출처"
        ])
        # 열 너비 조절 가능하도록 Interactive 모드 + 기본 너비 설정
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setStretchLastSection(True)
        # 기본 열 너비 설정
        self.setColumnWidth(0, 100)  # 항공사
        self.setColumnWidth(1, 180)  # 가격 (분리 표시용 넓게)
        self.setColumnWidth(2, 80)   # 가는편 출발
        self.setColumnWidth(3, 80)   # 가는편 도착
        self.setColumnWidth(4, 70)   # 경유
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        
        # Enable context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def update_data(self, results):
        # 대량 업데이트 최적화
        self.setUpdatesEnabled(False)
        self.setSortingEnabled(False)
        self.results_data = results
        self.setRowCount(len(results))
        
        # Calculate price range for color coding
        if results:
            min_price = min(r.price for r in results)
            max_price = max(r.price for r in results)
            price_range = max_price - min_price if max_price > min_price else 1
        
        for i, flight in enumerate(results):
            # Store flight object in first column's data
            airline_str = flight.airline
            if hasattr(flight, 'return_airline') and flight.return_airline and flight.airline != flight.return_airline:
                airline_str = f"{flight.airline} + {flight.return_airline}"
            
            airline_item = QTableWidgetItem(airline_str)
            airline_item.setData(Qt.ItemDataRole.UserRole + 1, i)
            # 툴팁에 상세 정보 표시
            if hasattr(flight, 'return_airline') and flight.return_airline:
                 airline_item.setToolTip(f"가는편: {flight.airline}\\n오는편: {flight.return_airline}")
            self.setItem(i, 0, airline_item)
            
            # Price (Color-coded: green=cheap, red=expensive)
            # 국내선: 가는편/오는편 가격 분리 표시
            if hasattr(flight, 'outbound_price') and flight.outbound_price > 0:
                price_text = f"{flight.price:,}원 ({flight.outbound_price:,}+{flight.return_price:,})"
            else:
                price_text = f"{flight.price:,}원"
            
            price_item = QTableWidgetItem(price_text)
            price_item.setData(Qt.ItemDataRole.UserRole, flight.price)
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            # Color coding based on price position
            ratio = (flight.price - min_price) / price_range if price_range else 0
            if ratio < 0.2:
                price_color = "#22c55e"  # Green - cheapest
            elif ratio < 0.5:
                price_color = "#4cc9f0"  # Cyan - good
            elif ratio < 0.8:
                price_color = "#f59e0b"  # Orange - moderate
            else:
                price_color = "#ef4444"  # Red - expensive
            
            price_item.setForeground(QColor(price_color))
            price_item.setFont(QFont("Pretendard", 11, QFont.Weight.Bold))
            self.setItem(i, 1, price_item)
            
            # Outbound
            self._set_time_item(i, 2, flight.departure_time)
            self._set_time_item(i, 3, flight.arrival_time)
            
            # Stops - highlight direct flights
            stops_item = QTableWidgetItem("✈️ 직항" if not flight.stops else f"{flight.stops}회 경유")
            if not flight.stops:
                stops_item.setForeground(QColor("#22c55e"))
            else:
                stops_item.setForeground(QColor("#94a3b8"))
            self.setItem(i, 4, stops_item)
            
            # Inbound
            if hasattr(flight, 'is_round_trip') and flight.is_round_trip:
                self._set_time_item(i, 5, flight.return_departure_time)
                self._set_time_item(i, 6, flight.return_arrival_time)
                ret_stops = QTableWidgetItem("✈️ 직항" if not flight.return_stops else f"{flight.return_stops}회 경유")
                if not flight.return_stops:
                    ret_stops.setForeground(QColor("#22c55e"))
                self.setItem(i, 7, ret_stops)
            else:
                self.setItem(i, 5, QTableWidgetItem("-"))
                self.setItem(i, 6, QTableWidgetItem("-"))
                self.setItem(i, 7, QTableWidgetItem("-"))
                
            # Source
            self.setItem(i, 8, QTableWidgetItem(flight.source))
            
            # Set row height
            self.setRowHeight(i, 45)
            
            # 최저가 행 배경색 강조
            if flight.price == min_price:
                highlight_color = QColor("#22c55e20")  # 녹색 반투명
                for col in range(self.columnCount()):
                    item = self.item(i, col)
                    if item:
                        item.setBackground(highlight_color)
            
        self.setSortingEnabled(True)
        self.setUpdatesEnabled(True)  # 렌더링 다시 활성화


    def _set_time_item(self, row, col, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row, col, item)
    
    def _show_context_menu(self, pos):
        row = self.rowAt(pos.y())
        if row < 0:
            return
        
        menu = QMenu(self)
        
        # Add to favorites
        action_fav = menu.addAction("⭐ 즐겨찾기 추가")
        action_fav.triggered.connect(lambda: self.favorite_requested.emit(row))
        
        menu.addSeparator()
        
        # Copy info
        action_copy = menu.addAction("📋 정보 복사")
        action_copy.triggered.connect(lambda: self._copy_row_info(row))
        
        menu.addSeparator()
        
        # Export options (전체 결과)
        action_excel = menu.addAction("📊 Excel로 내보내기")
        action_excel.triggered.connect(self.export_to_excel)
        
        action_csv = menu.addAction("📥 CSV로 내보내기")
        action_csv.triggered.connect(self.export_to_csv)
        
        menu.exec(self.mapToGlobal(pos))
    
    def _copy_row_info(self, row):
        if row >= len(self.results_data):
            return
        flight = self.results_data[row]
        info = f"{flight.airline} | {flight.price:,}원 | {flight.departure_time}→{flight.arrival_time}"
        QApplication.clipboard().setText(info)
    
    def export_to_excel(self):
        """검색 결과를 Excel 파일로 내보내기"""
        if not self.results_data:
            QMessageBox.warning(self, "경고", "내보낼 데이터가 없습니다.")
            return
        
        if not HAS_OPENPYXL:
            QMessageBox.warning(self, "경고", "openpyxl이 설치되지 않았습니다.\\npip install openpyxl")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Excel로 저장", 
            f"flight_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if not filename:
            return
        
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "검색 결과"
            
            # 헤더
            headers = ["항공사", "오는편 항공사", "가격", "가는편 출발", "가는편 도착", "경유",
                       "오는편 출발", "오는편 도착", "경유", "출처", "가는편 가격", "오는편 가격"]
            ws.append(headers)
            
            # 데이터
            for flight in self.results_data:
                row = [
                    flight.airline,
                    getattr(flight, 'return_airline', ''),
                    flight.price,
                    flight.departure_time,
                    flight.arrival_time,
                    flight.stops,
                    getattr(flight, 'return_departure_time', ''),
                    getattr(flight, 'return_arrival_time', ''),
                    getattr(flight, 'return_stops', 0),
                    flight.source,
                    getattr(flight, 'outbound_price', 0),
                    getattr(flight, 'return_price', 0)
                ]
                ws.append(row)
            
            # 열 너비 자동 조절
            for col in ws.columns:
                max_length = max(len(str(cell.value or '')) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = max_length + 2
            
            wb.save(filename)
            QMessageBox.information(self, "완료", f"Excel 파일이 저장되었습니다:\\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"저장 실패: {e}")
    
    def export_to_csv(self):
        """검색 결과를 CSV 파일로 내보내기"""
        if not self.results_data:
            QMessageBox.warning(self, "경고", "내보낼 데이터가 없습니다.")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "CSV로 저장",
            f"flight_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["항공사", "오는편 항공사", "가격", "가는편 출발", "가는편 도착", "경유",
                               "오는편 출발", "오는편 도착", "경유", "출처", "가는편 가격", "오는편 가격"])
                for flight in self.results_data:
                    writer.writerow([
                        flight.airline,
                        getattr(flight, 'return_airline', ''),
                        flight.price,
                        flight.departure_time,
                        flight.arrival_time,
                        flight.stops,
                        getattr(flight, 'return_departure_time', ''),
                        getattr(flight, 'return_arrival_time', ''),
                        getattr(flight, 'return_stops', 0),
                        flight.source,
                        getattr(flight, 'outbound_price', 0),
                        getattr(flight, 'return_price', 0)
                    ])
            QMessageBox.information(self, "완료", f"CSV 파일이 저장되었습니다:\\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"저장 실패: {e}")
    
    def get_flight_at_row(self, row):
        """Get flight data for the given visual row"""
        if 0 <= row < len(self.results_data):
            # Account for sorting - get original index from item data
            item = self.item(row, 0)
            if item:
                orig_idx = item.data(Qt.ItemDataRole.UserRole + 1)
                if orig_idx is not None and 0 <= orig_idx < len(self.results_data):
                    return self.results_data[orig_idx]
        return None


class LogViewer(QTextEdit):
    """실시간 로그 뷰어"""
    def __init__(self):
        super().__init__()
        self.setObjectName("log_view")
        self.setReadOnly(True)
        self.setPlaceholderText("검색 로그가 여기에 표시됩니다...")
    
    @pyqtSlot(str)
    def append_log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.append(f"[{timestamp}] {msg}")
        self.moveCursor(self.textCursor().MoveOperation.End)


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
        self.btn_search.setFixedHeight(50)
        self.btn_search.setToolTip("Ctrl+Enter로도 검색할 수 있습니다")
        self.btn_search.setStyleSheet("""
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4361ee, stop:1 #4cc9f0);
                font-size: 16px; border-radius: 8px; font-weight: bold;
            }
            QPushButton:hover { background: #3b82f6; }
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
        
        origin_code = self.cb_origin.currentData() or self.cb_origin.currentText().split(' ')[0].strip()
        dest_code = self.cb_dest.currentData() or self.cb_dest.currentText().split(' ')[0].strip()
        
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
            domestic_airports = {
                "GMP": "김포",
                "CJU": "제주",
                "PUS": "부산 김해",
                "TAE": "대구",
                "ICN": "인천"
            }
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
            
            # 커스텀 프리셋도 도착지에 추가
            try:
                presets = self.prefs.get_all_presets()
                for code, name in presets.items():
                    if code not in config.AIRPORTS:
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
                "adults": self.spin_adults.value()
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
            
        except Exception as e:
            QMessageBox.warning(self, "오류", f"프로필 로드 중 오류: {e}")

    def _open_settings(self):
        from ui.dialogs import SettingsDialog
        dlg = SettingsDialog(self, self.prefs)
        dlg.exec()
        # Refresh UI after settings close (presets might have changed)
        self._refresh_combos()
        self._refresh_profiles()
    
    def save_settings(self):
        """입력값을 QSettings에 저장 (프로그램 종료 시 호출)"""
        settings = QSettings("FlightBot", "FlightComparisonBot")
        settings.setValue("origin", self.cb_origin.currentText())
        settings.setValue("dest", self.cb_dest.currentText())
        settings.setValue("dep_date", self.date_dep.date().toString("yyyyMMdd"))
        if hasattr(self, 'date_ret') and self.date_ret.isEnabled():
            settings.setValue("ret_date", self.date_ret.date().toString("yyyyMMdd"))
        settings.setValue("adults", self.spin_adults.value())
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
