"""
Flight Bot Database Module
SQLite 기반 즐겨찾기, 가격 히스토리, 검색 로그 관리
"""

import sqlite3
import os
import sys
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from scraper_v2 import FlightResult

# 로거 설정
logger = logging.getLogger(__name__)


@dataclass
class FavoriteItem:
    """즐겨찾기 항목"""
    id: int
    airline: str
    price: int
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str]
    departure_time: str
    arrival_time: str
    stops: int
    note: str
    created_at: str
    search_params: str  # JSON string


@dataclass
class PriceHistoryItem:
    """가격 히스토리 항목"""
    id: int
    origin: str
    destination: str
    departure_date: str
    airline: str
    price: int
    recorded_at: str


@dataclass
class PriceAlert:
    """가격 알림 항목"""
    id: int
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str]
    target_price: int
    is_active: int
    last_checked: Optional[str]
    last_price: Optional[int]
    triggered: int
    created_at: str


class FlightDatabase:
    """항공권 데이터베이스 관리자 - 연결 재사용 최적화"""
    
    _local = threading.local()  # Thread-local storage (클래스 레벨 초기화)
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Determine appropriate path based on environment
            if getattr(sys, 'frozen', False):
                # Running as PyInstaller Bundle (EXE) -> Use AppData/Local
                app_data = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'FlightBot')
                os.makedirs(app_data, exist_ok=True)
                self.db_path = os.path.join(app_data, "flight_data.db")
            else:
                # Running from source (Dev) -> Use current directory
                self.db_path = "flight_data.db"
        else:
            self.db_path = db_path
            
        # Ensure directory exists for custom paths
        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create DB directory: {e}")

        logger.info(f"Database path: {self.db_path}")
        self._init_db()
    
    def _get_connection(self):
        """Thread-safe connection management with proper initialization"""
        if not hasattr(FlightDatabase._local, 'connections'):
            FlightDatabase._local.connections = {}
        
        conn = FlightDatabase._local.connections.get(self.db_path)
        
        # 연결이 없거나 닫혔을 경우 새로 생성
        if conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
            conn.execute("PRAGMA synchronous=NORMAL")  # Faster writes with reasonable safety
            FlightDatabase._local.connections[self.db_path] = conn
        else:
            # 연결 유효성 검사
            try:
                conn.execute("SELECT 1")
            except (sqlite3.ProgrammingError, sqlite3.OperationalError):
                # 연결이 닫혔거나 손상됐으면 재생성
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                FlightDatabase._local.connections[self.db_path] = conn
        
        return conn
    
    def _init_db(self):
        """데이터베이스 및 테이블 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 즐겨찾기 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    airline TEXT NOT NULL,
                    price INTEGER NOT NULL,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    departure_date TEXT NOT NULL,
                    return_date TEXT,
                    departure_time TEXT,
                    arrival_time TEXT,
                    stops INTEGER DEFAULT 0,
                    note TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    search_params TEXT DEFAULT '{}'
                )
            """)
            
            # 가격 히스토리 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    departure_date TEXT NOT NULL,
                    airline TEXT,
                    price INTEGER NOT NULL,
                    recorded_at TEXT NOT NULL
                )
            """)
            
            # 검색 로그 테이블 (통계용)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    departure_date TEXT NOT NULL,
                    return_date TEXT,
                    adults INTEGER DEFAULT 1,
                    result_count INTEGER DEFAULT 0,
                    min_price INTEGER,
                    searched_at TEXT NOT NULL
                )
            """)
            
            # 인덱스 생성
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ph_route ON price_history(origin, destination)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ph_date ON price_history(departure_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fav_route ON favorites(origin, destination)")
            
            # 가격 알림 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    departure_date TEXT NOT NULL,
                    return_date TEXT,
                    target_price INTEGER NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    last_checked TEXT,
                    last_price INTEGER,
                    triggered INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_active ON price_alerts(is_active)")
            
            # 마지막 검색 결과 테이블 (프로그램 재시작 시 복원용)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS last_search_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    airline TEXT NOT NULL,
                    price INTEGER NOT NULL,
                    departure_time TEXT,
                    arrival_time TEXT,
                    stops INTEGER DEFAULT 0,
                    source TEXT,
                    return_departure_time TEXT,
                    return_arrival_time TEXT,
                    return_stops INTEGER DEFAULT 0,
                    is_round_trip INTEGER DEFAULT 0,
                    outbound_price INTEGER DEFAULT 0,
                    return_price INTEGER DEFAULT 0,
                    return_airline TEXT
                )
            """)
            
            # 마지막 검색 메타데이터 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS last_search_meta (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    origin TEXT,
                    destination TEXT,
                    departure_date TEXT,
                    return_date TEXT,
                    adults INTEGER DEFAULT 1,
                    cabin_class TEXT DEFAULT 'ECONOMY',
                    searched_at TEXT NOT NULL,
                    result_count INTEGER DEFAULT 0
                )
            """)
            
            conn.commit()
    
    # ===== 즐겨찾기 =====
    
    def add_favorite(self, flight_data: Dict[str, Any], search_params: Dict[str, Any] = None) -> int:
        """즐겨찾기 추가"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO favorites 
                (airline, price, origin, destination, departure_date, return_date,
                 departure_time, arrival_time, stops, note, created_at, search_params)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                flight_data.get('airline', ''),
                flight_data.get('price', 0),
                flight_data.get('origin', ''),
                flight_data.get('destination', ''),
                flight_data.get('departure_date', ''),
                flight_data.get('return_date'),
                flight_data.get('departure_time', ''),
                flight_data.get('arrival_time', ''),
                flight_data.get('stops', 0),
                flight_data.get('note', ''),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                json.dumps(search_params or {}, ensure_ascii=False)
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_favorites(self) -> List[FavoriteItem]:
        """모든 즐겨찾기 조회"""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM favorites ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [FavoriteItem(**dict(row)) for row in rows]
    
    def get_favorite_by_id(self, fav_id: int) -> Optional[FavoriteItem]:
        """ID로 즐겨찾기 조회"""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM favorites WHERE id = ?", (fav_id,))
            row = cursor.fetchone()
            return FavoriteItem(**dict(row)) if row else None
    
    def update_favorite_note(self, fav_id: int, note: str) -> bool:
        """즐겨찾기 메모 수정"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE favorites SET note = ? WHERE id = ?", (note, fav_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def remove_favorite(self, fav_id: int) -> bool:
        """즐겨찾기 삭제"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM favorites WHERE id = ?", (fav_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def is_favorite(self, airline: str, price: int, departure_time: str, origin: str, dest: str) -> bool:
        """이미 즐겨찾기에 있는지 확인"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM favorites 
                WHERE airline = ? AND price = ? AND departure_time = ? 
                AND origin = ? AND destination = ?
            """, (airline, price, departure_time, origin, dest))
            return cursor.fetchone()[0] > 0
    
    # ===== 가격 히스토리 =====
    
    def add_price_history(self, origin: str, dest: str, dep_date: str, 
                          price: int, airline: str = None):
        """가격 히스토리 추가"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO price_history 
                (origin, destination, departure_date, airline, price, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                origin, dest, dep_date, airline, price,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            conn.commit()
    
    def add_price_history_batch(self, origin: str, dest: str, dep_date: str, 
                                results: List[Dict[str, Any]]):
        """검색 결과 일괄 저장 (최저가만)"""
        if not results:
            return
        
        # 최저가만 저장
        min_price = min(r.get('price', float('inf')) for r in results)
        min_item = next((r for r in results if r.get('price') == min_price), None)
        
        if min_item:
            self.add_price_history(
                origin, dest, dep_date,
                min_price, min_item.get('airline')
            )
    
    def get_price_history(self, origin: str, dest: str, 
                          days: int = 30) -> List[PriceHistoryItem]:
        """노선별 가격 히스토리 조회"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM price_history 
                WHERE origin = ? AND destination = ? AND recorded_at >= ?
                ORDER BY recorded_at ASC
            """, (origin, dest, cutoff))
            rows = cursor.fetchall()
            return [PriceHistoryItem(**dict(row)) for row in rows]
    
    def get_price_trend(self, origin: str, dest: str, dep_date: str = None) -> Dict[str, Any]:
        """가격 변동 추이 분석"""
        history = self.get_price_history(origin, dest, days=30)
        
        if not history:
            return {"trend": "unknown", "change": 0, "data": []}
        
        prices = [h.price for h in history]
        
        # 최근 vs 이전 비교
        if len(prices) >= 2:
            recent = prices[-1]
            prev = prices[-2]
            change = recent - prev
            trend = "up" if change > 0 else ("down" if change < 0 else "stable")
        else:
            change = 0
            trend = "stable"
        
        return {
            "trend": trend,
            "change": change,
            "min": min(prices),
            "max": max(prices),
            "avg": sum(prices) // len(prices),
            "current": prices[-1] if prices else 0,
            "data": [(h.recorded_at, h.price) for h in history]
        }
    
    # ===== 검색 로그 =====
    
    def log_search(self, origin: str, dest: str, dep_date: str, 
                   return_date: str = None, adults: int = 1,
                   result_count: int = 0, min_price: int = None):
        """검색 로그 저장"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO search_logs 
                (origin, destination, departure_date, return_date, adults, 
                 result_count, min_price, searched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                origin, dest, dep_date, return_date, adults,
                result_count, min_price,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            conn.commit()
    
    def get_popular_routes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """인기 노선 조회 (검색 빈도 기준)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT origin, destination, COUNT(*) as count,
                       AVG(min_price) as avg_price
                FROM search_logs
                GROUP BY origin, destination
                ORDER BY count DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [
                {"origin": r[0], "destination": r[1], "count": r[2], "avg_price": r[3]}
                for r in rows
            ]
    
    # ===== 유틸리티 =====
    
    def get_stats(self) -> Dict[str, int]:
        """데이터베이스 통계"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM favorites")
            fav_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM price_history")
            history_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM search_logs")
            log_count = cursor.fetchone()[0]
            
            return {
                "favorites": fav_count,
                "price_history": history_count,
                "search_logs": log_count
            }
    
    
    def cleanup_old_data(self, days: int = 90):
        """오래된 데이터 정리"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM price_history WHERE recorded_at < ?", (cutoff,))
            cursor.execute("DELETE FROM search_logs WHERE searched_at < ?", (cutoff,))
            conn.commit()
            
    def optimize(self):
        """데이터베이스 최적화 (VACUUM)"""
        try:
            with self._get_connection() as conn:
                conn.execute("VACUUM")
            logger.info("Database optimized (VACUUM completed)")
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")

    # ===== 가격 알림 =====
    
    def add_price_alert(self, origin: str, dest: str, dep_date: str, 
                        return_date: str, target_price: int) -> int:
        """가격 알림 추가"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO price_alerts 
                (origin, destination, departure_date, return_date, target_price, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                origin, dest, dep_date, return_date, target_price,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_active_alerts(self) -> List[PriceAlert]:
        """활성화된 가격 알림 조회"""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM price_alerts 
                WHERE is_active = 1 AND triggered = 0
                ORDER BY created_at DESC
            """)
            rows = cursor.fetchall()
            return [PriceAlert(**dict(row)) for row in rows]
    
    def get_all_alerts(self) -> List[PriceAlert]:
        """모든 가격 알림 조회"""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM price_alerts ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [PriceAlert(**dict(row)) for row in rows]
    
    def update_alert_check(self, alert_id: int, current_price: int) -> bool:
        """알림 마지막 체크 시간 및 가격 업데이트"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE price_alerts 
                SET last_checked = ?, last_price = ?
                WHERE id = ?
            """, (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                current_price,
                alert_id
            ))
            conn.commit()
            return cursor.rowcount > 0
    
    def mark_alert_triggered(self, alert_id: int) -> bool:
        """알림 발동 상태로 표시"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE price_alerts 
                SET triggered = 1, is_active = 0
                WHERE id = ?
            """, (alert_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_alert(self, alert_id: int) -> bool:
        """가격 알림 삭제"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM price_alerts WHERE id = ?", (alert_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def toggle_alert_active(self, alert_id: int, is_active: bool) -> bool:
        """가격 알림 활성화/비활성화"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE price_alerts SET is_active = ? WHERE id = ?
            """, (1 if is_active else 0, alert_id))
            conn.commit()
            return cursor.rowcount > 0

    # ===== 마지막 검색 결과 저장/복원 =====
    
    def save_last_search_results(self, search_params: Dict[str, Any], results: List[Any]):
        """마지막 검색 결과를 DB에 저장 (프로그램 재시작 시 복원용)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 기존 결과 삭제
            cursor.execute("DELETE FROM last_search_results")
            cursor.execute("DELETE FROM last_search_meta")
            
            # 메타데이터 저장
            cursor.execute("""
                INSERT OR REPLACE INTO last_search_meta 
                (id, origin, destination, departure_date, return_date, adults, cabin_class, searched_at, result_count)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                search_params.get('origin', ''),
                search_params.get('dest', ''),
                search_params.get('dep', ''),
                search_params.get('ret'),
                search_params.get('adults', 1),
                search_params.get('cabin_class', 'ECONOMY'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                len(results)
            ))
            
            # 결과 저장 (최대 1000개)
            limit = 1000
            actual_count = min(len(results), limit)
            if len(results) > limit:
                logger.info(f"마지막 검색 결과 저장: {actual_count}/{len(results)}건 (제한)")

            rows = [
                (
                    flight.airline,
                    flight.price,
                    flight.departure_time,
                    flight.arrival_time,
                    flight.stops,
                    flight.source,
                    getattr(flight, 'return_departure_time', ''),
                    getattr(flight, 'return_arrival_time', ''),
                    getattr(flight, 'return_stops', 0),
                    1 if getattr(flight, 'is_round_trip', False) else 0,
                    getattr(flight, 'outbound_price', 0),
                    getattr(flight, 'return_price', 0),
                    getattr(flight, 'return_airline', '')
                )
                for flight in results[:limit]
            ]
            cursor.executemany(
                """
                INSERT INTO last_search_results 
                (airline, price, departure_time, arrival_time, stops, source,
                 return_departure_time, return_arrival_time, return_stops,
                 is_round_trip, outbound_price, return_price, return_airline)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            
            conn.commit()
            logger.info(f"마지막 검색 결과 저장: {actual_count}/{len(results)}건")
    
    def get_last_search_results(self) -> tuple:
        """저장된 마지막 검색 결과 복원
        
        Returns:
            tuple: (search_params, results, searched_at, hours_ago)
        """
        # FlightResult import is now global
        
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 메타데이터 조회
            cursor.execute("SELECT * FROM last_search_meta WHERE id = 1")
            meta_row = cursor.fetchone()
            
            if not meta_row:
                return {}, [], "", 0
            
            meta = dict(meta_row)
            search_params = {
                'origin': meta.get('origin', ''),
                'dest': meta.get('destination', ''),
                'dep': meta.get('departure_date', ''),
                'ret': meta.get('return_date'),
                'adults': meta.get('adults', 1),
                'cabin_class': meta.get('cabin_class', 'ECONOMY')
            }
            searched_at = meta.get('searched_at', '')
            
            # 경과 시간 계산
            hours_ago = 0
            if searched_at:
                try:
                    search_time = datetime.strptime(searched_at, "%Y-%m-%d %H:%M:%S")
                    delta = datetime.now() - search_time
                    hours_ago = delta.total_seconds() / 3600
                except Exception:
                    pass
            
            # 결과 조회
            cursor.execute("SELECT * FROM last_search_results ORDER BY price ASC")
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                r = dict(row)
                flight = FlightResult(
                    airline=r.get('airline', ''),
                    price=r.get('price', 0),
                    departure_time=r.get('departure_time', ''),
                    arrival_time=r.get('arrival_time', ''),
                    stops=r.get('stops', 0),
                    source=r.get('source', 'Cached'),
                    return_departure_time=r.get('return_departure_time', ''),
                    return_arrival_time=r.get('return_arrival_time', ''),
                    return_stops=r.get('return_stops', 0),
                    is_round_trip=bool(r.get('is_round_trip', 0)),
                    outbound_price=r.get('outbound_price', 0),
                    return_price=r.get('return_price', 0),
                    return_airline=r.get('return_airline', '')
                )
                results.append(flight)
            
            return search_params, results, searched_at, hours_ago
    
    def clear_last_search_results(self):
        """저장된 마지막 검색 결과 삭제"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM last_search_results")
            cursor.execute("DELETE FROM last_search_meta")
            conn.commit()


# 테스트
if __name__ == "__main__":
    db = FlightDatabase("test_flight.db")
    
    # 즐겨찾기 테스트
    fav_id = db.add_favorite({
        "airline": "대한항공",
        "price": 350000,
        "origin": "ICN",
        "destination": "NRT",
        "departure_date": "20260115",
        "departure_time": "10:30",
        "arrival_time": "13:00",
        "stops": 0
    })
    logger.info(f"추가된 즐겨찾기 ID: {fav_id}")
    
    # 가격 히스토리 테스트
    db.add_price_history("ICN", "NRT", "20260115", 350000, "대한항공")
    db.add_price_history("ICN", "NRT", "20260115", 320000, "진에어")
    
    trend = db.get_price_trend("ICN", "NRT")
    logger.info(f"가격 추이: {trend}")
    
    # 통계
    stats = db.get_stats()
    logger.info(f"DB 통계: {stats}")
    
    # 정리
    os.remove("test_flight.db")
    logger.info("테스트 완료!")

