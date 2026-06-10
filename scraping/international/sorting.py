"""Common result ordering helpers."""

from typing import Callable, List, Optional

from scraping.models import FlightResult


def sort_and_limit_results(
    results: List[FlightResult],
    max_results: int,
    log_func: Optional[Callable[[str], None]] = None,
) -> List[FlightResult]:
    """Sort results by price and cap the list when needed."""

    if not results:
        return []

    ordered = sorted(results, key=lambda item: item.price if item.price > 0 else float("inf"))
    if isinstance(max_results, int) and max_results > 0 and len(ordered) > max_results:
        if log_func:
            log_func(f"⚠️ 결과 {len(ordered)}개 중 상위 {max_results}개만 유지합니다.")
        return ordered[:max_results]
    return ordered
