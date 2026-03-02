"""FilteringMixin methods extracted from MainWindow."""

from app.mainwindow.shared import *


class FilteringMixin:
    def _schedule_filter_apply(self, filters):
        """연속 필터 이벤트를 디바운스로 합쳐 마지막 변경만 적용."""
        self._pending_filter = filters
        self._filter_apply_timer.start(scraper_config.FILTER_DEBOUNCE_MS)
    def _run_scheduled_filter_apply(self):
        if self._pending_filter is None:
            return
        filters = self._pending_filter
        self._pending_filter = None
        self._apply_filter(filters)
    def _append_filter_log(self, message: str):
        """동일 필터 로그의 짧은 간격 중복 출력을 억제."""
        now = time.monotonic()
        if message == self._last_filter_log_msg and (now - self._last_filter_log_ts) < 1.0:
            return
        self._last_filter_log_msg = message
        self._last_filter_log_ts = now
        self.log_viewer.append_log(message)
    def _apply_filter(self, filters=None):
        if filters is None:
            filters = self.filter_panel.get_current_filters()
            
        if not self.all_results:
            return
            
        direct_only = filters.get("direct_only", False)
        include_layover = filters.get("include_layover", True)
        airline_category = filters.get("airline_category", "ALL")
        max_stops = filters.get("max_stops", 3)
        
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
            
            # 5. Price Range Filter (Advanced)
            min_price = filters.get("min_price", 0)
            max_price = filters.get("max_price", MAX_PRICE_FILTER)
            if f.price < min_price:
                continue
            if max_price < MAX_PRICE_FILTER:
                if f.price > max_price:
                    continue
                
            filtered.append(f)
            
        self.table.update_data(filtered)
        
        # 상태 메시지에 가격 범위 표시
        price_msg = ""
        min_p = filters.get("min_price", 0)
        max_p = filters.get("max_price", MAX_PRICE_FILTER)
        if min_p > 0 or max_p < MAX_PRICE_FILTER:
            price_msg = f" | 가격: {min_p//10000}~{max_p//10000}만원"
        
        msg = f"필터링: {len(filtered)}/{len(self.all_results)} | 시간: {start_h}~{end_h}시 | 항공사: {airline_category}{price_msg}"
        self.statusBar().showMessage(msg)
        self._append_filter_log(msg)

    # --- History Tab Methods ---
