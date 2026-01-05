
"""
Background Workers for Flight Bot
"""
import logging
import traceback
from datetime import datetime, timedelta
from PyQt6.QtCore import QThread, pyqtSignal

from scraper_v2 import FlightSearcher

# 로거 설정
logger = logging.getLogger(__name__)

class SearchWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    manual_mode_signal = pyqtSignal(object)  # active_searcher

    def __init__(self, origin, destination, date, return_date, adults, cabin_class="ECONOMY", max_results=500):
        super().__init__()
        self.origin = origin
        self.destination = destination
        self.date = date
        self.return_date = return_date
        self.adults = adults
        self.cabin_class = cabin_class
        self.max_results = max_results
        self.searcher = FlightSearcher()
        self._cancelled = False

    def cancel(self):
        """검색 취소 요청 및 브라우저 정리"""
        self._cancelled = True
        try:
            if self.searcher:
                self.searcher.close()
        except Exception as e:
            logging.debug(f"검색 취소 중 오류 (무시됨): {e}")

    def run(self):
        try:
            results = self.searcher.search(
                self.origin, self.destination, self.date, 
                self.return_date, self.adults, self.cabin_class,
                max_results=self.max_results,
                progress_callback=lambda msg: self.progress.emit(msg)
            )
            
            if self._cancelled:
                self.progress.emit("검색이 취소되었습니다.")
                return
            
            if not results and self.searcher.is_manual_mode():
                self.manual_mode_signal.emit(self.searcher)
            else:
                self.finished.emit(results)
        except Exception as e:
            if not self._cancelled:
                traceback.print_exc()
                self.error.emit(str(e))
        finally:
            # 항상 브라우저 정리 보장
            if self._cancelled or not self.searcher.is_manual_mode():
                try:
                    self.searcher.close()
                except Exception:
                    pass


class MultiSearchWorker(QThread):
    """다중 목적지 순차 검색 Worker"""
    progress = pyqtSignal(str)
    single_finished = pyqtSignal(str, list)  # dest, results
    all_finished = pyqtSignal(dict)  # {dest: [results]}
    error = pyqtSignal(str)
    
    def __init__(self, origin, destinations, date, return_date, adults, max_results=500):
        super().__init__()
        self.origin = origin
        self.destinations = destinations  # list of destination codes
        self.date = date
        self.return_date = return_date
        self.adults = adults
        self.max_results = max_results
    
    def run(self):
        all_results = {}
        total = len(self.destinations)
        
        for i, dest in enumerate(self.destinations, 1):
            try:
                self.progress.emit(f"🔍 [{i}/{total}] {dest} 검색 중...")
                searcher = FlightSearcher()
                results = searcher.search(
                    self.origin, dest, self.date, self.return_date, self.adults,
                    max_results=self.max_results,
                    progress_callback=lambda msg: self.progress.emit(f"[{dest}] {msg}")
                )
                all_results[dest] = results
                self.single_finished.emit(dest, results)
                searcher.close()
            except Exception as e:
                self.progress.emit(f"⚠️ {dest} 검색 실패: {e}")
                all_results[dest] = []
        
        self.all_finished.emit(all_results)


class DateRangeWorker(QThread):
    """날짜 범위 검색 Worker"""
    progress = pyqtSignal(str)
    date_result = pyqtSignal(str, int, str)  # date, min_price, airline
    all_finished = pyqtSignal(dict)  # {date: (price, airline)}
    
    def __init__(self, origin, dest, dates, return_offset, adults, max_results=500):
        super().__init__()
        self.origin = origin
        self.dest = dest
        self.dates = dates  # list of date strings
        self.return_offset = return_offset  # days after departure for return
        self.adults = adults
        self.max_results = max_results
    
    def run(self):
        all_results = {}
        total = len(self.dates)
        
        # 최대 검색 횟수 제한 (무한 루프 방지)
        MAX_SEARCHES = 30
        if total > MAX_SEARCHES:
            self.progress.emit(f"⚠️ 최대 {MAX_SEARCHES}개 날짜만 검색합니다.")
            self.dates = self.dates[:MAX_SEARCHES]
            total = MAX_SEARCHES
        
        for i, date in enumerate(self.dates, 1):
            try:
                self.progress.emit(f"📅 [{i}/{total}] {date} 검색 중...")
                
                # Calculate return date
                dep_dt = datetime.strptime(date, "%Y%m%d")
                ret_date = (dep_dt + timedelta(days=self.return_offset)).strftime("%Y%m%d") if self.return_offset else None
                
                searcher = FlightSearcher()
                
                try:
                    results = searcher.search(
                        self.origin, self.dest, date, ret_date, self.adults,
                        max_results=self.max_results,
                        progress_callback=lambda msg: self.progress.emit(msg)
                    )
                    
                    # 수동 모드 전환 시 건너뛰기
                    if searcher.is_manual_mode():
                        self.progress.emit(f"⏭️ {date} - 수동 모드 전환됨, 건너뜁니다")
                        all_results[date] = (0, "수동모드")
                        searcher.close()
                        continue
                    
                    if results:
                        min_price = min(r.price for r in results)
                        min_airline = next(r.airline for r in results if r.price == min_price)
                        all_results[date] = (min_price, min_airline)
                        self.date_result.emit(date, min_price, min_airline)
                        self.progress.emit(f"✅ {date}: {min_price:,}원 ({min_airline})")
                    else:
                        all_results[date] = (0, "N/A")
                        self.progress.emit(f"⚠️ {date}: 결과 없음")
                finally:
                    # 항상 브라우저 닫기
                    try:
                        searcher.close()
                    except:
                        pass
                    
            except Exception as e:
                self.progress.emit(f"⚠️ {date} 검색 실패: {e}")
                all_results[date] = (0, "Error")
        
        self.progress.emit(f"🏁 검색 완료! 총 {len(all_results)}개 날짜 분석됨")
        self.all_finished.emit(all_results)
