"""Last-search snapshot save/restore operations."""

import sqlite3
import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, TYPE_CHECKING

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

if TYPE_CHECKING:
    from storage.flight_database import FlightDatabase

class LastSearchMixin:
    def save_last_search_results(self: Any, search_params: Dict[str, Any], results: List[Any]):
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
                    getattr(flight, 'return_airline', ''),
                    float(getattr(flight, 'confidence', 0.0) or 0.0),
                    getattr(flight, 'extraction_source', ''),
                )
                for flight in results[:limit]
            ]
            cursor.executemany(
                """
                INSERT INTO last_search_results 
                (airline, price, departure_time, arrival_time, stops, source,
                 return_departure_time, return_arrival_time, return_stops,
                 is_round_trip, outbound_price, return_price, return_airline,
                 confidence, extraction_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            
            conn.commit()
            logger.info(f"마지막 검색 결과 저장: {actual_count}/{len(results)}건")
    def get_last_search_results(self: Any) -> tuple:
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
                    return_airline=r.get('return_airline', ''),
                    confidence=float(r.get('confidence', 0.0) or 0.0),
                    extraction_source=r.get('extraction_source', ''),
                )
                results.append(flight)
            
            return search_params, results, searched_at, hours_ago
    def clear_last_search_results(self: Any):
        """저장된 마지막 검색 결과 삭제"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM last_search_results")
            cursor.execute("DELETE FROM last_search_meta")
            conn.commit()


__all__ = ["LastSearchMixin"]



