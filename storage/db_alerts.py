"""Price alert operations for FlightDatabase."""

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

class AlertsMixin:
    def add_price_alert(
        self,
        origin: str,
        dest: str,
        dep_date: str,
        return_date: str,
        target_price: int,
        cabin_class: str = "ECONOMY",
    ) -> int:
        """가격 알림 추가"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO price_alerts 
                (origin, destination, departure_date, return_date, target_price, cabin_class, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                origin, dest, dep_date, return_date, target_price, (cabin_class or "ECONOMY"),
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

__all__ = ["AlertsMixin"]
