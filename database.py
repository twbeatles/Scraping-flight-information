"""
Flight Bot Database Module
SQLite 기반 즐겨찾기, 가격 히스토리, 검색 로그 관리
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


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


class FlightDatabase:
    """항공권 데이터베이스 관리자"""
    
    def __init__(self, db_path: str = "flight_data.db"):
        self.db_path = db_path
        self._init_db()
    
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
            
            conn.commit()
    
    # ===== 즐겨찾기 =====
    
    def add_favorite(self, flight_data: Dict[str, Any], search_params: Dict[str, Any] = None) -> int:
        """즐겨찾기 추가"""
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM favorites ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [FavoriteItem(**dict(row)) for row in rows]
    
    def get_favorite_by_id(self, fav_id: int) -> Optional[FavoriteItem]:
        """ID로 즐겨찾기 조회"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM favorites WHERE id = ?", (fav_id,))
            row = cursor.fetchone()
            return FavoriteItem(**dict(row)) if row else None
    
    def update_favorite_note(self, fav_id: int, note: str) -> bool:
        """즐겨찾기 메모 수정"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE favorites SET note = ? WHERE id = ?", (note, fav_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def remove_favorite(self, fav_id: int) -> bool:
        """즐겨찾기 삭제"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM favorites WHERE id = ?", (fav_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def is_favorite(self, airline: str, price: int, departure_time: str, origin: str, dest: str) -> bool:
        """이미 즐겨찾기에 있는지 확인"""
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
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
        
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
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
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM price_history WHERE recorded_at < ?", (cutoff,))
            cursor.execute("DELETE FROM search_logs WHERE searched_at < ?", (cutoff,))
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
    print(f"추가된 즐겨찾기 ID: {fav_id}")
    
    # 가격 히스토리 테스트
    db.add_price_history("ICN", "NRT", "20260115", 350000, "대한항공")
    db.add_price_history("ICN", "NRT", "20260115", 320000, "진에어")
    
    trend = db.get_price_trend("ICN", "NRT")
    print(f"가격 추이: {trend}")
    
    # 통계
    stats = db.get_stats()
    print(f"DB 통계: {stats}")
    
    # 정리
    os.remove("test_flight.db")
    print("테스트 완료!")
