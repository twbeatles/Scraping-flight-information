"""Schema and migration routines for FlightDatabase."""

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

class DatabaseSchemaMixin:
    def _init_db(self):
        """데이터베이스 및 테이블 초기화"""
        conn = sqlite3.connect(self.db_path)
        try:
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
                    search_params TEXT DEFAULT '{}',
                    dedup_key TEXT DEFAULT ''
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
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fav_dedup_key ON favorites(dedup_key)")
            
            # 가격 알림 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    departure_date TEXT NOT NULL,
                    return_date TEXT,
                    target_price INTEGER NOT NULL,
                    cabin_class TEXT DEFAULT 'ECONOMY',
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
                    return_airline TEXT,
                    confidence REAL DEFAULT 0.0,
                    extraction_source TEXT DEFAULT ''
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

            # 텔레메트리 이벤트 테이블 (관측성)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetry_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_time TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    error_code TEXT,
                    route TEXT,
                    manual_mode INTEGER DEFAULT 0,
                    selector_name TEXT,
                    extraction_source TEXT,
                    confidence REAL DEFAULT 0.0,
                    duration_ms INTEGER,
                    result_count INTEGER,
                    details_json TEXT DEFAULT '{}'
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tel_time ON telemetry_events(event_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tel_type ON telemetry_events(event_type)")
            
            conn.commit()
        finally:
            conn.close()
    def _migrate_schema_if_needed(self):
        """기존 DB를 안전하게 최신 스키마로 보강."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            def ensure_column(table: str, column: str, definition: str):
                cursor.execute(f"PRAGMA table_info({table})")
                columns = {row[1] for row in cursor.fetchall()}
                if column not in columns:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

            ensure_column("price_alerts", "cabin_class", "TEXT DEFAULT 'ECONOMY'")
            ensure_column("last_search_results", "confidence", "REAL DEFAULT 0.0")
            ensure_column("last_search_results", "extraction_source", "TEXT DEFAULT ''")
            ensure_column("favorites", "dedup_key", "TEXT DEFAULT ''")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fav_dedup_key ON favorites(dedup_key)")

            conn.commit()
        finally:
            conn.close()
    def _backfill_favorite_dedup_keys(self):
        """Legacy favorites created before dedup_key migration are backfilled once."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, airline, price, origin, destination, departure_date, return_date,
                       departure_time, arrival_time, stops
                FROM favorites
                WHERE COALESCE(dedup_key, '') = ''
                """
            )
            rows = cursor.fetchall()
            if not rows:
                return

            updates = []
            for row in rows:
                row_dict = dict(row)
                updates.append((self._build_favorite_dedup_key(row_dict), int(row_dict["id"])))

            cursor.executemany("UPDATE favorites SET dedup_key = ? WHERE id = ?", updates)
            conn.commit()

__all__ = ["DatabaseSchemaMixin"]
