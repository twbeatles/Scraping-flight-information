"""Filter state defaults, snapshot building, and time validation (SRP: state only)."""

from typing import Any, Dict, Tuple

DEFAULT_FILTERS: Dict[str, Any] = {
    "direct_only": False,
    "include_layover": True,
    "airline_category": "ALL",
    "max_stops": 3,
    "start_time": 0,
    "end_time": 24,
    "ret_start_time": 0,
    "ret_end_time": 24,
    "min_price": 0,
    "max_price": 9999 * 10000,
}


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
