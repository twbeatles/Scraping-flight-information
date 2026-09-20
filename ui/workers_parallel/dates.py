"""Date-range parallel search worker (SRP: date fan-out only)."""

import logging
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timedelta
from PyQt6.QtCore import pyqtSignal

from ui.workers_parallel.base import (
    MAX_PARALLEL_WORKERS,
    CancellableWorker,
    _cancel_and_shutdown_executor,
    _searcher_cls,
)


logger = logging.getLogger(__name__)

MAX_DATE_RANGE_SEARCHES = 30


class DateRangeWorker(CancellableWorker):
    """날짜 범위 검색 Worker"""

    _cancel_log_prefix = "날짜 검색"

    progress = pyqtSignal(str)
    date_result = pyqtSignal(str, int, str)  # date, min_price, airline
    all_finished = pyqtSignal(dict)  # {date: (price, airline)}

    def __init__(
        self,
        origin,
        dest,
        dates,
        return_offset,
        adults,
        cabin_class="ECONOMY",
        max_results=1000,
        telemetry_callback=None,
        child=0,
        infant=0,
    ):
        super().__init__()
        self.origin = origin
        self.dest = dest
        self.dates = dates  # list of date strings
        self.return_offset = return_offset  # days after departure for return
        self.adults = adults
        self.cabin_class = cabin_class
        self.max_results = max_results
        self.telemetry_callback = telemetry_callback
        self.child = max(0, int(child or 0))
        self.infant = max(0, int(infant or 0))

    def run(self):
        all_results = {}
        total = len(self.dates)

        # 최대 검색 날짜수 제한 (무한 루프 방지)
        if total > MAX_DATE_RANGE_SEARCHES:
            self.progress.emit(f"⚠️ 최대 {MAX_DATE_RANGE_SEARCHES}개 날짜만 검색됩니다.")
            self.dates = self.dates[:MAX_DATE_RANGE_SEARCHES]
            total = MAX_DATE_RANGE_SEARCHES

        if total == 0:
            self.all_finished.emit({})
            return

        def search_single(date):
            if self.is_cancelled():
                return date, (0, "취소됨"), "cancelled"

            ret_date = None
            try:
                dep_dt = datetime.strptime(date, "%Y%m%d")
                ret_date = (dep_dt + timedelta(days=self.return_offset)).strftime("%Y%m%d") if self.return_offset else None
            except Exception:
                pass

            searcher_cls = _searcher_cls()
            try:
                searcher = searcher_cls(telemetry_callback=self.telemetry_callback)
            except TypeError:
                searcher = searcher_cls()
            self._register_active_searcher(searcher)
            try:
                if self.is_cancelled():
                    return date, (0, "취소됨"), "cancelled"
                results = searcher.search(
                    self.origin, self.dest, date, ret_date, self.adults, self.cabin_class,
                    max_results=self.max_results,
                    progress_callback=lambda msg: self.progress.emit(msg),
                    background_mode=True,
                    child=self.child,
                    infant=self.infant,
                    cancel_check=self.is_cancelled,
                )

                if searcher.is_manual_mode():
                    return date, (0, "수동모드"), "manual"

                if results:
                    from scraping.models import effective_flight_price

                    best = min(results, key=effective_flight_price)
                    return date, (effective_flight_price(best), best.airline), "ok"
                return date, (0, "N/A"), "empty"
            except Exception as e:
                return date, (0, "Error"), str(e)
            finally:
                self._unregister_active_searcher(searcher)
                try:
                    searcher.close()
                except Exception as e:
                    logger.debug(f"날짜 검색 브라우저 정리 오류 (무시됨): {e}")

        executor = ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS)
        pending = list(self.dates)
        futures = {}
        completed = 0
        try:
            while pending or futures:
                if self.is_cancelled():
                    self._close_all_active_searchers()
                    _cancel_and_shutdown_executor(executor, futures)
                    self.progress.emit(f"⚠️ 날짜 범위 검색이 취소되었습니다. ({len(all_results)}개 날짜 분석)")
                    return

                while pending and len(futures) < MAX_PARALLEL_WORKERS and not self.is_cancelled():
                    date = pending.pop(0)
                    self.progress.emit(f"📟 [{completed + len(futures) + 1}/{total}] {date} 검색 대기...")
                    futures[executor.submit(search_single, date)] = date

                if not futures:
                    continue

                done, _ = wait(list(futures.keys()), timeout=0.1, return_when=FIRST_COMPLETED)
                if not done:
                    continue

                for future in done:
                    date = futures.pop(future, None)
                    if not date:
                        continue

                    completed += 1
                    try:
                        dep_date, price_info, status = future.result()
                    except Exception as e:
                        dep_date, price_info, status = date, (0, "Error"), str(e)

                    all_results[dep_date] = price_info
                    price, airline = price_info

                    if status == "cancelled":
                        continue
                    if status == "manual":
                        self.progress.emit(f"⚠️ {dep_date} - 수동 모드 전환됨, 건너뜁니다. [{completed}/{total}]")
                        continue
                    if status == "ok":
                        self.date_result.emit(dep_date, price, airline)
                        self.progress.emit(f"✅ {dep_date}: {price:,}원 ({airline}) [{completed}/{total}]")
                        continue
                    if status == "empty":
                        self.progress.emit(f"⚠️ {dep_date}: 결과 없음 [{completed}/{total}]")
                        continue

                    self.progress.emit(f"⚠️ {dep_date} 검색 실패: {status} [{completed}/{total}]")
        finally:
            if futures:
                _cancel_and_shutdown_executor(executor, futures)
            else:
                executor.shutdown(wait=False, cancel_futures=True)

        self.progress.emit(f"🎾 검색 완료! 총 {len(all_results)}개 날짜 분석")
        ordered_results = {date: all_results.get(date, (0, "N/A")) for date in self.dates}
        self.all_finished.emit(ordered_results)
