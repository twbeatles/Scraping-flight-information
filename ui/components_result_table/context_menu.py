"""Result table context menu and clipboard (SRP: row actions only)."""

from typing import Any

from PyQt6.QtWidgets import QApplication, QMenu


def show_context_menu(table: Any, pos) -> None:
    row = table.rowAt(pos.y())
    if row < 0:
        return

    menu = QMenu(table)

    # Add to favorites
    action_fav = menu.addAction("⭐ 즐겨찾기 추가")
    if action_fav is not None:
        action_fav.triggered.connect(lambda: table.favorite_requested.emit(row))

    menu.addSeparator()

    # Copy info
    action_copy = menu.addAction("📋 정보 복사")
    if action_copy is not None:
        action_copy.triggered.connect(lambda: copy_row_info(table, row))

    menu.addSeparator()

    # Export options (전체 결과)
    action_excel = menu.addAction("📊 Excel로 내보내기")
    if action_excel is not None:
        action_excel.triggered.connect(table.export_to_excel)

    action_csv = menu.addAction("📥 CSV로 내보내기")
    if action_csv is not None:
        action_csv.triggered.connect(table.export_to_csv)

    menu.exec(table.mapToGlobal(pos))


def copy_row_info(table: Any, row: int) -> None:
    flight = table.get_flight_at_row(row)
    if not flight:
        return
    info = f"{flight.airline} | {flight.price:,}원 | {flight.departure_time}→{flight.arrival_time}"
    clipboard = QApplication.clipboard()
    if clipboard is not None:
        clipboard.setText(info)
