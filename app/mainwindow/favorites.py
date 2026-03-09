"""FavoritesMixin methods extracted from MainWindow."""

from app.mainwindow.shared import *
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.main_window import MainWindow


class FavoritesMixin:
    def _create_favorites_tab(self: Any):
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
        header = self.fav_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
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
    def _refresh_favorites(self: Any):
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
    def _add_to_favorites(self: Any, row):
        flight = self.table.get_flight_at_row(row)
        if not flight:
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
            'return_airline': getattr(flight, 'return_airline', ''),
            'return_departure_time': getattr(flight, 'return_departure_time', ''),
            'return_arrival_time': getattr(flight, 'return_arrival_time', ''),
            'return_stops': getattr(flight, 'return_stops', 0),
            'is_round_trip': bool(getattr(flight, 'is_round_trip', False)),
            'outbound_price': getattr(flight, 'outbound_price', 0),
            'return_price': getattr(flight, 'return_price', 0),
        }

        # Check if already favorited
        if self.db.is_favorite_by_entry(flight_data):
            QMessageBox.information(self, "알림", "이미 즐겨찾기에 추가된 항공권입니다.")
            return
        
        # Ask for note
        note, ok = QInputDialog.getText(self, "즐겨찾기 메모", "메모를 입력하세요 (선택):")
        if not ok:
            return

        flight_data['note'] = note
        
        self.db.add_favorite(flight_data, self.current_search_params)
        self._refresh_favorites()
        self.log_viewer.append_log(f"⭐ 즐겨찾기 추가: {flight.airline} {flight.price:,}원")
        QMessageBox.information(self, "완료", "즐겨찾기에 추가되었습니다!")
    def _delete_selected_favorite(self: Any):
        row = self.fav_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "선택 오류", "삭제할 항목을 선택하세요.")
            return
        
        id_item = self.fav_table.item(row, 0)
        if id_item is None:
            QMessageBox.warning(self, "선택 오류", "선택된 즐겨찾기 정보를 읽을 수 없습니다.")
            return
        fav_id = int(id_item.text())
        reply = QMessageBox.question(
            self, "삭제 확인", "선택한 즐겨찾기를 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.remove_favorite(fav_id)
            self._refresh_favorites()
            self.log_viewer.append_log("즐겨찾기 삭제됨")

    # --- Export Functions ---



