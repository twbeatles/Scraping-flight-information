"""Parallel route/date search orchestration."""

import heapq
import logging
from typing import Callable, Dict, List, Optional

from scraping.models import FlightResult
from scraping.searcher import FlightSearcher

logger = logging.getLogger(__name__)

class ParallelSearcher:
    """다중 검색을 병렬로 실행하는 검색 엔진"""
    
    def __init__(self, max_concurrent: int = 2):
        self.max_concurrent = min(max_concurrent, 4)  # 최대 4개로 제한
        self.results = {}
        self._lock = None
    
    def search_multiple_destinations(self, origin: str, destinations: List[str],
                                     departure_date: str, return_date: Optional[str] = None,
                                     adults: int = 1, cabin_class: str = "ECONOMY",
                                     progress_callback: Callable = None) -> Dict[str, List[FlightResult]]:
        """여러 목적지를 병렬로 검색"""
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        self._lock = threading.Lock()
        self.results = {}
        
        def search_single(dest: str) -> tuple:
            """단일 목적지 검색"""
            searcher = FlightSearcher()
            try:
                def emit(msg):
                    if progress_callback:
                        progress_callback(f"[{dest}] {msg}")
                    logger.info(f"[{dest}] {msg}")
                
                results = searcher.scraper.search(
                    origin, dest, departure_date, return_date, 
                    adults, cabin_class, max_results=500, emit=emit, background_mode=True
                )
                return dest, results
            except Exception as e:
                logger.error(f"Parallel search error for {dest}: {e}")
                return dest, []
            finally:
                searcher.close()
        
        if progress_callback:
            progress_callback(f"🚀 병렬 검색 시작: {len(destinations)}개 목적지 (동시 {self.max_concurrent}개)")
        
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            futures = {executor.submit(search_single, dest): dest for dest in destinations}
            
            for future in as_completed(futures):
                try:
                    dest, results = future.result()
                    with self._lock:
                        self.results[dest] = results
                        
                    if progress_callback:
                        count = len(results)
                        cheapest = min((r.price for r in results), default=0) if results else 0
                        progress_callback(f"✅ {dest} 완료: {count}개 결과, 최저가 {cheapest:,}원")
                except Exception as e:
                    logger.error(f"Future error: {e}")
        
        if progress_callback:
            progress_callback(f"🏁 병렬 검색 완료: {len(self.results)}개 목적지")
        
        return self.results
    
    def search_date_range(self, origin: str, destination: str,
                          dates: List[str], return_offset: int = 0,
                          adults: int = 1, cabin_class: str = "ECONOMY",
                          progress_callback: Callable = None) -> Dict[str, tuple]:
        """여러 날짜를 병렬로 검색"""
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from datetime import datetime, timedelta
        
        self._lock = threading.Lock()
        date_results = {}
        
        def search_single_date(dep_date: str) -> tuple:
            """단일 날짜 검색"""
            ret_date = None
            if return_offset > 0:
                try:
                    dt = datetime.strptime(dep_date, "%Y%m%d")
                    ret_date = (dt + timedelta(days=return_offset)).strftime("%Y%m%d")
                except Exception:
                    pass
            
            searcher = FlightSearcher()
            try:
                # 조용히 실행
                results = searcher.scraper.search(
                    origin, destination, dep_date, ret_date,
                    adults, cabin_class, max_results=100, emit=lambda msg: None, background_mode=True
                )
                
                if results:
                    cheapest = min(results, key=lambda x: x.price)
                    return dep_date, (cheapest.price, cheapest.airline)
                return dep_date, (0, "N/A")
            except Exception as e:
                logger.error(f"Date search error for {dep_date}: {e}")
                return dep_date, (0, "Error")
            finally:
                searcher.close()
        
        if progress_callback:
            progress_callback(f"🚀 날짜 병렬 검색: {len(dates)}일 (동시 {self.max_concurrent}개)")
        
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            futures = {executor.submit(search_single_date, d): d for d in dates}
            completed = 0
            
            for future in as_completed(futures):
                try:
                    dep_date, price_info = future.result()
                    with self._lock:
                        date_results[dep_date] = price_info
                        completed += 1
                    
                    if progress_callback:
                        price, airline = price_info
                        if price > 0:
                            progress_callback(f"📅 {dep_date}: {price:,}원 ({airline}) [{completed}/{len(dates)}]")
                        else:
                            progress_callback(f"📅 {dep_date}: 결과 없음 [{completed}/{len(dates)}]")
                except Exception as e:
                    logger.error(f"Future error: {e}")
        
        if progress_callback:
            progress_callback(f"🏁 날짜 검색 완료: {len(date_results)}일")
        
        return date_results


if __name__ == "__main__":
    searcher = FlightSearcher()
    try:
        print("\n=== Playwright 테스트 (서울 → 도쿄) ===")
        # 테스트를 위해 30일 후 날짜 생성
        from datetime import datetime, timedelta
        d1 = (datetime.now() + timedelta(days=30)).strftime("%Y%m%d")
        d2 = (datetime.now() + timedelta(days=35)).strftime("%Y%m%d")
        
        results = searcher.search("ICN", "NRT", d1, d2)
        
        if results:
            print(f"\n{len(results)}개 결과:")
            for i, r in enumerate(results[:5], 1):
                stops = "직항" if r.stops == 0 else f"{r.stops}회 경유"
                print(f"{i}. {r.airline} - {r.price:,}원 | {r.departure_time} -> {r.arrival_time}")
        else:
            print("결과 없음 또는 수동 모드 전환됨")
    finally:
        searcher.close()
