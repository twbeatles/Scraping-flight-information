"""Filter panel widget (SRP: widget assembly and signal wiring only).

State defaults/snapshots and time-range validation live in `state.py`.
"""

import logging
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)
from PySide6.QtCore import Signal

from ui.components_filter_panel.state import (
    STOPS_OPTIONS,
    UNLIMITED_STOPS,
    adjust_time_range,
    build_filter_dict,
    stops_limit_to_flags,
)
from ui.components_primitives import NoWheelSpinBox, NoWheelComboBox


logger = logging.getLogger(__name__)


class FilterPanel(QFrame):
    filter_changed = Signal(dict)  # {direct_only, include_layover, airline_category, max_stops}

    def __init__(self):
        super().__init__()
        self.setObjectName("card")

        # 메인 레이아웃: 세로 방향 (2줄)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(12)

        # === 첫 번째 줄: 기본 필터 ===
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        # Filter label with icon
        filter_label = QLabel("🎯 필터")
        filter_label.setStyleSheet("font-weight: 700; font-size: 15px;")
        row1.addWidget(filter_label)

        # Stops filter - 직항/경유 한도를 하나의 선택으로 정한다
        stops_label = QLabel("경유:")
        stops_label.setStyleSheet("font-weight: 600; font-size: 14px;")
        row1.addWidget(stops_label)
        self.cb_stops = NoWheelComboBox()
        self.cb_stops.setToolTip("허용할 최대 경유 횟수 (가는편·오는편 각각 적용)")
        for label, limit in STOPS_OPTIONS:
            self.cb_stops.addItem(label, limit)
        self.cb_stops.setMinimumWidth(120)
        self.cb_stops.setStyleSheet("font-size: 13px; padding: 4px;")
        self.cb_stops.currentIndexChanged.connect(self._emit_filter)
        row1.addWidget(self.cb_stops)

        row1.addWidget(self._create_separator())

        # Airline Category Filter
        airline_label = QLabel("항공사:")
        airline_label.setStyleSheet("font-weight: 600; font-size: 14px;")
        row1.addWidget(airline_label)
        self.cb_airline_category = NoWheelComboBox()
        self.cb_airline_category.setToolTip("LCC: 저비용항공사 (제주항공, 진에어 등)\nFSC: 일반항공사 (대한항공, 아시아나)")
        self.cb_airline_category.addItem("전체", "ALL")
        self.cb_airline_category.addItem("🏷️ LCC (저비용)", "LCC")
        self.cb_airline_category.addItem("✈️ FSC (일반)", "FSC")
        self.cb_airline_category.setMinimumWidth(140)
        self.cb_airline_category.setStyleSheet("font-size: 13px; padding: 4px;")
        self.cb_airline_category.currentIndexChanged.connect(self._emit_filter)
        row1.addWidget(self.cb_airline_category)

        row1.addStretch()

        # Reset Button
        btn_reset = QPushButton("↺ 초기화")
        btn_reset.setToolTip("필터 초기화")
        btn_reset.setObjectName("tool_btn")
        btn_reset.setStyleSheet("font-size: 13px; padding: 6px 12px;")
        btn_reset.clicked.connect(self._reset_filters)
        row1.addWidget(btn_reset)

        main_layout.addLayout(row1)

        # === 두 번째 줄: 상세 필터 ===
        row2 = QHBoxLayout()
        row2.setSpacing(12)

        # 공통 스타일
        spin_style = """
            QSpinBox {
                min-width: 70px;
                min-height: 32px;
                font-size: 13px;
                padding: 4px 6px;
                font-weight: 600;
                border-radius: 8px;
            }
        """

        # Time Filter (Outbound) with icon
        lbl_out = QLabel("🛫 가는편:")
        lbl_out.setStyleSheet("font-weight: 700; color: #22d3ee; font-size: 13px;")
        row2.addWidget(lbl_out)

        self.spin_start_time = NoWheelSpinBox()
        self.spin_start_time.setRange(0, 23)
        self.spin_start_time.setSuffix("시")
        self.spin_start_time.setStyleSheet(spin_style)
        self.spin_start_time.valueChanged.connect(self._on_time_changed)
        row2.addWidget(self.spin_start_time)

        tilde1 = QLabel("~")
        tilde1.setStyleSheet("font-size: 14px; color: #94a3b8;")
        row2.addWidget(tilde1)

        self.spin_end_time = NoWheelSpinBox()
        self.spin_end_time.setRange(1, 24)
        self.spin_end_time.setValue(24)
        self.spin_end_time.setSuffix("시")
        self.spin_end_time.setStyleSheet(spin_style)
        self.spin_end_time.valueChanged.connect(self._on_time_changed)
        row2.addWidget(self.spin_end_time)

        row2.addWidget(self._create_separator())

        # Time Filter (Inbound) with icon
        lbl_in = QLabel("🛬 오는편:")
        lbl_in.setStyleSheet("font-weight: 700; color: #a78bfa; font-size: 13px;")
        row2.addWidget(lbl_in)

        self.spin_ret_start = NoWheelSpinBox()
        self.spin_ret_start.setRange(0, 23)
        self.spin_ret_start.setSuffix("시")
        self.spin_ret_start.setStyleSheet(spin_style)
        self.spin_ret_start.valueChanged.connect(self._on_time_changed)
        row2.addWidget(self.spin_ret_start)

        tilde2 = QLabel("~")
        tilde2.setStyleSheet("font-size: 14px; color: #94a3b8;")
        row2.addWidget(tilde2)

        self.spin_ret_end = NoWheelSpinBox()
        self.spin_ret_end.setRange(1, 24)
        self.spin_ret_end.setValue(24)
        self.spin_ret_end.setSuffix("시")
        self.spin_ret_end.setStyleSheet(spin_style)
        self.spin_ret_end.valueChanged.connect(self._on_time_changed)
        row2.addWidget(self.spin_ret_end)

        row2.addWidget(self._create_separator())

        # Price Range Filter with icon
        lbl_price = QLabel("💰 가격:")
        lbl_price.setStyleSheet("font-weight: 700; color: #4ade80; font-size: 13px;")
        row2.addWidget(lbl_price)
        self.spin_min_price = NoWheelSpinBox()
        self.spin_min_price.setRange(0, 9999)
        self.spin_min_price.setValue(0)
        self.spin_min_price.setSuffix("만")
        self.spin_min_price.setStyleSheet(spin_style)
        self.spin_min_price.setToolTip("최소 가격 (만원 단위, 혜택 반영 비교가 기준)")
        self.spin_min_price.valueChanged.connect(self._emit_filter)
        row2.addWidget(self.spin_min_price)

        tilde3 = QLabel("~")
        tilde3.setStyleSheet("font-size: 14px; color: #94a3b8;")
        row2.addWidget(tilde3)

        self.spin_max_price = NoWheelSpinBox()
        self.spin_max_price.setRange(0, 9999)
        self.spin_max_price.setValue(9999)
        self.spin_max_price.setSuffix("만")
        self.spin_max_price.setStyleSheet(spin_style)
        self.spin_max_price.setToolTip("최대 가격 (만원 단위, 혜택 반영 비교가 기준, 9999=무제한)")
        self.spin_max_price.valueChanged.connect(self._emit_filter)
        row2.addWidget(self.spin_max_price)

        row2.addStretch()

        main_layout.addLayout(row2)

    def _create_separator(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #30475e;")
        return sep

    def _on_time_changed(self):
        """시간 변경 시 유효성 검사 후 시그널 발생

        무한 재귀 방지를 위해 값 변경 시 시그널을 일시적으로 차단합니다.
        """
        # 가는편
        start = self.spin_start_time.value()
        end = self.spin_end_time.value()
        fixed_start, fixed_end = adjust_time_range(
            start, end, sender_is_start=(self.sender() == self.spin_start_time)
        )
        if (fixed_start, fixed_end) != (start, end):
            self.spin_start_time.blockSignals(True)
            self.spin_end_time.blockSignals(True)
            self.spin_start_time.setValue(fixed_start)
            self.spin_end_time.setValue(fixed_end)
            self.spin_start_time.blockSignals(False)
            self.spin_end_time.blockSignals(False)

        # 오는편
        r_start = self.spin_ret_start.value()
        r_end = self.spin_ret_end.value()
        fixed_r_start, fixed_r_end = adjust_time_range(
            r_start, r_end, sender_is_start=(self.sender() == self.spin_ret_start)
        )
        if (fixed_r_start, fixed_r_end) != (r_start, r_end):
            self.spin_ret_start.blockSignals(True)
            self.spin_ret_end.blockSignals(True)
            self.spin_ret_start.setValue(fixed_r_start)
            self.spin_ret_end.setValue(fixed_r_end)
            self.spin_ret_start.blockSignals(False)
            self.spin_ret_end.blockSignals(False)

        self._emit_filter()

    def _emit_filter(self):
        filters = self.get_current_filters()
        self.filter_changed.emit(filters)

    def _reset_filters(self):
        """필터 초기화 - 시그널 차단으로 다중 emit 방지"""
        # 모든 필터 위젯의 시그널 차단
        widgets = [
            self.cb_stops, self.cb_airline_category,
            self.spin_start_time, self.spin_end_time,
            self.spin_ret_start, self.spin_ret_end, self.spin_min_price, self.spin_max_price
        ]
        for w in widgets:
            w.blockSignals(True)

        # 값 초기화
        self.cb_stops.setCurrentIndex(0)  # 전체
        self.cb_airline_category.setCurrentIndex(0)  # ALL
        self.spin_start_time.setValue(0)
        self.spin_end_time.setValue(24)
        self.spin_ret_start.setValue(0)
        self.spin_ret_end.setValue(24)
        self.spin_min_price.setValue(0)
        self.spin_max_price.setValue(9999)

        # 시그널 재활성화
        for w in widgets:
            w.blockSignals(False)

        # 마지막에 한 번만 emit
        self._emit_filter()

    def set_departure_time_range(self, start: int, end: int) -> None:
        """가는편 출발 시간대를 시그널 없이 설정한다 (설정의 선호 시간 초기화용)."""
        start = max(0, min(int(start), 23))
        end = max(start + 1, min(int(end), 24))
        for spin, value in ((self.spin_start_time, start), (self.spin_end_time, end)):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)

    def get_current_filters(self):
        stops_data = self.cb_stops.currentData()
        max_stops = UNLIMITED_STOPS if stops_data is None else int(stops_data)
        direct_only, include_layover = stops_limit_to_flags(max_stops)
        return build_filter_dict(
            direct_only=direct_only,
            include_layover=include_layover,
            airline_category=self.cb_airline_category.currentData(),
            max_stops=max_stops,
            start_time=self.spin_start_time.value(),
            end_time=self.spin_end_time.value(),
            ret_start_time=self.spin_ret_start.value(),
            ret_end_time=self.spin_ret_end.value(),
            min_price_manwon=self.spin_min_price.value(),
            max_price_manwon=self.spin_max_price.value(),
        )
