"""Price history and search log operations."""

import sqlite3
import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from scraper_v2 import FlightResult
from storage.models import (
    FavoriteItem,
    PriceHistoryItem,
    PriceAlert,
    TELEMETRY_DB_RETENTION_DAYS,
    TELEMETRY_JSONL_MAX_BYTES,
    TELEMETRY_JSONL_MAX_FILES,
)

logger = logging.getLogger(__name__)

class HistoryLogsMixin:
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

__all__ = ["HistoryLogsMixin"]
