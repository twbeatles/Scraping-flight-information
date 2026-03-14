"""Search panel UI construction mixin."""

from ui.search_panel_shared import *


class SearchPanelBuildMixin(SearchPanelMixinBase):
    def _init_ui(self) -> None:
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

    def _create_airport_combo(
        self,
        default_code: str = "ICN",
        include_presets: bool = False,
    ) -> QComboBox:
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

    def _labeled_widget(self, label_text: str, widget: QWidget) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        vbox.addWidget(lbl)
        vbox.addWidget(widget)
        return container
