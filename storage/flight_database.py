"""Composed FlightDatabase implementation."""

import sqlite3
import os
import sys
import logging
import threading
from typing import List

from storage.schema import DatabaseSchemaMixin
from storage.db_favorites import FavoritesMixin
from storage.db_history_logs import HistoryLogsMixin
from storage.db_telemetry import TelemetryMixin
from storage.db_alerts import AlertsMixin
from storage.db_last_search import LastSearchMixin
from storage.models import TELEMETRY_JSONL_MAX_BYTES, TELEMETRY_JSONL_MAX_FILES

logger = logging.getLogger(__name__)


class FlightDatabase(
    DatabaseSchemaMixin,
    FavoritesMixin,
    HistoryLogsMixin,
    TelemetryMixin,
    AlertsMixin,
    LastSearchMixin,
):
    """Flight data persistence with thread-local SQLite connections."""

    _local = threading.local()
    _registry_lock = threading.Lock()
    _all_connections: List[sqlite3.Connection] = []

    def __init__(self, db_path: str | None = None):
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

        if getattr(sys, 'frozen', False):
            app_data = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'FlightBot')
            log_dir = os.path.join(app_data, "logs")
        else:
            log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        self.telemetry_log_path = os.path.join(log_dir, "flightbot_events.jsonl")
        self._telemetry_file_lock = threading.Lock()
        self.telemetry_jsonl_max_bytes = TELEMETRY_JSONL_MAX_BYTES
        self.telemetry_jsonl_max_files = TELEMETRY_JSONL_MAX_FILES

        logger.info(f"Database path: {self.db_path}")
        self._init_db()
        self._migrate_schema_if_needed()
        self._backfill_favorite_dedup_keys()
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
            with FlightDatabase._registry_lock:
                FlightDatabase._all_connections.append(conn)
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
                with FlightDatabase._registry_lock:
                    FlightDatabase._all_connections.append(conn)
        
        return conn
    def close_all_connections(self):
        """열려 있는 SQLite 연결을 모두 닫는다."""
        with FlightDatabase._registry_lock:
            conns = list(FlightDatabase._all_connections)
            FlightDatabase._all_connections.clear()

        for conn in conns:
            try:
                conn.close()
            except Exception:
                pass

        if hasattr(FlightDatabase._local, "connections"):
            FlightDatabase._local.connections = {}
    def close(self):
        self.close_all_connections()
    
    # ===== 즐겨찾기 =====
