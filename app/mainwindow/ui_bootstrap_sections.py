"""Section builders for the main window bootstrap UI."""

from __future__ import annotations

from typing import Any, Tuple

from app.mainwindow.shared import *


def create_scroll_container() -> Tuple[QScrollArea, QWidget, QVBoxLayout]:
    """Create the outer scroll container and root layout."""

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setStyleSheet(
        """
        QScrollArea {
            border: none;
            background: transparent;
        }
        QScrollArea > QWidget > QWidget {
            background: transparent;
        }
        """
    )

    container = QWidget()
    container.setStyleSheet("background: transparent;")
    container.setMinimumWidth(1200)

    main_layout = QVBoxLayout(container)
    main_layout.setContentsMargins(24, 24, 24, 24)
    main_layout.setSpacing(18)
    return scroll, container, main_layout


def add_header_section(window: Any, main_layout: QVBoxLayout) -> None:
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

    btn_multi = QPushButton("🌍 다중 목적지")
    btn_multi.setToolTip("여러 목적지를 한 번에 비교 검색")
    btn_multi.clicked.connect(window._open_multi_dest_search)
    h_layout.addWidget(btn_multi)

    btn_date = QPushButton("📅 날짜 범위")
    btn_date.setToolTip("날짜 범위에서 최저가 찾기")
    btn_date.clicked.connect(window._open_date_range_search)
    h_layout.addWidget(btn_date)

    sep1 = QFrame()
    sep1.setObjectName("v_separator")
    sep1.setFrameShape(QFrame.Shape.VLine)
    sep1.setFixedWidth(2)
    sep1.setFixedHeight(30)
    h_layout.addWidget(sep1)

    btn_calendar = QPushButton("📠 캘린더뷰")
    btn_calendar.setObjectName("secondary_btn")
    btn_calendar.setToolTip("날짜별 가격을 캘린더 형태로 보기 (날짜범위 검색 후 사용)")
    btn_calendar.clicked.connect(window._show_calendar_view)
    h_layout.addWidget(btn_calendar)

    btn_alert = QPushButton("🔔 가격알림")
    btn_alert.setObjectName("secondary_btn")
    btn_alert.setToolTip("목표 가격 설정 및 알림 관리")
    btn_alert.clicked.connect(window._open_price_alert_dialog)
    h_layout.addWidget(btn_alert)

    sep2 = QFrame()
    sep2.setObjectName("v_separator")
    sep2.setFrameShape(QFrame.Shape.VLine)
    sep2.setFixedWidth(2)
    sep2.setFixedHeight(30)
    h_layout.addWidget(sep2)

    btn_save_session = QPushButton("💶")
    btn_save_session.setObjectName("icon_btn")
    btn_save_session.setToolTip("현재 검색 결과를 파일로 저장")
    btn_save_session.clicked.connect(window._save_session)
    h_layout.addWidget(btn_save_session)

    btn_load_session = QPushButton("💛")
    btn_load_session.setObjectName("icon_btn")
    btn_load_session.setToolTip("저장한 검색 결과 불러오기")
    btn_load_session.clicked.connect(window._load_session)
    h_layout.addWidget(btn_load_session)

    btn_shortcuts = QPushButton("⌨️")
    btn_shortcuts.setObjectName("icon_btn")
    btn_shortcuts.setToolTip("키보드 단축키 보기")
    btn_shortcuts.clicked.connect(window._show_shortcuts)
    h_layout.addWidget(btn_shortcuts)

    window.btn_theme = QPushButton("🌔" if window.is_dark_theme else "☀️")
    window.btn_theme.setObjectName("icon_btn")
    window.btn_theme.setToolTip("라이트 / 다크 테마 전환")
    window.btn_theme.clicked.connect(window._toggle_theme)
    h_layout.addWidget(window.btn_theme)

    btn_main_settings = QPushButton("⚙️ 설정")
    btn_main_settings.clicked.connect(window._open_main_settings)
    h_layout.addWidget(btn_main_settings)

    main_layout.addWidget(header)


def add_search_panel_section(window: Any, main_layout: QVBoxLayout) -> None:
    toggle_container = QWidget()
    toggle_layout = QHBoxLayout(toggle_container)
    toggle_layout.setContentsMargins(0, 0, 0, 0)

    window.btn_toggle_search = QPushButton("▼ 검색 설정")
    window.btn_toggle_search.setStyleSheet(
        """
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
        """
    )
    window.btn_toggle_search.setCheckable(True)
    window.btn_toggle_search.setChecked(True)
    window.btn_toggle_search.clicked.connect(window._toggle_search_panel)
    toggle_layout.addWidget(window.btn_toggle_search)
    toggle_layout.addStretch()
    main_layout.addWidget(toggle_container)

    window.search_panel = SearchPanel(window.prefs)
    window.search_panel.search_requested.connect(window._start_search)
    main_layout.addWidget(window.search_panel)


def add_filter_progress_section(window: Any, main_layout: QVBoxLayout) -> None:
    filter_label = QLabel("필터")
    filter_label.setObjectName("section_title")
    main_layout.addWidget(filter_label)

    window.filter_panel = FilterPanel()
    window.filter_panel.filter_changed.connect(window._schedule_filter_apply)
    main_layout.addWidget(window.filter_panel)

    status_label = QLabel("🔄 검색 상태")
    status_label.setObjectName("section_title")
    main_layout.addWidget(status_label)

    window.progress_bar = QProgressBar()
    window.progress_bar.setFormat("✨ 준비됨")
    window.progress_bar.setMinimumHeight(48)
    window.progress_bar.setStyleSheet(
        """
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
        """
    )
    main_layout.addWidget(window.progress_bar)


def add_results_section(window: Any, main_layout: QVBoxLayout) -> None:
    result_header = QWidget()
    rh_layout = QHBoxLayout(result_header)
    rh_layout.setContentsMargins(0, 0, 0, 0)

    result_label = QLabel("검색 결과")
    result_label.setObjectName("section_title")
    rh_layout.addWidget(result_label)
    rh_layout.addStretch()

    btn_export_csv = QPushButton("📥 CSV 저장")
    btn_export_csv.setObjectName("tool_btn")
    btn_export_csv.setToolTip("검색 결과를 CSV 파일로 저장")
    btn_export_csv.clicked.connect(window._export_to_csv)
    rh_layout.addWidget(btn_export_csv)

    btn_copy = QPushButton("📋 복사")
    btn_copy.setObjectName("tool_btn")
    btn_copy.setToolTip("검색 결과를 클립보드에 복사")
    btn_copy.clicked.connect(window._copy_results_to_clipboard)
    rh_layout.addWidget(btn_copy)

    main_layout.addWidget(result_header)

    window.tabs = NoWheelTabWidget()
    window.tabs.setMinimumHeight(400)

    window.table = ResultTable()
    window.table.favorite_requested.connect(window._add_to_favorites)
    window.table.cellDoubleClicked.connect(window._on_table_double_click)
    window.tabs.addTab(window.table, "🔍 검색 결과")

    window.favorites_tab = window._create_favorites_tab()
    window.tabs.addTab(window.favorites_tab, "⭐ 즐겨찾기")

    window.log_viewer = LogViewer()
    window.tabs.addTab(window.log_viewer, "📋 로그")

    window.history_list = window.create_history_tab()
    window.tabs.addTab(window.history_list, "📚 검색 기록")

    main_layout.addWidget(window.tabs, 1)


def add_manual_mode_section(window: Any, main_layout: QVBoxLayout) -> None:
    window.manual_frame = QFrame()
    window.manual_frame.setObjectName("card")
    window.manual_frame.setVisible(False)

    m_layout = QHBoxLayout(window.manual_frame)
    window.manual_status_label = QLabel(
        "🖐️ <b>수동 모드 활성화됨</b> - 브라우저에서 결과를 확인하세요"
    )
    m_layout.addWidget(window.manual_status_label)

    btn_extract = QPushButton("데이터 추출하기")
    btn_extract.setObjectName("manual_btn")
    btn_extract.clicked.connect(window._manual_extract)

    btn_close_browser = QPushButton("브라우저 닫기")
    btn_close_browser.setObjectName("secondary_btn")
    btn_close_browser.clicked.connect(window._close_active_browser)

    m_layout.addStretch()
    m_layout.addWidget(btn_extract)
    m_layout.addWidget(btn_close_browser)
    main_layout.addWidget(window.manual_frame)


def finalize_window_layout(window: Any, scroll: QScrollArea, container: QWidget) -> None:
    scroll.setWidget(container)
    window.setCentralWidget(scroll)

    status_bar = window.statusBar()
    if status_bar is not None:
        status_bar.showMessage("준비 완료 | Ctrl+Enter: 검색, F5: 새로고침, Esc: 취소")
