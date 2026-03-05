"""UiBootstrapMixin methods extracted from MainWindow."""

from app.mainwindow.shared import *


class UiBootstrapMixin:
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
        self.statusBar().showMessage("준비 완료 | Ctrl+Enter: 검색, F5: 새로고침, Esc: 취소")
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
        
        # F5: Refresh (reapply filter)
        shortcut_refresh = QShortcut(QKeySequence("F5"), self)
        shortcut_refresh.activated.connect(self._apply_filter)
        
        # Escape: Cancel / Close dialogs
        shortcut_esc = QShortcut(QKeySequence("Escape"), self)
        shortcut_esc.activated.connect(self._on_escape)
        
        # Ctrl+F: Focus on filter
        shortcut_filter = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut_filter.activated.connect(lambda: self.filter_panel.cb_airline_category.setFocus())
    def _on_table_double_click(self, row, col):
        """테이블 더블클릭 - 예약 페이지 열기"""
        flight = self.table.get_flight_at_row(row)
        if flight:
            # Construct Interpark search URL
            origin = self.current_search_params.get('origin', 'ICN')
            dest = self.current_search_params.get('dest', 'NRT')
            dep = self.current_search_params.get('dep', '')
            ret = self.current_search_params.get('ret', '')
            cabin = (self.current_search_params.get('cabin_class') or "ECONOMY").upper()
            if cabin not in {"ECONOMY", "BUSINESS", "FIRST"}:
                cabin = "ECONOMY"
            try:
                adults = int(self.current_search_params.get('adults', 1))
            except Exception:
                adults = 1
            adults = max(1, adults)
            
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
                url = (
                    f"https://travel.interpark.com/air/search/"
                    f"{origin_prefix}:{origin_code}-{dest_prefix}:{dest_code}-{dep}/"
                    f"{dest_prefix}:{dest_code}-{origin_prefix}:{origin_code}-{ret}"
                    f"?cabin={cabin}&adult={adults}"
                )
            else:
                url = (
                    f"https://travel.interpark.com/air/search/"
                    f"{origin_prefix}:{origin_code}-{dest_prefix}:{dest_code}-{dep}"
                    f"?cabin={cabin}&adult={adults}"
                )
            
            webbrowser.open(url)
            self.log_viewer.append_log(f"브라우저에서 예약 페이지 열기: {flight.airline}")

    # --- Favorites Tab ---
