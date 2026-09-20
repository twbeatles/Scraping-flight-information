"""Result table widget (SRP: widget lifecycle and row orchestration only).

Cell content, context menu, and export dialogs live in sibling modules.
"""

import logging
from PyQt6.QtWidgets import (
    QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem,
)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.components_result_table import context_menu, export_view
from ui.components_result_table.formatting import (
    build_airline_item,
    build_airport_item,
    build_baggage_item,
    build_price_item,
    build_seats_item,
    build_stops_item,
    compute_effective_prices,
    create_palette,
    format_arrival_text,
)
from ui.components_result_table.table_config import (
    COLUMN_LABELS,
    DEFAULT_ROW_HEIGHT,
    INITIAL_WIDTHS,
    MIN_SECTION_SIZE,
    PLACEHOLDER_ROW_HEIGHT,
    PLACEHOLDER_TEXT,
    RESULT_TABLE_STYLESHEET,
    STRETCH_COLUMN,
)


logger = logging.getLogger(__name__)


class ResultTable(QTableWidget):
    favorite_requested = pyqtSignal(int)  # row index

    def __init__(self):
        super().__init__()
        self.results_data = []  # Store flight results for access
        self._palette = create_palette()

        self.setColumnCount(len(COLUMN_LABELS))
        self.setHorizontalHeaderLabels(COLUMN_LABELS)

        # 열 너비 설정: 내용에 맞게 자동 조절 + 마지막 열 스트레치
        header = self.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for idx, width in enumerate(INITIAL_WIDTHS):
            if idx == STRETCH_COLUMN:
                if header is not None:
                    header.setSectionResizeMode(idx, QHeaderView.ResizeMode.Stretch)
            else:
                self.setColumnWidth(idx, width)

        # 최소 너비 설정 (HiDPI 대응)
        if header is not None:
            header.setMinimumSectionSize(MIN_SECTION_SIZE)

        v_header = self.verticalHeader()
        if v_header is not None:
            v_header.setVisible(False)
            v_header.setDefaultSectionSize(DEFAULT_ROW_HEIGHT)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)

        # 렌더링 시 재사용할 스타일 객체
        self._font_placeholder = self._palette["font_placeholder"]
        self._font_price = self._palette["font_price"]
        self._font_highlight = self._palette["font_highlight"]
        self._color_placeholder = self._palette["color_placeholder"]
        self._color_price_cheap = self._palette["color_price_cheap"]
        self._color_price_good = self._palette["color_price_good"]
        self._color_price_mid = self._palette["color_price_mid"]
        self._color_price_high = self._palette["color_price_high"]
        self._color_stops_direct = self._palette["color_stops_direct"]
        self._color_stops_layover = self._palette["color_stops_layover"]
        self._highlight_color = self._palette["highlight_color"]

        # 테이블 스타일
        self.setStyleSheet(RESULT_TABLE_STYLESHEET)

        # Enable context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def update_data(self, results):
        # 대량 업데이트 최적화
        self.setUpdatesEnabled(False)
        self.setSortingEnabled(False)
        self.results_data = results

        # Handle empty results - show placeholder
        if not results:
            self.setRowCount(1)
            placeholder_item = QTableWidgetItem(PLACEHOLDER_TEXT)
            placeholder_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder_item.setForeground(self._color_placeholder)
            placeholder_item.setFont(self._font_placeholder)
            self.setSpan(0, 0, 1, self.columnCount())
            self.setItem(0, 0, placeholder_item)
            self.setRowHeight(0, PLACEHOLDER_ROW_HEIGHT)
            self.setSortingEnabled(False)
            self.setUpdatesEnabled(True)
            return

        # Clear any previous span
        self.clearSpans()
        self.setRowCount(len(results))

        # Effective price (benefit-aware) for badge/color consistency with alerts.
        effective_prices, min_price, price_range = compute_effective_prices(results)

        for i, flight in enumerate(results):
            eff_price = effective_prices[i]
            self.setItem(i, 0, build_airline_item(flight, i))
            self.setItem(
                i, 1, build_price_item(flight, eff_price, min_price, price_range, self._palette)
            )

            # Outbound
            self._set_time_item(i, 2, flight.departure_time)
            arr_text = format_arrival_text(
                flight.arrival_time, getattr(flight, "arrival_day_offset", 0)
            )
            self._set_time_item(i, 3, arr_text)

            # Stops - highlight direct flights
            self.setItem(i, 4, build_stops_item(flight.stops, self._palette))

            # Inbound
            if hasattr(flight, 'is_round_trip') and flight.is_round_trip:
                self._set_time_item(i, 5, flight.return_departure_time)
                ret_arr = format_arrival_text(
                    flight.return_arrival_time,
                    getattr(flight, "return_arrival_day_offset", 0),
                )
                self._set_time_item(i, 6, ret_arr)
                self.setItem(i, 7, build_stops_item(flight.return_stops, self._palette))
            else:
                self.setItem(i, 5, QTableWidgetItem("-"))
                self.setItem(i, 6, QTableWidgetItem("-"))
                self.setItem(i, 7, QTableWidgetItem("-"))

            # Airports / baggage / seats / source
            self.setItem(i, 8, build_airport_item(flight))
            self.setItem(i, 9, build_baggage_item(flight))
            self.setItem(i, 10, build_seats_item(flight))
            self.setItem(i, 11, QTableWidgetItem(flight.source))

            # 최저가 행 배경색 강조 (혜택 반영 비교가 기준)
            if eff_price == min_price:
                for col in range(self.columnCount()):
                    item = self.item(i, col)
                    if item:
                        item.setBackground(self._highlight_color)
                        item.setFont(self._font_highlight)

        self.setSortingEnabled(True)
        self.setUpdatesEnabled(True)  # 렌더링 다시 활성화

    def _set_time_item(self, row, col, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row, col, item)

    def _show_context_menu(self, pos):
        context_menu.show_context_menu(self, pos)

    def _copy_row_info(self, row):
        context_menu.copy_row_info(self, row)

    def export_to_excel(self):
        export_view.export_to_excel(self)

    def export_to_csv(self):
        export_view.export_to_csv(self)

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
