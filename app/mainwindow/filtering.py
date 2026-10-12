"""FilteringMixin methods extracted from MainWindow."""

from app.mainwindow.shared import (
    MAX_PRICE_FILTER,
    config,
    logger,
    scraper_config,
    time,
)
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from scraping.models import effective_flight_price
from ui.components_filter_panel.state import UNLIMITED_STOPS, describe_stops_filter
from ui.components_result_table.table_config import FILTERED_EMPTY_TEXT

if TYPE_CHECKING:
    from app.main_window import MainWindow


AIRLINE_CATEGORY_LABELS = {"ALL": "전체", "LCC": "LCC", "FSC": "FSC"}
CABIN_LABELS = {"ECONOMY": "이코노미", "BUSINESS": "비즈니스", "FIRST": "일등석"}


def _format_short_date(value: Any) -> str:
    text = str(value or "")
    if len(text) == 8 and text.isdigit():
        return f"{int(text[4:6])}/{int(text[6:8])}"
    return text


def lowest_effective_price(flights: List[Any]) -> int:
    """가격이 확인된 항공편 중 최저 비교가. 없으면 0."""

    prices = [p for p in (effective_flight_price(f) for f in flights) if p > 0]
    return min(prices) if prices else 0


def build_result_summary(
    params: Optional[Dict[str, Any]],
    shown: List[Any],
    total: int,
    *,
    truncated: bool = False,
) -> str:
    """결과 표 위 요약 문구: 조회 조건 · 표시/전체 건수 · 최저가 · 누락 경고."""

    params = params or {}
    parts: List[str] = []

    origin = str(params.get("origin") or "")
    dest = str(params.get("dest") or "")
    if origin and dest:
        parts.append(f"{origin} → {dest}")

    dep = _format_short_date(params.get("dep"))
    ret = _format_short_date(params.get("ret"))
    if dep:
        parts.append(f"{dep} ~ {ret} 왕복" if ret else f"{dep} 편도")

    try:
        adults = int(params.get("adults") or 0)
        child = int(params.get("child") or 0)
        infant = int(params.get("infant") or 0)
    except (TypeError, ValueError):
        adults = child = infant = 0
    if adults:
        pax = f"성인 {adults}"
        if child:
            pax += f" · 소아 {child}"
        if infant:
            pax += f" · 유아 {infant}"
        parts.append(pax)

    cabin = CABIN_LABELS.get(str(params.get("cabin_class") or "").upper())
    if cabin and parts:
        parts.append(cabin)

    if total <= 0:
        parts.append("결과 없음")
    elif len(shown) == total:
        parts.append(f"{total}건")
    else:
        parts.append(f"{len(shown)}건 표시 / 전체 {total}건")

    best = lowest_effective_price(shown)
    if best > 0:
        parts.append(f"최저 {best:,}원 (혜택 반영)")

    text = "  |  ".join(parts)
    if truncated:
        text += "  |  ⚠️ 조회 상한에 도달해 일부 결과가 빠졌을 수 있습니다"
    return text


class FilteringMixin:
    def _schedule_filter_apply(self: Any, filters):
        """연속 필터 이벤트를 디바운스로 합쳐 마지막 변경만 적용."""
        self._pending_filter = filters
        self._filter_apply_timer.start(scraper_config.FILTER_DEBOUNCE_MS)
    def _run_scheduled_filter_apply(self: Any):
        if self._pending_filter is None:
            return
        filters = self._pending_filter
        self._pending_filter = None
        self._apply_filter(filters)
    def _append_filter_log(self: Any, message: str):
        """동일 필터 로그의 짧은 간격 중복 출력을 억제."""
        now = time.monotonic()
        if message == self._last_filter_log_msg and (now - self._last_filter_log_ts) < 1.0:
            return
        self._last_filter_log_msg = message
        self._last_filter_log_ts = now
        self.log_viewer.append_log(message)
    def _update_result_summary(self: Any, shown: List[Any]):
        label = getattr(self, "result_summary_label", None)
        if label is None:
            return
        label.setText(
            build_result_summary(
                getattr(self, "current_search_params", None),
                shown,
                len(getattr(self, "all_results", None) or []),
                truncated=bool(getattr(self, "_last_search_truncated", False)),
            )
        )

    def _apply_filter(self: Any, filters=None):
        if filters is None:
            filters = self.filter_panel.get_current_filters()
            
        if not self.all_results:
            return
            
        direct_only = filters.get("direct_only", False)
        include_layover = filters.get("include_layover", True)
        airline_category = filters.get("airline_category", "ALL")
        max_stops = filters.get("max_stops", UNLIMITED_STOPS)
        
        # Outbound Time Filter
        start_h = filters.get("start_time", 0)
        end_h = filters.get("end_time", 24)
        
        # Inbound Time Filter
        ret_start_h = filters.get("ret_start_time", 0)
        ret_end_h = filters.get("ret_end_time", 24)
        
        # 만약 필터 패널에서 값을 안 줬다면(초기 로딩 등) 설정값 사용
        if "start_time" not in filters:
            pref_time = self.prefs.get_preferred_time()
            start_h = pref_time.get("departure_start", 0)
            end_h = pref_time.get("departure_end", 24)
            # 오는편 선호 시간은 설정에 없으므로 기본값(0-24) 유지
            
        filtered = []
        for f in self.all_results:
            # 1. Stops Filter
            if direct_only and f.stops > 0:
                continue
            if not include_layover and f.stops > 0:
                continue
            if f.stops > max_stops:
                continue
            
            # 2. Airline Category Filter
            if airline_category != "ALL":
                category = config.get_airline_category(f.airline)
                if category != airline_category:
                    continue
            
            # 3. Time Filter (Outbound)
            try:
                if ':' in f.departure_time:
                    dep_h = int(f.departure_time.split(':')[0])
                    if not (start_h <= dep_h <= end_h):  # <= 로 변경하여 종료시간 포함
                        continue
            except Exception as e:
                logger.debug(f"Time filter parsing error: {e}")
            
            # 4. Time Filter (Inbound) - Only for round trips
            if f.is_round_trip and hasattr(f, 'return_departure_time') and f.return_departure_time:
                try:
                    if ':' in f.return_departure_time:
                        ret_dep_h = int(f.return_departure_time.split(':')[0])
                        if not (ret_start_h <= ret_dep_h <= ret_end_h):  # <= 로 변경
                            continue
                except Exception as e:
                    logger.debug(f"Return time filter parsing error: {e}")
            
            # 5. Price Range Filter - 표의 가격 칸·최저가 강조와 같은 비교가(혜택 반영) 기준
            compare_price = effective_flight_price(f)
            min_price = filters.get("min_price", 0)
            max_price = filters.get("max_price", MAX_PRICE_FILTER)
            if compare_price < min_price:
                continue
            if max_price < MAX_PRICE_FILTER:
                if compare_price > max_price:
                    continue
                
            filtered.append(f)
            
        # 가격 미확인(0)은 뒤로, 나머지는 비교가 오름차순
        filtered.sort(key=lambda item: effective_flight_price(item) or float("inf"))

        if hasattr(self.table, "set_empty_message"):
            self.table.set_empty_message(
                None if filtered else FILTERED_EMPTY_TEXT.format(total=len(self.all_results))
            )
        self.table.update_data(filtered)
        self._update_result_summary(filtered)
        
        # 상태 메시지에 가격 범위 표시
        price_msg = ""
        min_p = filters.get("min_price", 0)
        max_p = filters.get("max_price", MAX_PRICE_FILTER)
        if min_p > 0 or max_p < MAX_PRICE_FILTER:
            price_msg = f" | 가격: {min_p//10000}~{max_p//10000}만원"
        
        airline_label = AIRLINE_CATEGORY_LABELS.get(airline_category, airline_category)
        stops_label = describe_stops_filter(direct_only, include_layover, max_stops)
        msg = (
            f"표시 {len(filtered)}건 / 전체 {len(self.all_results)}건"
            f" | 경유: {stops_label} | 가는편 출발: {start_h}~{end_h}시"
            f" | 항공사: {airline_label}{price_msg}"
        )
        status_bar = self.statusBar()
        if status_bar is not None:
            status_bar.showMessage(msg)
        self._append_filter_log(msg)

    # --- History Tab Methods ---



