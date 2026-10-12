"""Filter state defaults, snapshot building, and time validation (SRP: state only)."""

from typing import Any, Dict, Tuple

# "전체" 선택 시 max_stops 값. 경유 횟수로 걸러내지 않는다는 뜻이다.
UNLIMITED_STOPS = 99

# 경유 콤보 선택지: (표시 문구, 허용 최대 경유 횟수)
STOPS_OPTIONS: Tuple[Tuple[str, int], ...] = (
    ("전체", UNLIMITED_STOPS),
    ("✈️ 직항만", 0),
    ("1회 이하", 1),
    ("2회 이하", 2),
)

DEFAULT_FILTERS: Dict[str, Any] = {
    "direct_only": False,
    "include_layover": True,
    "airline_category": "ALL",
    "max_stops": UNLIMITED_STOPS,
    "start_time": 0,
    "end_time": 24,
    "ret_start_time": 0,
    "ret_end_time": 24,
    "min_price": 0,
    "max_price": 9999 * 10000,
}


def stops_limit_to_flags(max_stops: int) -> Tuple[bool, bool]:
    """경유 한도 하나에서 기존 필터 키 (direct_only, include_layover)를 파생한다."""

    direct_only = max_stops <= 0
    return direct_only, not direct_only


def describe_stops_filter(direct_only: bool, include_layover: bool, max_stops: int) -> str:
    if direct_only or not include_layover or max_stops <= 0:
        return "직항만"
    if max_stops >= UNLIMITED_STOPS:
        return "전체"
    return f"{max_stops}회 이하"


def build_filter_dict(
    *,
    direct_only: bool,
    include_layover: bool,
    airline_category: str,
    max_stops: int,
    start_time: int,
    end_time: int,
    ret_start_time: int,
    ret_end_time: int,
    min_price_manwon: int,
    max_price_manwon: int,
) -> Dict[str, Any]:
    return {
        "direct_only": direct_only,
        "include_layover": include_layover,
        "airline_category": airline_category,
        "max_stops": max_stops,
        "start_time": start_time,
        "end_time": end_time,
        "ret_start_time": ret_start_time,
        "ret_end_time": ret_end_time,
        "min_price": min_price_manwon * 10000,  # 만원 -> 원
        "max_price": max_price_manwon * 10000,  # 만원 -> 원
    }


def adjust_time_range(start: int, end: int, sender_is_start: bool) -> Tuple[int, int]:
    """Clamp an invalid (start >= end) time range by moving the edited side.

    Returns the corrected (start, end) pair; unchanged when already valid.
    """

    if start < end:
        return start, end
    if sender_is_start:
        return start, min(start + 1, 24)
    return max(end - 1, 0), end
