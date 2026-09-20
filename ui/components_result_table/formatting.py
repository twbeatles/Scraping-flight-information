"""Result table cell formatting (SRP: item text/color/tooltip building only)."""

from typing import Any, Dict, List, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QTableWidgetItem

from scraping.models import effective_flight_price


def create_palette() -> Dict[str, Any]:
    return {
        "font_placeholder": QFont("Pretendard", 12),
        "font_price": QFont("Pretendard", 11, QFont.Weight.Bold),
        "font_highlight": QFont("Pretendard", 11, QFont.Weight.Bold),
        "color_placeholder": QColor("#64748b"),
        "color_price_cheap": QColor("#22c55e"),
        "color_price_good": QColor("#4cc9f0"),
        "color_price_mid": QColor("#f59e0b"),
        "color_price_high": QColor("#ef4444"),
        "color_stops_direct": QColor("#22c55e"),
        "color_stops_layover": QColor("#94a3b8"),
        "highlight_color": QColor(34, 197, 94, 40),
    }


def compute_effective_prices(results: List[Any]) -> Tuple[List[int], int, int]:
    effective_prices = [effective_flight_price(r) for r in results]
    min_price = min(effective_prices)
    max_price = max(effective_prices)
    price_range = max_price - min_price if max_price > min_price else 1
    return effective_prices, min_price, price_range


def price_color_for(ratio: float, palette: Dict[str, Any]) -> QColor:
    if ratio < 0.2:
        return palette["color_price_cheap"]  # Green - cheapest
    if ratio < 0.5:
        return palette["color_price_good"]  # Cyan - good
    if ratio < 0.8:
        return palette["color_price_mid"]  # Orange - moderate
    return palette["color_price_high"]  # Red - expensive


def build_airline_item(flight: Any, index: int) -> QTableWidgetItem:
    airline_str = flight.airline
    if hasattr(flight, 'return_airline') and flight.return_airline and flight.airline != flight.return_airline:
        airline_str = f"{flight.airline} + {flight.return_airline}"

    airline_item = QTableWidgetItem(airline_str)
    airline_item.setData(Qt.ItemDataRole.UserRole + 1, index)
    airline_tips = []
    if hasattr(flight, 'return_airline') and flight.return_airline:
        airline_tips.append(f"가는편: {flight.airline}")
        airline_tips.append(f"오는편: {flight.return_airline}")
    if getattr(flight, "flight_number", ""):
        airline_tips.append(f"편명: {flight.flight_number}")
    if getattr(flight, "recommendation_tag", ""):
        airline_tips.append(f"추천: {flight.recommendation_tag}")
    if airline_tips:
        airline_item.setToolTip("\n".join(airline_tips))
    return airline_item


def build_price_item(
    flight: Any, eff_price: int, min_price: int, price_range: int, palette: Dict[str, Any]
) -> QTableWidgetItem:
    badge = "🏆 " if eff_price == min_price else ""
    if hasattr(flight, 'outbound_price') and flight.outbound_price > 0:
        price_text = f"{badge}{flight.price:,}원 ({flight.outbound_price:,}+{flight.return_price:,})"
    else:
        price_text = f"{badge}{flight.price:,}원"
    if getattr(flight, "benefit_price", 0) > 0 and flight.benefit_price != flight.price:
        price_text = f"{price_text} / 혜택 {flight.benefit_price:,}"

    price_item = QTableWidgetItem(price_text)
    price_item.setData(Qt.ItemDataRole.UserRole, eff_price)
    price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    tooltip_lines = [
        f"기본가: {flight.price:,}원",
        f"비교가(혜택 반영): {eff_price:,}원",
    ]
    if hasattr(flight, 'outbound_price') and flight.outbound_price > 0:
        tooltip_lines.append(
            f"구성: {flight.outbound_price:,}원 + {flight.return_price:,}원"
        )
    if getattr(flight, 'benefit_price', 0) > 0:
        tooltip_lines.append(f"혜택가: {flight.benefit_price:,}원")
    if getattr(flight, 'benefit_label', ''):
        tooltip_lines.append(f"혜택 정보: {flight.benefit_label}")
    if getattr(flight, "duration", ""):
        tooltip_lines.append(f"소요시간: {flight.duration}")
    if getattr(flight, "arrival_day_offset", 0):
        tooltip_lines.append(f"도착일 +{flight.arrival_day_offset}")
    price_item.setToolTip("\n".join(tooltip_lines))

    ratio = (eff_price - min_price) / price_range if price_range else 0
    price_item.setForeground(price_color_for(ratio, palette))
    price_item.setFont(palette["font_price"])
    return price_item


def build_stops_item(stops: int, palette: Dict[str, Any]) -> QTableWidgetItem:
    stops_item = QTableWidgetItem("✈️ 직항" if not stops else f"{stops}회 경유")
    if not stops:
        stops_item.setForeground(palette["color_stops_direct"])
    else:
        stops_item.setForeground(palette["color_stops_layover"])
    return stops_item


def format_arrival_text(base: str, day_offset: int) -> str:
    if day_offset:
        return f"{base}(+{day_offset})"
    return base


def build_airport_item(flight: Any) -> QTableWidgetItem:
    dep_ap = getattr(flight, "departure_airport", "") or ""
    arr_ap = getattr(flight, "arrival_airport", "") or ""
    ret_dep_ap = getattr(flight, "return_departure_airport", "") or ""
    ret_arr_ap = getattr(flight, "return_arrival_airport", "") or ""
    if dep_ap or arr_ap:
        airport_text = f"{dep_ap or '?'}→{arr_ap or '?'}"
        if getattr(flight, "is_round_trip", False) and (ret_dep_ap or ret_arr_ap):
            airport_text = f"{airport_text} / {ret_dep_ap or '?'}→{ret_arr_ap or '?'}"
    else:
        airport_text = "-"
    airport_item = QTableWidgetItem(airport_text)
    airport_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return airport_item


def build_baggage_item(flight: Any) -> QTableWidgetItem:
    bag = getattr(flight, "baggage", "") or ""
    ret_bag = getattr(flight, "return_baggage", "") or ""
    if bag and ret_bag and bag != ret_bag:
        bag_text = f"{bag} / {ret_bag}"
    else:
        bag_text = bag or ret_bag or "-"
    bag_item = QTableWidgetItem(bag_text)
    bag_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return bag_item


def build_seats_item(flight: Any) -> QTableWidgetItem:
    seats = int(getattr(flight, "seat_availability", 0) or 0)
    seats_text = str(seats) if seats > 0 else "-"
    seats_item = QTableWidgetItem(seats_text)
    seats_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    seats_item.setData(Qt.ItemDataRole.UserRole, seats)
    return seats_item
