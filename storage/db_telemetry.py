"""Telemetry persistence and retention operations."""

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

class TelemetryMixin:
    def _rotate_telemetry_jsonl_if_needed(self: Any):
        try:
            if not os.path.exists(self.telemetry_log_path):
                return
            if os.path.getsize(self.telemetry_log_path) < int(self.telemetry_jsonl_max_bytes):
                return

            max_files = max(1, int(self.telemetry_jsonl_max_files))
            if max_files == 1:
                os.remove(self.telemetry_log_path)
                return

            max_backup_index = max_files - 1
            oldest = f"{self.telemetry_log_path}.{max_backup_index}"
            if os.path.exists(oldest):
                os.remove(oldest)

            for idx in range(max_backup_index - 1, 0, -1):
                src = f"{self.telemetry_log_path}.{idx}"
                dst = f"{self.telemetry_log_path}.{idx + 1}"
                if os.path.exists(src):
                    os.replace(src, dst)

            os.replace(self.telemetry_log_path, f"{self.telemetry_log_path}.1")
        except Exception as e:
            logger.debug(f"Failed to rotate telemetry jsonl: {e}")
    def _append_telemetry_jsonl(self: Any, event: Dict[str, Any]):
        try:
            with self._telemetry_file_lock:
                self._rotate_telemetry_jsonl_if_needed()
                with open(self.telemetry_log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        except Exception as e:
            logger.debug(f"Failed to append telemetry jsonl: {e}")
    def log_telemetry_event(
        self: Any,
        event_type: str,
        success: bool = True,
        error_code: str = "",
        route: str = "",
        manual_mode: bool = False,
        selector_name: str = "",
        extraction_source: str = "",
        confidence: float = 0.0,
        duration_ms: Optional[int] = None,
        result_count: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        details_json = json.dumps(details or {}, ensure_ascii=False, default=str)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO telemetry_events
                (event_time, event_type, success, error_code, route, manual_mode,
                 selector_name, extraction_source, confidence, duration_ms, result_count, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    event_type,
                    1 if success else 0,
                    error_code or "",
                    route or "",
                    1 if manual_mode else 0,
                    selector_name or "",
                    extraction_source or "",
                    float(confidence or 0.0),
                    duration_ms,
                    result_count,
                    details_json,
                ),
            )
            conn.commit()

        event = {
            "event_time": now,
            "event_type": event_type,
            "success": bool(success),
            "error_code": error_code or "",
            "route": route or "",
            "manual_mode": bool(manual_mode),
            "selector_name": selector_name or "",
            "extraction_source": extraction_source or "",
            "confidence": float(confidence or 0.0),
            "duration_ms": duration_ms,
            "result_count": result_count,
            "details": details or {},
        }
        self._append_telemetry_jsonl(event)
    def get_telemetry_summary(self: Any, hours: int = 24) -> Dict[str, Any]:
        cutoff = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT COUNT(*), SUM(success), SUM(manual_mode) FROM telemetry_events WHERE event_time >= ?",
                (cutoff,),
            )
            row = cursor.fetchone() or (0, 0, 0)
            total = int(row[0] or 0)
            success_count = int(row[1] or 0)
            manual_count = int(row[2] or 0)

            cursor.execute(
                """
                SELECT error_code, COUNT(*) as cnt
                FROM telemetry_events
                WHERE event_time >= ? AND COALESCE(error_code, '') != ''
                GROUP BY error_code
                ORDER BY cnt DESC
                LIMIT 5
                """,
                (cutoff,),
            )
            top_errors = [{"error_code": r[0], "count": int(r[1])} for r in cursor.fetchall()]

        return {
            "total_events": total,
            "success_events": success_count,
            "success_rate": (success_count * 100.0 / total) if total > 0 else 0.0,
            "manual_mode_rate": (manual_count * 100.0 / total) if total > 0 else 0.0,
            "top_errors": top_errors,
        }
    def get_selector_health(self: Any, limit: int = 200) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT selector_name, success
                FROM telemetry_events
                WHERE event_type = 'selector_wait'
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()

        if not rows:
            return {"overall_success_rate": 0.0, "sample_count": 0, "by_selector": {}}

        total = len(rows)
        success_count = sum(int(r[1] or 0) for r in rows)
        by_selector: Dict[str, Dict[str, Any]] = {}
        for selector_name, success in rows:
            name = selector_name or "(unknown)"
            item = by_selector.setdefault(name, {"total": 0, "success": 0, "success_rate": 0.0})
            item["total"] += 1
            item["success"] += int(success or 0)

        for item in by_selector.values():
            item["success_rate"] = (item["success"] * 100.0 / item["total"]) if item["total"] > 0 else 0.0

        return {
            "overall_success_rate": (success_count * 100.0 / total) if total > 0 else 0.0,
            "sample_count": total,
            "by_selector": by_selector,
        }
    def cleanup_old_data(self: Any, days: int = 90, telemetry_days: int = TELEMETRY_DB_RETENTION_DAYS):
        """오래된 데이터 정리"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        telemetry_cutoff = (datetime.now() - timedelta(days=telemetry_days)).strftime("%Y-%m-%d %H:%M:%S")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM price_history WHERE recorded_at < ?", (cutoff,))
            cursor.execute("DELETE FROM search_logs WHERE searched_at < ?", (cutoff,))
            cursor.execute("DELETE FROM telemetry_events WHERE event_time < ?", (telemetry_cutoff,))
            conn.commit()
    def optimize(self: Any):
        """데이터베이스 최적화 (VACUUM)"""
        try:
            with self._get_connection() as conn:
                conn.execute("VACUUM")
            logger.info("Database optimized (VACUUM completed)")
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")

    # ===== 가격 알림 =====

__all__ = ["TelemetryMixin"]



