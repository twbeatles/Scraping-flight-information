"""Database domain models and constants."""

from dataclasses import dataclass
from typing import Optional

TELEMETRY_DB_RETENTION_DAYS = 30
TELEMETRY_JSONL_MAX_BYTES = 10 * 1024 * 1024
TELEMETRY_JSONL_MAX_FILES = 5


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
    dedup_key: str = ""


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
    cabin_class: str = "ECONOMY"
