"""
Flight Comparison Bot V2.5 - Modern GUI
Modular, card-based interface with dark theme and Playwright integration.
Enhanced with multi-destination search, date range search, airline filters,
favorites, price history, and improved UI/UX.
"""

import sys
import os
import time
import webbrowser

# HiDPI 지원 활성화 (Qt 초기화 전에 설정해야 함)
# os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
# os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

# Qt CSS 경고 억제 (Unknown property content 등)
os.environ["QT_LOGGING_RULES"] = "qt.qpa.css.warning=false"


from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QDateEdit, QSpinBox, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QProgressBar, QFrame, QRadioButton, QButtonGroup, QAbstractItemView,
    QSizePolicy, QTabWidget, QTextEdit, QListWidget, QListWidgetItem,
    QDialog, QFileDialog, QLineEdit, QGroupBox, QGridLayout,
    QCheckBox, QSlider, QMenu, QCalendarWidget, QScrollArea,
    QToolButton, QInputDialog
)
from PyQt6.QtCore import QDate, Qt, QThread, pyqtSignal, QSize, pyqtSlot, QTimer, QSettings
from PyQt6.QtGui import QFont, QColor, QIcon, QPalette, QShortcut, QKeySequence, QAction, QTextCharFormat
import json
import logging

# 로거 설정
logger = logging.getLogger(__name__)

from scraper_v2 import FlightSearcher, FlightResult
import config
import scraper_config
from database import FlightDatabase

# Try importing openpyxl
try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


# --- Styling ---
from ui.styles import DARK_THEME, LIGHT_THEME
from ui.components import (
    NoWheelSpinBox, NoWheelComboBox, NoWheelDateEdit, NoWheelTabWidget,
    FilterPanel, ResultTable, LogViewer, SearchPanel
)
from ui.workers import SearchWorker, MultiSearchWorker, DateRangeWorker
from ui.dialogs import (
    CalendarViewDialog, CombinationSelectorDialog, MultiDestDialog,
    MultiDestResultDialog, DateRangeDialog, DateRangeResultDialog,
    ShortcutsDialog, PriceAlertDialog, SettingsDialog
)

# 기본 테마 (호환성)
MODERN_THEME = DARK_THEME

# === 상수 정의 ===
MAX_PRICE_FILTER = 99_990_000  # 필터 최대값 (무제한 표시용)

class SessionManager:
    """세션 저장/복원 관리자"""
    
    @staticmethod
    def _safe_serialize(obj):
        """객체를 JSON 직렬화 가능한 형태로 안전하게 변환"""
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif hasattr(obj, '__dict__'):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
        else:
            # 기본 타입은 그대로 반환, 직렬화 불가능한 경우 문자열로 변환
            try:
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                return str(obj)
    
    @staticmethod
    def save_session(filepath: str, search_params: dict, results: list) -> bool:
        """세션을 JSON 파일로 저장 (직렬화 검증 포함)"""
        try:
            # 결과 데이터를 안전하게 직렬화
            serialized_results = []
            for r in results:
                try:
                    serialized = SessionManager._safe_serialize(r)
                    # 직렬화 가능 여부 사전 검증
                    json.dumps(serialized)
                    serialized_results.append(serialized)
                except (TypeError, ValueError) as e:
                    logger.warning(f"결과 직렬화 실패, 건너뜀: {e}")
                    continue
            
            session_data = {
                "saved_at": datetime.now().isoformat(),
                "search_params": search_params,
                "results": serialized_results
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logging.error(f"Session save error: {e}")
            return False
    
    @staticmethod
    def load_session(filepath: str) -> tuple:
        """저장된 세션 로드, (params, results, saved_at) 반환"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 결과를 FlightResult 객체로 변환
            from scraper_v2 import FlightResult
            results = []
            for r in data.get("results", []):
                flight = FlightResult(
                    airline=r.get("airline", "Unknown"),
                    price=r.get("price", 0),
                    currency=r.get("currency", "KRW"),
                    departure_time=r.get("departure_time", ""),
                    arrival_time=r.get("arrival_time", ""),
                    duration=r.get("duration", ""),
                    stops=r.get("stops", 0),
                    flight_number=r.get("flight_number", ""),
                    source=r.get("source", "Session"),
                    return_departure_time=r.get("return_departure_time", ""),
                    return_arrival_time=r.get("return_arrival_time", ""),
                    return_duration=r.get("return_duration", ""),
                    return_stops=r.get("return_stops", 0),
                    is_round_trip=r.get("is_round_trip", False),
                    outbound_price=r.get("outbound_price", 0),
                    return_price=r.get("return_price", 0),
                    return_airline=r.get("return_airline", "")
                )
                results.append(flight)
            
            return data.get("search_params", {}), results, data.get("saved_at", "")
        except Exception as e:
            logging.error(f"Session load error: {e}")
            return {}, [], ""


# --- Calendar View Dialog ---

# --- Main Window ---

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("✈️ Flight Bot v2.5 - Pro")
        self.setMinimumSize(1280, 900)
        
        # 테마 초기화 - 저장된 설정에서 로드
        self.prefs = config.PreferenceManager()
        saved_theme = self.prefs.get_theme()
        self.is_dark_theme = (saved_theme == "dark")
        self.setStyleSheet(DARK_THEME if self.is_dark_theme else LIGHT_THEME)
        
        self.worker = None
        self.multi_worker = None
        self.date_worker = None
        self.active_searcher = None
        self.results = []
        self.all_results = []
        self.current_search_params = {}
        self._cancelling = False  # 검색 취소 중복 방지 플래그
        self._pending_filter = None
        self._last_filter_log_msg = ""
        self._last_filter_log_ts = 0.0
        self._last_progress_msg = ""
        self._last_progress_ts = 0.0
        self._filter_apply_timer = QTimer(self)
        self._filter_apply_timer.setSingleShot(True)
        self._filter_apply_timer.timeout.connect(self._run_scheduled_filter_apply)
        
        # prefs는 이미 테마 로드 시 초기화됨
        self.db = FlightDatabase()
        self.db.cleanup_old_data(days=60)
        
        self._init_ui()
        if hasattr(self, 'search_panel'):
            self.search_panel.restore_settings()
        self._setup_shortcuts()
        
        # 프로그램 시작 시 마지막 검색 결과 복원
        QTimer.singleShot(0, self._restore_last_search)

    def _init_ui(self):
        # 전체 UI 스크롤 가능하도록 설정
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background: transparent; 
            }
            QScrollArea > QWidget > QWidget { 
                background: transparent; 
            }
        """)
        
        # 스크롤 내부 컨테이너
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        # HiDPI 환경에서 콘텐츠가 잘리지 않도록 최소 너비 설정
        container.setMinimumWidth(1200)
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(18)
        
        # 1. Header
        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 10)
        
        v_title = QVBoxLayout()
        title = QLabel("✈️ 항공권 최저가 검색기")
        title.setObjectName("title")
        subtitle = QLabel("Playwright 엔진 기반 실시간 항공권 비교 분석 v2.5")
        subtitle.setObjectName("subtitle")
        v_title.addWidget(title)
        v_title.addWidget(subtitle)
        
        h_layout.addLayout(v_title)
        h_layout.addStretch()
        
        # === 검색 버튼 그룹 ===
        btn_multi = QPushButton("🌍 다중 목적지")
        btn_multi.setToolTip("여러 목적지를 한 번에 비교 검색")
        btn_multi.clicked.connect(self._open_multi_dest_search)
        h_layout.addWidget(btn_multi)
        
        btn_date = QPushButton("📅 날짜 범위")
        btn_date.setToolTip("날짜 범위에서 최저가 찾기")
        btn_date.clicked.connect(self._open_date_range_search)
        h_layout.addWidget(btn_date)
        
        # 구분선 1
        sep1 = QFrame()
        sep1.setObjectName("v_separator")
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setFixedWidth(2)
        sep1.setFixedHeight(30)
        h_layout.addWidget(sep1)
        
        # === 뷰/알림 버튼 그룹 ===
        btn_calendar = QPushButton("📆 캘린더뷰")
        btn_calendar.setObjectName("secondary_btn")
        btn_calendar.setToolTip("날짜별 가격을 캘린더 형태로 보기 (날짜범위 검색 후 사용)")
        btn_calendar.clicked.connect(self._show_calendar_view)
        h_layout.addWidget(btn_calendar)
        
        btn_alert = QPushButton("🔔 가격알림")
        btn_alert.setObjectName("secondary_btn")
        btn_alert.setToolTip("목표 가격 설정 및 알림 관리")
        btn_alert.clicked.connect(self._open_price_alert_dialog)
        h_layout.addWidget(btn_alert)
        
        # 구분선 2
        sep2 = QFrame()
        sep2.setObjectName("v_separator")
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setFixedWidth(2)
        sep2.setFixedHeight(30)
        h_layout.addWidget(sep2)
        
        # === 세션/설정 버튼 그룹 ===
        btn_save_session = QPushButton("💾")
        btn_save_session.setObjectName("icon_btn")
        btn_save_session.setToolTip("현재 검색 결과를 파일로 저장")
        btn_save_session.clicked.connect(self._save_session)
        h_layout.addWidget(btn_save_session)
        
        btn_load_session = QPushButton("📂")
        btn_load_session.setObjectName("icon_btn")
        btn_load_session.setToolTip("저장된 검색 결과 불러오기")
        btn_load_session.clicked.connect(self._load_session)
        h_layout.addWidget(btn_load_session)
        
        btn_shortcuts = QPushButton("⌨️")
        btn_shortcuts.setObjectName("icon_btn")
        btn_shortcuts.setToolTip("키보드 단축키 보기")
        btn_shortcuts.clicked.connect(self._show_shortcuts)
        h_layout.addWidget(btn_shortcuts)
        
        # 테마 전환 버튼
        self.btn_theme = QPushButton("🌙" if self.is_dark_theme else "☀️")
        self.btn_theme.setObjectName("icon_btn")
        self.btn_theme.setToolTip("라이트/다크 테마 전환")
        self.btn_theme.clicked.connect(self._toggle_theme)
        h_layout.addWidget(self.btn_theme)
        
        # 설정 버튼
        btn_main_settings = QPushButton("⚙️ 설정")
        btn_main_settings.clicked.connect(self._open_main_settings)
        h_layout.addWidget(btn_main_settings)
        
        main_layout.addWidget(header)
        
        # 2. Search Panel (접기/펼치기)
        toggle_container = QWidget()
        toggle_layout = QHBoxLayout(toggle_container)
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_toggle_search = QPushButton("▼ 검색 설정")
        self.btn_toggle_search.setStyleSheet("""
            QPushButton { 
                background: rgba(34, 211, 238, 0.08); 
                color: #22d3ee; 
                font-weight: 600; 
                text-align: left; 
                padding: 10px 16px;
                border: 1px solid rgba(34, 211, 238, 0.15);
                border-radius: 10px;
                font-size: 14px;
            }
            QPushButton:hover { 
                background: rgba(34, 211, 238, 0.15);
                border: 1px solid rgba(34, 211, 238, 0.35);
                color: #67e8f9; 
            }
        """)
        self.btn_toggle_search.setCheckable(True)
        self.btn_toggle_search.setChecked(True)
        self.btn_toggle_search.clicked.connect(self._toggle_search_panel)
        toggle_layout.addWidget(self.btn_toggle_search)
        toggle_layout.addStretch()
        main_layout.addWidget(toggle_container)
        
        self.search_panel = SearchPanel(self.prefs)
        self.search_panel.search_requested.connect(self._start_search)
        main_layout.addWidget(self.search_panel)
        
        # 3. Filter Panel (별도 섹션)
        main_layout.addWidget(QLabel("필터", objectName="section_title"))
        self.filter_panel = FilterPanel()
        self.filter_panel.filter_changed.connect(self._schedule_filter_apply)
        main_layout.addWidget(self.filter_panel)
        
        # 4. Progress Bar (별도 섹션, 크게 표시 - Enhanced styling)
        main_layout.addWidget(QLabel("🔄 검색 상태", objectName="section_title"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat("✨ 준비됨")
        self.progress_bar.setMinimumHeight(48)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                font-size: 14px;
                font-weight: 700;
                text-align: center;
                border-radius: 14px;
                padding: 4px;
                background: rgba(15, 52, 96, 0.6);
                border: 1px solid rgba(34, 211, 238, 0.2);
                color: #e2e8f0;
            }
            QProgressBar::chunk {
                border-radius: 12px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #06b6d4, stop:0.4 #667eea, stop:0.7 #a855f7, stop:1 #ec4899);
            }
        """)
        main_layout.addWidget(self.progress_bar)
        
        # 5. Content Area (Tabs) with Export Buttons
        result_header = QWidget()
        rh_layout = QHBoxLayout(result_header)
        rh_layout.setContentsMargins(0, 0, 0, 0)
        rh_layout.addWidget(QLabel("검색 결과", objectName="section_title"))
        rh_layout.addStretch()
        
        # Export buttons
        btn_export_csv = QPushButton("📥 CSV 저장")
        btn_export_csv.setObjectName("tool_btn")
        btn_export_csv.setToolTip("검색 결과를 CSV 파일로 저장")
        btn_export_csv.clicked.connect(self._export_to_csv)
        rh_layout.addWidget(btn_export_csv)
        
        btn_copy = QPushButton("📋 복사")
        btn_copy.setObjectName("tool_btn")
        btn_copy.setToolTip("검색 결과를 클립보드에 복사")
        btn_copy.clicked.connect(self._copy_results_to_clipboard)
        rh_layout.addWidget(btn_copy)
        
        main_layout.addWidget(result_header)

        self.tabs = NoWheelTabWidget()
        self.tabs.setMinimumHeight(400)
        
        # Tab 1: Results
        self.table = ResultTable()
        self.table.favorite_requested.connect(self._add_to_favorites)
        self.table.cellDoubleClicked.connect(self._on_table_double_click)
        self.tabs.addTab(self.table, "🔍 검색 결과")
        
        # Tab 2: Favorites
        self.favorites_tab = self._create_favorites_tab()
        self.tabs.addTab(self.favorites_tab, "⭐ 즐겨찾기")
        
        # Tab 3: Logs
        self.log_viewer = LogViewer()
        self.tabs.addTab(self.log_viewer, "📋 로그")
        
        # Tab 4: History
        self.history_list = self.create_history_tab()
        self.tabs.addTab(self.history_list, "📜 검색 기록")
        
        main_layout.addWidget(self.tabs, 1)
        
        # 5. Manual Mode Actions
        self.manual_frame = QFrame()
        self.manual_frame.setObjectName("card")
        self.manual_frame.setVisible(False)
        m_layout = QHBoxLayout(self.manual_frame)
        self.manual_status_label = QLabel("🖐️ <b>수동 모드 활성화됨</b> - 브라우저에서 결과를 확인하세요")
        m_layout.addWidget(self.manual_status_label)
        
        btn_extract = QPushButton("데이터 추출하기")
        btn_extract.setObjectName("manual_btn")
        btn_extract.clicked.connect(self._manual_extract)
        btn_close_browser = QPushButton("브라우저 닫기")
        btn_close_browser.setObjectName("secondary_btn")
        btn_close_browser.clicked.connect(self._close_active_browser)
        m_layout.addStretch()
        m_layout.addWidget(btn_extract)
        m_layout.addWidget(btn_close_browser)
        
        main_layout.addWidget(self.manual_frame)
        
        # 스크롤 영역에 컨테이너 설정
        scroll.setWidget(container)
        self.setCentralWidget(scroll)
        
        # Status Bar
        self.statusBar().showMessage("준비 완료 | Ctrl+Enter: 검색, Ctrl+Shift+Enter: 강제 재조회, F5: 새로고침, Esc: 취소")

    def _toggle_search_panel(self):
        """검색 패널 접기/펼치기 토글"""
        is_visible = self.search_panel.isVisible()
        self.search_panel.setVisible(not is_visible)
        self.btn_toggle_search.setText("▶ 검색 설정" if is_visible else "▼ 검색 설정")

    def _setup_shortcuts(self):
        """키보드 단축키 설정"""
        # Ctrl+Enter: Start search
        shortcut_search = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut_search.activated.connect(self.search_panel._on_search)

        # Ctrl+Shift+Enter: Force refresh (cache bypass)
        shortcut_force_search = QShortcut(QKeySequence("Ctrl+Shift+Return"), self)
        shortcut_force_search.activated.connect(self._start_force_refresh_search)
        
        # F5: Refresh (reapply filter)
        shortcut_refresh = QShortcut(QKeySequence("F5"), self)
        shortcut_refresh.activated.connect(self._apply_filter)
        
        # Escape: Cancel / Close dialogs
        shortcut_esc = QShortcut(QKeySequence("Escape"), self)
        shortcut_esc.activated.connect(self._on_escape)
        
        # Ctrl+F: Focus on filter
        shortcut_filter = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut_filter.activated.connect(lambda: self.filter_panel.cb_airline_category.setFocus())

    def _start_force_refresh_search(self):
        """캐시를 우회한 강제 재조회 단축키 처리"""
        if not hasattr(self, "search_panel"):
            return
        self.search_panel._on_force_refresh_search()

    def _schedule_filter_apply(self, filters):
        """연속 필터 이벤트를 디바운스로 합쳐 마지막 변경만 적용."""
        self._pending_filter = filters
        self._filter_apply_timer.start(scraper_config.FILTER_DEBOUNCE_MS)

    def _run_scheduled_filter_apply(self):
        if self._pending_filter is None:
            return
        filters = self._pending_filter
        self._pending_filter = None
        self._apply_filter(filters)

    def _append_filter_log(self, message: str):
        """동일 필터 로그의 짧은 간격 중복 출력을 억제."""
        now = time.monotonic()
        if message == self._last_filter_log_msg and (now - self._last_filter_log_ts) < 1.0:
            return
        self._last_filter_log_msg = message
        self._last_filter_log_ts = now
        self.log_viewer.append_log(message)

    def _get_running_workers(self):
        """현재 실행 중인 워커 목록 반환"""
        running_workers = []
        if self.worker and self.worker.isRunning():
            running_workers.append(("일반 검색", self.worker))
        if self.multi_worker and self.multi_worker.isRunning():
            running_workers.append(("다중 목적지 검색", self.multi_worker))
        if self.date_worker and self.date_worker.isRunning():
            running_workers.append(("날짜 범위 검색", self.date_worker))
        return running_workers

    def _ensure_no_running_search(self):
        """새 검색 시작 전 동시 실행 여부 확인"""
        running_workers = self._get_running_workers()
        if not running_workers:
            return True

        running_names = ", ".join(name for name, _ in running_workers)
        QMessageBox.warning(
            self,
            "검색 진행 중",
            f"이미 검색이 진행 중입니다: {running_names}\n\n"
            "Esc로 현재 검색을 취소하거나 완료 후 다시 시도해주세요."
        )
        return False

    def _on_escape(self):
        """Escape 키 처리 - 검색 취소 및 브라우저 정리"""
        running_workers = self._get_running_workers()

        if not running_workers:
            if self.active_searcher:
                self._close_active_browser(confirm=True)
            return

        # 중복 취소 방지
        if self._cancelling:
            return
        self._cancelling = True

        try:
            reply = QMessageBox.question(
                self, "검색 취소", "진행 중인 검색 작업을 취소하시겠습니까?\n(브라우저가 안전하게 종료됩니다)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            for worker_name, worker in running_workers:
                if hasattr(worker, 'cancel'):
                    worker.cancel()
                worker.requestInterruption()
                if not worker.wait(5000):
                    self.log_viewer.append_log(f"⚠️ {worker_name} 종료 지연 - 추가 대기 중")
                    if not worker.wait(2000):
                        worker.terminate()
                        worker.wait(500)
                self.log_viewer.append_log(f"⚠️ {worker_name} 취소 요청 완료")

            self.search_panel.set_searching(False)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("검색 취소됨")
            self.log_viewer.append_log("⚠️ 사용자가 검색을 취소했습니다. 브라우저가 정리되었습니다.")
        finally:
            self._cancelling = False

    def _on_table_double_click(self, row, col):
        """테이블 더블클릭 - 예약 페이지 열기"""
        flight = self.table.get_flight_at_row(row)
        if flight:
            # Construct Interpark search URL
            origin = self.current_search_params.get('origin', 'ICN')
            dest = self.current_search_params.get('dest', 'NRT')
            dep = self.current_search_params.get('dep', '')
            ret = self.current_search_params.get('ret', '')
            
            # CITY_CODES_MAP에 있으면 도시 코드(c:)로, 없으면 공항 코드(a:)로 처리
            if origin in config.CITY_CODES_MAP:
                origin_code = config.CITY_CODES_MAP[origin]
                origin_prefix = "c"
            else:
                origin_code = origin
                origin_prefix = "a"
            
            if dest in config.CITY_CODES_MAP:
                dest_code = config.CITY_CODES_MAP[dest]
                dest_prefix = "c"
            else:
                dest_code = dest
                dest_prefix = "a"
            
            if ret:
                url = f"https://travel.interpark.com/air/search/{origin_prefix}:{origin_code}-{dest_prefix}:{dest_code}-{dep}/{dest_prefix}:{dest_code}-{origin_prefix}:{origin_code}-{ret}"
            else:
                url = f"https://travel.interpark.com/air/search/{origin_prefix}:{origin_code}-{dest_prefix}:{dest_code}-{dep}"
            
            webbrowser.open(url)
            self.log_viewer.append_log(f"브라우저에서 예약 페이지 열기: {flight.airline}")

    # --- Favorites Tab ---
    def _create_favorites_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("저장된 즐겨찾기 목록"))
        toolbar.addStretch()
        
        btn_refresh = QPushButton("🔄 새로고침")
        btn_refresh.clicked.connect(self._refresh_favorites)
        toolbar.addWidget(btn_refresh)
        
        btn_delete = QPushButton("🗑️ 선택 삭제")
        btn_delete.clicked.connect(self._delete_selected_favorite)
        toolbar.addWidget(btn_delete)
        
        layout.addLayout(toolbar)
        
        # Table
        self.fav_table = QTableWidget()
        self.fav_table.setColumnCount(7)
        self.fav_table.setHorizontalHeaderLabels([
            "ID", "항공사", "가격", "출발지", "도착지", "출발일", "메모"
        ])
        self.fav_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.fav_table.setColumnHidden(0, True)  # Hide ID column
        self.fav_table.setAlternatingRowColors(True)
        self.fav_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.fav_table)
        
        # Stats
        self.fav_stats_label = QLabel("")
        self.fav_stats_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(self.fav_stats_label)
        
        self._refresh_favorites()
        return widget
    
    def _refresh_favorites(self):
        favorites = self.db.get_favorites()
        self.fav_table.setRowCount(len(favorites))
        
        for i, fav in enumerate(favorites):
            self.fav_table.setItem(i, 0, QTableWidgetItem(str(fav.id)))
            self.fav_table.setItem(i, 1, QTableWidgetItem(fav.airline))
            
            price_item = QTableWidgetItem(f"{fav.price:,}원")
            price_item.setForeground(QColor("#4cc9f0"))
            self.fav_table.setItem(i, 2, price_item)
            
            self.fav_table.setItem(i, 3, QTableWidgetItem(fav.origin))
            self.fav_table.setItem(i, 4, QTableWidgetItem(fav.destination))
            self.fav_table.setItem(i, 5, QTableWidgetItem(fav.departure_date))
            self.fav_table.setItem(i, 6, QTableWidgetItem(fav.note))
        
        stats = self.db.get_stats()
        self.fav_stats_label.setText(
            f"총 {stats['favorites']}개 즐겨찾기 | "
            f"가격기록 {stats['price_history']}건 | "
            f"검색로그 {stats['search_logs']}건"
        )
    
    def _add_to_favorites(self, row):
        flight = self.table.get_flight_at_row(row)
        if not flight:
            return
        
        # Check if already favorited
        if self.db.is_favorite(
            flight.airline, flight.price, flight.departure_time,
            self.current_search_params.get('origin', ''),
            self.current_search_params.get('dest', '')
        ):
            QMessageBox.information(self, "알림", "이미 즐겨찾기에 추가된 항공권입니다.")
            return
        
        # Ask for note
        note, ok = QInputDialog.getText(self, "즐겨찾기 메모", "메모를 입력하세요 (선택):")
        if not ok:
            return
        
        flight_data = {
            'airline': flight.airline,
            'price': flight.price,
            'origin': self.current_search_params.get('origin', ''),
            'destination': self.current_search_params.get('dest', ''),
            'departure_date': self.current_search_params.get('dep', ''),
            'return_date': self.current_search_params.get('ret'),
            'departure_time': flight.departure_time,
            'arrival_time': flight.arrival_time,
            'stops': flight.stops,
            'note': note
        }
        
        self.db.add_favorite(flight_data, self.current_search_params)
        self._refresh_favorites()
        self.log_viewer.append_log(f"⭐ 즐겨찾기 추가: {flight.airline} {flight.price:,}원")
        QMessageBox.information(self, "완료", "즐겨찾기에 추가되었습니다!")
    
    def _delete_selected_favorite(self):
        row = self.fav_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "선택 오류", "삭제할 항목을 선택하세요.")
            return
        
        fav_id = int(self.fav_table.item(row, 0).text())
        reply = QMessageBox.question(
            self, "삭제 확인", "선택한 즐겨찾기를 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.remove_favorite(fav_id)
            self._refresh_favorites()
            self.log_viewer.append_log("즐겨찾기 삭제됨")

    # --- Export Functions ---
    def _export_to_csv(self):
        """검색 결과를 CSV 파일로 저장"""
        if not self.all_results:
            QMessageBox.warning(self, "내보내기 오류", "내보낼 검색 결과가 없습니다.")
            return
        
        import csv
        
        fname, _ = QFileDialog.getSaveFileName(
            self, "CSV로 저장", 
            f"flight_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not fname:
            return
        
        try:
            with open(fname, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # Header
                writer.writerow([
                    "항공사", "가격", "가는편 출발", "가는편 도착", "경유",
                    "오는편 출발", "오는편 도착", "오는편 경유", "출처"
                ])
                
                # Data
                for flight in self.all_results:
                    writer.writerow([
                        flight.airline,
                        flight.price,
                        flight.departure_time,
                        flight.arrival_time,
                        flight.stops,
                        getattr(flight, 'return_departure_time', '-'),
                        getattr(flight, 'return_arrival_time', '-'),
                        getattr(flight, 'return_stops', '-'),
                        flight.source
                    ])
            
            self.log_viewer.append_log(f"📥 CSV 저장 완료: {fname}")
            QMessageBox.information(self, "저장 완료", f"{len(self.all_results)}개 결과가 저장되었습니다.\n{fname}")
            
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", f"파일 저장 중 오류 발생:\n{e}")
    
    def _copy_results_to_clipboard(self):
        """검색 결과를 클립보드에 복사"""
        if not self.all_results:
            QMessageBox.warning(self, "복사 오류", "복사할 검색 결과가 없습니다.")
            return
        
        from PyQt6.QtWidgets import QApplication
        
        lines = ["항공사\t가격\t출발\t도착\t경유"]
        for flight in self.all_results[:50]:  # 최대 50개
            lines.append(f"{flight.airline}\t{flight.price:,}원\t{flight.departure_time}\t{flight.arrival_time}\t{flight.stops}회")
        
        text = "\n".join(lines)
        QApplication.clipboard().setText(text)
        
        self.log_viewer.append_log(f"📋 {min(len(self.all_results), 50)}개 결과 클립보드에 복사됨")
        QMessageBox.information(self, "복사 완료", f"{min(len(self.all_results), 50)}개 결과가 클립보드에 복사되었습니다.")

    # --- Multi-Destination Search ---
    def _open_multi_dest_search(self):
        dialog = MultiDestDialog(self, self.prefs)
        dialog.search_requested.connect(self._start_multi_search)
        dialog.exec()

    def _guard_manual_browser_for_new_search(self, action_name: str) -> bool:
        """수동 모드 브라우저가 열려 있을 때 새 검색 진행 여부를 확인"""
        if not self.active_searcher:
            return True

        reply = QMessageBox.question(
            self,
            "수동 모드 브라우저 유지",
            f"수동 모드 브라우저가 열려 있습니다.\n닫고 {action_name}을(를) 시작할까요?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._close_active_browser(confirm=False)
            return True

        self.log_viewer.append_log(f"ℹ️ {action_name} 취소: 수동 모드 브라우저를 유지했습니다.")
        return False
    
    def _start_multi_search(self, origin, destinations, dep, ret, adults):
        if not self._ensure_no_running_search():
            return

        if not self._guard_manual_browser_for_new_search("다중 검색"):
            return

        self.log_viewer.clear()
        self.log_viewer.append_log(f"🌍 다중 목적지 검색 시작: {', '.join(destinations)}")
        
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat("다중 목적지 검색 중...")
        self.tabs.setCurrentIndex(2)  # Logs tab
        
        max_results = self.prefs.get_max_results()
        self.multi_worker = MultiSearchWorker(origin, destinations, dep, ret, adults, max_results)
        self.multi_worker.progress.connect(self._update_progress)
        self.multi_worker.single_finished.connect(self._on_multi_single_finished)
        self.multi_worker.all_finished.connect(self._multi_search_finished)
        self.multi_worker.start()

    def _on_multi_single_finished(self, dest, results):
        if results:
            best = min(results, key=lambda x: x.price)
            self.log_viewer.append_log(
                f"📌 [{dest}] 중간 결과: {len(results)}건, 최저가 {best.price:,}원 ({best.airline})"
            )
        else:
            self.log_viewer.append_log(f"📌 [{dest}] 중간 결과: 검색 결과 없음")
    
    def _multi_search_finished(self, results):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("다중 검색 완료")
        
        # Show results dialog
        dialog = MultiDestResultDialog(results, self)
        dialog.exec()
        
        self.log_viewer.append_log(f"✅ 다중 목적지 검색 완료: {len(results)}개 목적지")

    # --- Date Range Search ---
    def _open_date_range_search(self):
        dialog = DateRangeDialog(self, self.prefs)
        dialog.search_requested.connect(self._start_date_search)
        dialog.exec()
    
    def _start_date_search(self, origin, dest, dates, duration, adults):
        if not self._ensure_no_running_search():
            return

        if not self._guard_manual_browser_for_new_search("날짜 범위 검색"):
            return

        self.log_viewer.clear()
        self.log_viewer.append_log(f"📅 날짜 범위 검색 시작: {dates[0]} ~ {dates[-1]}")
        
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat("날짜별 검색 중...")
        self.tabs.setCurrentIndex(2)  # Logs tab
        
        max_results = self.prefs.get_max_results()
        self.date_worker = DateRangeWorker(origin, dest, dates, duration, adults, max_results)
        self.date_worker.progress.connect(self._update_progress)
        self.date_worker.date_result.connect(self._on_date_range_result)
        self.date_worker.all_finished.connect(self._date_search_finished)
        self.date_worker.start()

    def _on_date_range_result(self, date, min_price, airline):
        self.log_viewer.append_log(f"📌 [{date}] 중간 결과: {min_price:,}원 ({airline})")
    
    def _date_search_finished(self, results):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("날짜 검색 완료")
        
        # 캘린더 뷰용 데이터 저장
        self.date_range_results = results
        
        # Show results dialog
        dialog = DateRangeResultDialog(results, self)
        dialog.exec()
        
        self.log_viewer.append_log(f"✅ 날짜 범위 검색 완료: {len(results)}일 (캘린더뷰 사용 가능)")

    # --- Standard Search ---
    def _start_search(self, origin, dest, dep, ret, adults, cabin_class="ECONOMY", force_refresh=False):
        if not self._ensure_no_running_search():
            return

        if not self._guard_manual_browser_for_new_search("새 검색"):
            return

        if hasattr(self, "search_panel") and hasattr(self.search_panel, "consume_force_refresh"):
            force_refresh = bool(force_refresh or self.search_panel.consume_force_refresh())

        # Save search params for later use
        self.current_search_params = {
            "origin": origin,
            "dest": dest,
            "dep": dep,
            "ret": ret,
            "adults": adults,
            "cabin_class": cabin_class,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        
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
        manual_browser_open = self.active_searcher is not None
        if manual_browser_open and hasattr(self, "manual_status_label"):
            self.manual_status_label.setText("🖐️ <b>수동 모드 유지 중</b> - 브라우저 닫기 가능")
        self.manual_frame.setVisible(manual_browser_open)
        self.log_viewer.clear()
        self.log_viewer.append_log(f"검색 프로세스 시작... (좌석등급: {cabin_label})")
        if force_refresh:
            self.statusBar().showMessage("🔄 캐시 무시 재조회 실행 중...")
            self.log_viewer.append_log("🔄 강제 재조회: 캐시를 무시하고 새로 검색합니다.")
        self.tabs.setCurrentIndex(2)  # Switch to logs
        
        # Start Worker
        max_results = self.prefs.get_max_results()
        self.worker = SearchWorker(
            origin, dest, dep, ret, adults, cabin_class, max_results, force_refresh=force_refresh
        )
        self.worker.progress.connect(self._update_progress)
        self.worker.finished.connect(self._search_finished)
        self.worker.error.connect(self._search_error)
        self.worker.manual_mode_signal.connect(self._activate_manual_mode)
        self.worker.start()

    def _update_progress(self, msg):
        self.statusBar().showMessage(msg)
        self.progress_bar.setFormat(msg)
        now = time.monotonic()
        dedup_window = max(
            0, int(getattr(scraper_config, "PROGRESS_LOG_DEDUP_WINDOW_MS", 300))
        ) / 1000.0
        if msg == self._last_progress_msg and (now - self._last_progress_ts) < dedup_window:
            return
        self._last_progress_msg = msg
        self._last_progress_ts = now
        self.log_viewer.append_log(msg)

    def _search_finished(self, results):
        self.search_panel.set_searching(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        
        if results:
            self.all_results = results
            self.results = results
            
            # Save price history
            if self.current_search_params:
                self.db.add_price_history_batch(
                    self.current_search_params.get('origin', ''),
                    self.current_search_params.get('dest', ''),
                    self.current_search_params.get('dep', ''),
                    results,
                )
                
                # Log search
                self.db.log_search(
                    self.current_search_params.get('origin', ''),
                    self.current_search_params.get('dest', ''),
                    self.current_search_params.get('dep', ''),
                    self.current_search_params.get('ret'),
                    self.current_search_params.get('adults', 1),
                    len(results),
                    results[0].price if results else None
                )
                
                # 마지막 검색 결과를 DB에 저장 (프로그램 재시작 시 복원용)
                self.db.save_last_search_results(self.current_search_params, results)
                
                # 가격 알림 체크
                self._check_price_alerts(results)
            
            best_price = results[0].price
            self.progress_bar.setFormat(f"✨ 검색 완료! 최저가: {best_price:,}원 🏆")
            self.log_viewer.append_log(f"✅ 검색 완료. {len(results)}건 발견, 최저가: {best_price:,}원")
            self._apply_filter()
            self.tabs.setCurrentIndex(0)  # Switch to results
        else:
            self.progress_bar.setFormat("💭 검색 결과 없음")
            self.log_viewer.append_log("⚠️ 검색 결과가 없습니다.")
            self.table.update_data([])
            self.tabs.setCurrentIndex(0)
            QMessageBox.information(self, "결과 없음", "항공권을 찾을 수 없습니다.")
    
    def _check_price_alerts(self, results):
        """검색 완료 후 활성 가격 알림 체크"""
        if not results or not self.current_search_params:
            return
        
        try:
            alerts = self.db.get_active_alerts()
            origin = self.current_search_params.get('origin', '').upper()
            dest = self.current_search_params.get('dest', '').upper()
            dep = self.current_search_params.get('dep', '')
            ret = self.current_search_params.get('ret')
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
                
                # 알림 마지막 체크 시간 및 가격 업데이트
                self.db.update_alert_check(alert.id, min_price)
                
                # 목표 가격 이하인 경우 알림 발생
                if min_price <= alert.target_price:
                    self.db.mark_alert_triggered(alert.id)
                    self.log_viewer.append_log(
                        f"🔔 가격 알림 발동! {origin}→{dest} 최저가 {min_price:,}원 "
                        f"(목표: {alert.target_price:,}원 이하)"
                    )
                    QMessageBox.information(
                        self, "🔔 가격 알림",
                        f"목표 가격에 도달했습니다!\n\n"
                        f"노선: {origin} → {dest}\n"
                        f"최저가: {min_price:,}원\n"
                        f"목표 가격: {alert.target_price:,}원 이하"
                    )
        except Exception as e:
            logger.debug(f"가격 알림 체크 중 오류 (무시됨): {e}")

    def _search_error(self, err_msg):
        self.search_panel.set_searching(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("❌ 오류 발생")
        self.log_viewer.append_log(f"❌ 오류 발생: {err_msg}")

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

    def _activate_manual_mode(self, searcher):
        self.active_searcher = searcher
        self.search_panel.set_searching(False)
        
        self.manual_frame.setVisible(True)
        if hasattr(self, "manual_status_label"):
            self.manual_status_label.setText("🖐️ <b>수동 모드 활성화됨</b> - 브라우저가 유지됩니다")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(50)
        self.progress_bar.setFormat("수동 모드 대기 중...")
        self.log_viewer.append_log("수동 모드로 전환됨.")
        
        QMessageBox.warning(self, "수동 모드 전환", 
                            "자동 추출에 실패했습니다.\n"
                            "브라우저창이 유지됩니다. 직접 검색 후 '데이터 추출하기' 버튼을 누르세요.")

    def _manual_extract(self):
        if not self.active_searcher:
            return
            
        try:
            self.log_viewer.append_log("수동 추출 시도...")
            results = self.active_searcher.extract_manual()
            if results:
                self._search_finished(results)
            else:
                self.log_viewer.append_log("수동 추출 실패: 데이터 없음")
                QMessageBox.warning(self, "실패", "데이터를 찾을 수 없습니다.")
        except Exception as e:
            QMessageBox.critical(self, "오류", str(e))
        finally:
            if hasattr(self, "manual_status_label"):
                self.manual_status_label.setText("🖐️ <b>수동 모드 유지 중</b> - 필요 시 다시 추출 가능합니다")

    def _close_active_browser(self, confirm: bool = True):
        if not self.active_searcher:
            return
        if confirm:
            reply = QMessageBox.question(
                self,
                "브라우저 닫기",
                "수동 모드 브라우저를 닫으시겠습니까?\n(열려있는 페이지는 종료됩니다)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        try:
            self.active_searcher.close()
            self.log_viewer.append_log("✅ 수동 모드 브라우저를 닫았습니다.")
        except Exception as e:
            logger.debug(f"Failed to close manual browser: {e}")
        finally:
            self.active_searcher = None
            self.manual_frame.setVisible(False)

    def _open_main_settings(self):
        dlg = SettingsDialog(self, self.prefs)
        dlg.exec()
        self.search_panel._refresh_combos()
        self.search_panel._refresh_profiles()

    def _show_shortcuts(self):
        """키보드 단축키 다이얼로그 표시"""
        dlg = ShortcutsDialog(self)
        dlg.exec()

    def _open_price_alert_dialog(self):
        """가격 알림 관리 다이얼로그 열기"""
        dlg = PriceAlertDialog(self, self.db, self.prefs)
        dlg.exec()

    def _toggle_theme(self):
        """라이트/다크 테마 전환 및 저장"""
        if self.is_dark_theme:
            # 다크 -> 라이트
            self.setStyleSheet(LIGHT_THEME)
            self.btn_theme.setText("☀️")
            self.is_dark_theme = False
            self.prefs.set_theme("light")
        else:
            # 라이트 -> 다크
            self.setStyleSheet(DARK_THEME)
            self.btn_theme.setText("🌙")
            self.is_dark_theme = True
            self.prefs.set_theme("dark")

    def _apply_filter(self, filters=None):
        if filters is None:
            filters = self.filter_panel.get_current_filters()
            
        if not self.all_results:
            return
            
        direct_only = filters.get("direct_only", False)
        include_layover = filters.get("include_layover", True)
        airline_category = filters.get("airline_category", "ALL")
        max_stops = filters.get("max_stops", 3)
        
        # Outbound Time Filter
        start_h = filters.get("start_time", 0)
        end_h = filters.get("end_time", 24)
        
        # Inbound Time Filter
        ret_start_h = filters.get("ret_start_time", 0)
        ret_end_h = filters.get("ret_end_time", 24)
        
        # 만약 필터 패널에서 값을 안 줬다면(초기 로딩 등) 설정값 사용
        if "start_time" not in filters:
            pref_time = self.prefs.get_preferred_time()
            start_h = pref_time.get("departure_start", 0)
            end_h = pref_time.get("departure_end", 24)
            # 오는편 선호 시간은 설정에 없으므로 기본값(0-24) 유지
            
        filtered = []
        for f in self.all_results:
            # 1. Stops Filter
            if direct_only and f.stops > 0:
                continue
            if not include_layover and f.stops > 0:
                continue
            if f.stops > max_stops:
                continue
            
            # 2. Airline Category Filter
            if airline_category != "ALL":
                category = config.get_airline_category(f.airline)
                if category != airline_category:
                    continue
            
            # 3. Time Filter (Outbound)
            try:
                if ':' in f.departure_time:
                    dep_h = int(f.departure_time.split(':')[0])
                    if not (start_h <= dep_h <= end_h):  # <= 로 변경하여 종료시간 포함
                        continue
            except Exception as e:
                logger.debug(f"Time filter parsing error: {e}")
            
            # 4. Time Filter (Inbound) - Only for round trips
            if f.is_round_trip and hasattr(f, 'return_departure_time') and f.return_departure_time:
                try:
                    if ':' in f.return_departure_time:
                        ret_dep_h = int(f.return_departure_time.split(':')[0])
                        if not (ret_start_h <= ret_dep_h <= ret_end_h):  # <= 로 변경
                            continue
                except Exception as e:
                    logger.debug(f"Return time filter parsing error: {e}")
            
            # 5. Price Range Filter (Advanced)
            min_price = filters.get("min_price", 0)
            max_price = filters.get("max_price", MAX_PRICE_FILTER)
            if f.price < min_price:
                continue
            if max_price < MAX_PRICE_FILTER:
                if f.price > max_price:
                    continue
                
            filtered.append(f)
            
        self.table.update_data(filtered)
        
        # 상태 메시지에 가격 범위 표시
        price_msg = ""
        min_p = filters.get("min_price", 0)
        max_p = filters.get("max_price", MAX_PRICE_FILTER)
        if min_p > 0 or max_p < MAX_PRICE_FILTER:
            price_msg = f" | 가격: {min_p//10000}~{max_p//10000}만원"
        
        msg = f"필터링: {len(filtered)}/{len(self.all_results)} | 시간: {start_h}~{end_h}시 | 항공사: {airline_category}{price_msg}"
        self.statusBar().showMessage(msg)
        self._append_filter_log(msg)

    # --- History Tab Methods ---
    def create_history_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.list_history = QListWidget()
        self.list_history.itemDoubleClicked.connect(self.restore_search_from_history)
        layout.addWidget(self.list_history)
        
        btn_refresh = QPushButton("기록 새로고침")
        btn_refresh.clicked.connect(self._refresh_history_tab)
        layout.addWidget(btn_refresh)
        
        self._refresh_history_tab()
        return widget

    def _refresh_history_tab(self):
        if not hasattr(self, 'list_history'):
            return
        self.list_history.clear()
        history = self.prefs.get_history()
        for item in history:
            display = f"[{item.get('timestamp')}] {item.get('origin')} ➝ {item.get('dest')} ({item.get('dep')})"
            list_item = QListWidgetItem(display)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.list_history.addItem(list_item)

    def _restore_search_panel_from_params(self, params: dict):
        """검색 파라미터를 검색 패널 UI에 복원"""
        if not params:
            return

        sp = self.search_panel

        origin = params.get('origin')
        if origin:
            idx = sp.cb_origin.findData(origin)
            if idx >= 0:
                sp.cb_origin.setCurrentIndex(idx)

        dest = params.get('dest')
        if dest:
            idx = sp.cb_dest.findData(dest)
            if idx >= 0:
                sp.cb_dest.setCurrentIndex(idx)

        dep = params.get('dep')
        if dep:
            dep_date = QDate.fromString(dep, "yyyyMMdd")
            if dep_date.isValid():
                sp.date_dep.setDate(dep_date)

        ret = params.get('ret')
        if ret:
            sp.rb_round.setChecked(True)
            sp._toggle_return_date()
            ret_date = QDate.fromString(ret, "yyyyMMdd")
            if ret_date.isValid():
                sp.date_ret.setDate(ret_date)
        else:
            sp.rb_oneway.setChecked(True)
            sp._toggle_return_date()

        adults = params.get('adults')
        if adults:
            sp.spin_adults.setValue(int(adults))

        cabin = params.get('cabin_class')
        if cabin:
            idx = sp.cb_cabin_class.findData(cabin)
            if idx >= 0:
                sp.cb_cabin_class.setCurrentIndex(idx)

    def restore_search_from_history(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        try:
            sp = self.search_panel
            
            idx_o = sp.cb_origin.findData(data['origin'])
            if idx_o >= 0:
                sp.cb_origin.setCurrentIndex(idx_o)
            else:
                sp.cb_origin.setCurrentText(data['origin'])
            
            idx_d = sp.cb_dest.findData(data['dest'])
            if idx_d >= 0:
                sp.cb_dest.setCurrentIndex(idx_d)
            else:
                sp.cb_dest.setCurrentText(data['dest'])
            
            qt_date = QDate.fromString(data['dep'], "yyyyMMdd")
            sp.date_dep.setDate(qt_date)
            
            if data['ret']:
                sp.rb_round.setChecked(True)
                sp.date_ret.setEnabled(True)
                sp.date_ret.setDate(QDate.fromString(data['ret'], "yyyyMMdd"))
            else:
                sp.rb_oneway.setChecked(True)
                sp._toggle_return_date()
                
            sp.spin_adults.setValue(data['adults'])
            
            QMessageBox.information(self, "복원 완료", "검색 조건이 복원되었습니다.")
            
        except Exception as e:
            QMessageBox.warning(self, "오류", f"복원 중 오류: {e}")
    
    # --- Session Management Methods ---
    def _save_session(self):
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
    
    def _load_session(self):
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
        self.current_search_params = params
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
    def _show_calendar_view(self):
        """날짜별 가격 캘린더 뷰 표시"""
        # 저장된 날짜별 가격 데이터가 있는지 확인
        if not hasattr(self, 'date_range_results') or not self.date_range_results:
            QMessageBox.information(
                self, "캘린더 뷰", 
                "날짜별 가격 데이터가 없습니다.\n\n'📅 날짜 범위' 버튼을 눌러 먼저 날짜별 최저가를 검색해주세요."
            )
            return
        
        # 캘린더 다이얼로그 표시
        dlg = CalendarViewDialog(self.date_range_results, self)
        dlg.date_selected.connect(self._on_calendar_date_selected)
        dlg.exec()
    
    def _on_calendar_date_selected(self, date_str):
        """캘린더에서 날짜 선택 시 해당 날짜로 검색 조건 설정"""
        try:
            qdate = QDate.fromString(date_str, "yyyyMMdd")
            if qdate.isValid():
                self.search_panel.date_dep.setDate(qdate)
                self.log_viewer.append_log(f"📅 출발일 변경: {qdate.toString('yyyy-MM-dd')}")
        except Exception as e:
            logger.debug(f"Calendar date selection error: {e}")

    def _restore_last_search(self):
        """프로그램 시작 시 마지막 검색 결과 복원"""
        try:
            search_params, results, searched_at, hours_ago = self.db.get_last_search_results()
            
            if not results:
                self.log_viewer.append_log("ℹ️ 이전 검색 기록이 없습니다.")
                return
            
            # 검색 조건 복원
            self.current_search_params = search_params
            self.all_results = results
            self.results = results
            
            # 검색 패널에 조건 복원
            try:
                self._restore_search_panel_from_params(search_params)
            except Exception as e:
                logger.debug(f"검색 조건 복원 실패: {e}")
            
            # 로그 및 상태 표시
            min_price = results[0].price if results else 0
            origin = search_params.get('origin', '?')
            dest = search_params.get('dest', '?')
            
            # 24시간 경과 여부는 비차단 안내만 표시
            if hours_ago >= 24:
                days_ago = int(hours_ago / 24)
                age_hours = int(hours_ago % 24)
                self.progress_bar.setFormat(f"⚠️ {days_ago}일 전 데이터 | 최저가: {min_price:,}원")
                self.statusBar().showMessage(
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

    def closeEvent(self, event):
        """창 닫기 시 워커 스레드 및 리소스 정리"""
        # Worker threads 정리 (안전한 종료 패턴)
        workers = [self.worker, self.multi_worker, self.date_worker]
        for worker in workers:
            if worker and worker.isRunning():
                if hasattr(worker, 'cancel'):
                    worker.cancel()
                worker.requestInterruption()  # 안전한 중단 요청
                if not worker.wait(5000):
                    logger.warning("Worker 스레드 종료 지연 - 추가 대기 시도")
                    if worker.wait(2000):
                        continue
                    logger.warning("Worker 스레드가 응답하지 않습니다. 강제 종료합니다.")
                    worker.terminate()  # 응답 없으면 강제 종료
                    worker.wait(500)
        
        # Active searcher 브라우저 종료
        if self.active_searcher:
            try:
                self.active_searcher.close()
            except Exception as e:
                logger.debug(f"Failed to close searcher: {e}")
        
        # 설정 저장
        try:
            if hasattr(self, 'search_panel'):
                self.search_panel.save_settings()
            self.prefs.save()
        except Exception as e:
            logger.warning(f"Failed to save settings on exit: {e}")
        
        event.accept()


def main():
    # 로깅 설정 (중앙 집중식)
    log_level = resolve_log_level()
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # HiDPI 설정
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


def resolve_log_level() -> int:
    level_name = os.environ.get("FLIGHTBOT_LOG_LEVEL", "INFO").upper().strip()
    return getattr(logging, level_name, logging.INFO)

if __name__ == "__main__":
    main()
