"""Favorites domain operations for FlightDatabase."""

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

class FavoritesMixin:
    @staticmethod
    def _normalize_text(value: Any, upper: bool = False) -> str:
        text = str(value or "").strip()
        return text.upper() if upper else text
    @staticmethod
    def _normalize_int(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0
    def _build_favorite_dedup_key(self, flight_data: Dict[str, Any]) -> str:
        is_round_trip = bool(
            flight_data.get("is_round_trip")
            or flight_data.get("return_date")
            or flight_data.get("return_departure_time")
            or flight_data.get("return_arrival_time")
            or flight_data.get("return_airline")
        )
        parts = [
            self._normalize_text(flight_data.get("origin"), upper=True),
            self._normalize_text(flight_data.get("destination"), upper=True),
            self._normalize_text(flight_data.get("departure_date")),
            self._normalize_text(flight_data.get("return_date")),
            self._normalize_text(flight_data.get("airline"), upper=True),
            str(self._normalize_int(flight_data.get("price"))),
            self._normalize_text(flight_data.get("departure_time")),
            self._normalize_text(flight_data.get("arrival_time")),
            str(self._normalize_int(flight_data.get("stops"))),
            self._normalize_text(flight_data.get("return_airline"), upper=True),
            self._normalize_text(flight_data.get("return_departure_time")),
            self._normalize_text(flight_data.get("return_arrival_time")),
            str(self._normalize_int(flight_data.get("return_stops"))),
            str(self._normalize_int(flight_data.get("outbound_price"))),
            str(self._normalize_int(flight_data.get("return_price"))),
            "RT" if is_round_trip else "OW",
        ]
        return "|".join(parts)
    def add_favorite(self, flight_data: Dict[str, Any], search_params: Dict[str, Any] = None) -> int:
        """즐겨찾기 추가"""
        dedup_key = self._build_favorite_dedup_key(flight_data or {})
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO favorites 
                (airline, price, origin, destination, departure_date, return_date,
                 departure_time, arrival_time, stops, note, created_at, search_params, dedup_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                json.dumps(search_params or {}, ensure_ascii=False),
                dedup_key,
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
    def is_favorite_by_entry(self, flight_data: Dict[str, Any]) -> bool:
        """중복키 기준으로 즐겨찾기 존재 여부를 확인한다."""
        dedup_key = self._build_favorite_dedup_key(flight_data or {})
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM favorites WHERE dedup_key = ?", (dedup_key,))
            return cursor.fetchone()[0] > 0
    def is_favorite(self, airline: str, price: int, departure_time: str, origin: str, dest: str) -> bool:
        """하위 호환용 메서드. 내부적으로 dedup_key 기반 검사로 위임한다."""
        return self.is_favorite_by_entry(
            {
                "airline": airline,
                "price": price,
                "departure_time": departure_time,
                "origin": origin,
                "destination": dest,
            }
        )
    
    # ===== 가격 히스토리 =====

__all__ = ["FavoritesMixin"]
