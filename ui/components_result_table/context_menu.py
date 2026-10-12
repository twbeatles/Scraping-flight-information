"""Result table context menu and clipboard (SRP: row actions only)."""

from typing import Any

from PyQt6.QtWidgets import QApplication, QMenu

from scraping.models import effective_flight_price


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


def format_row_info(flight: Any) -> str:
    """행 복사용 한 줄 요약. 비교가를 먼저 쓰고 기본가가 다르면 함께 적는다."""

    eff_price = effective_flight_price(flight)
    price_text = f"{eff_price:,}원"
    if eff_price != flight.price and flight.price > 0:
        price_text = f"{price_text} (기본 {flight.price:,}원)"

    airline = flight.airline
    return_airline = getattr(flight, "return_airline", "") or ""
    if return_airline and return_airline != airline:
        airline = f"{airline} + {return_airline}"

    parts = [airline, price_text, f"가는편 {flight.departure_time}→{flight.arrival_time}"]
    if getattr(flight, "is_round_trip", False):
        parts.append(f"오는편 {flight.return_departure_time}→{flight.return_arrival_time}")
    return " | ".join(parts)


def copy_row_info(table: Any, row: int) -> None:
    flight = table.get_flight_at_row(row)
    if not flight:
        return
    clipboard = QApplication.clipboard()
    if clipboard is not None:
        clipboard.setText(format_row_info(flight))
