"""Result table cell formatting (SRP: item text/color/tooltip building only)."""

import re
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


# 정렬 전용 숫자 키. 표시 문자열(🏆, 쉼표, "원")과 무관하게 숫자 크기로 정렬한다.
SORT_ROLE = Qt.ItemDataRole.UserRole + 2
SORT_LAST = float("inf")


class SortableItem(QTableWidgetItem):
    """SORT_ROLE 숫자 키로 비교하는 셀. 키가 없으면 문자열 비교로 내려간다."""

    def __lt__(self, other: QTableWidgetItem) -> bool:
        left = self.data(SORT_ROLE)
        right = other.data(SORT_ROLE)
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return left < right
        return super().__lt__(other)


def price_sort_key(price: int) -> float:
    """가격 미확인(0 이하)은 오름차순에서 맨 뒤로 보낸다."""

    return float(price) if price > 0 else SORT_LAST


def duration_to_minutes(text: str) -> int:
    """'02시간 30분', '2h 30m', '02:30', '150' 형태를 분으로 변환. 해석 불가면 0."""

    raw = str(text or "").strip()
    if not raw:
        return 0
    if raw.isdigit():
        return int(raw)
    clock = re.fullmatch(r"(\d{1,2}):(\d{2})", raw)
    if clock:
        return int(clock.group(1)) * 60 + int(clock.group(2))
    hours = re.search(r"(\d+)\s*(?:시간|h)", raw, re.IGNORECASE)
    minutes = re.search(r"(\d+)\s*(?:분|m)", raw, re.IGNORECASE)
    return (int(hours.group(1)) * 60 if hours else 0) + (int(minutes.group(1)) if minutes else 0)


def compute_effective_prices(results: List[Any]) -> Tuple[List[int], int, int]:
    effective_prices = [effective_flight_price(r) for r in results]
    known_prices = [p for p in effective_prices if p > 0] or effective_prices
    min_price = min(known_prices)
    max_price = max(known_prices)
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
    base_price = int(getattr(flight, "price", 0) or 0)
    outbound_price = int(getattr(flight, "outbound_price", 0) or 0)
    return_price = int(getattr(flight, "return_price", 0) or 0)
    # 비교가(혜택 반영)를 주 표시로 하고, 기본가·구간가는 보조로 붙인다.
    price_text = f"{badge}{eff_price:,}원"
    if eff_price != base_price and base_price > 0:
        price_text = f"{price_text} (기본 {base_price:,})"
    if outbound_price > 0:
        price_text = f"{price_text} · {outbound_price:,}+{return_price:,}"

    price_item = SortableItem(price_text)
    price_item.setData(Qt.ItemDataRole.UserRole, eff_price)
    price_item.setData(SORT_ROLE, price_sort_key(eff_price))
    price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    tooltip_lines = [
        f"비교가(혜택 반영, 정렬·필터 기준): {eff_price:,}원",
        f"기본가: {flight.price:,}원",
    ]
    if hasattr(flight, 'outbound_price') and flight.outbound_price > 0:
        tooltip_lines.append(
            f"구성: {flight.outbound_price:,}원 + {flight.return_price:,}원"
        )
    if getattr(flight, 'benefit_price', 0) > 0:
        tooltip_lines.append(f"혜택가: {flight.benefit_price:,}원")
    if getattr(flight, 'benefit_label', ''):
        tooltip_lines.append(f"혜택 정보: {flight.benefit_label}")
    if getattr(flight, "arrival_day_offset", 0):
        tooltip_lines.append(f"도착일 +{flight.arrival_day_offset}")
    price_item.setToolTip("\n".join(tooltip_lines))

    ratio = (eff_price - min_price) / price_range if price_range else 0
    price_item.setForeground(price_color_for(ratio, palette))
    price_item.setFont(palette["font_price"])
    return price_item


def build_stops_item(stops: int, palette: Dict[str, Any]) -> QTableWidgetItem:
    stops_item = SortableItem("✈️ 직항" if not stops else f"{stops}회 경유")
    stops_item.setData(SORT_ROLE, int(stops or 0))
    if not stops:
        stops_item.setForeground(palette["color_stops_direct"])
    else:
        stops_item.setForeground(palette["color_stops_layover"])
    return stops_item


def build_empty_item() -> QTableWidgetItem:
    """편도 결과의 오는편 칸. 정렬 시 항상 뒤로 간다."""

    item = SortableItem("-")
    item.setData(SORT_ROLE, SORT_LAST)
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return item


def build_duration_item(flight: Any) -> QTableWidgetItem:
    outbound = str(getattr(flight, "duration", "") or "")
    returning = ""
    if getattr(flight, "is_round_trip", False):
        returning = str(getattr(flight, "return_duration", "") or "")
    if outbound and returning:
        text = f"{outbound} / {returning}"
    else:
        text = outbound or returning or "-"
    item = SortableItem(text)
    minutes = duration_to_minutes(outbound) + duration_to_minutes(returning)
    item.setData(SORT_ROLE, minutes if minutes > 0 else SORT_LAST)
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    if outbound and returning:
        item.setToolTip(f"가는편: {outbound}\n오는편: {returning}")
    return item


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
    seats_item = SortableItem(seats_text)
    seats_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    seats_item.setData(Qt.ItemDataRole.UserRole, seats)
    seats_item.setData(SORT_ROLE, seats if seats > 0 else SORT_LAST)
    return seats_item
