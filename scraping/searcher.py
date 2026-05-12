"""High-level single-route searcher."""

from collections import OrderedDict
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

import scraper_config
from scraping.models import FlightResult
from scraping.search_sources import InterparkAirSource, SearchSourceProtocol, create_search_source

logger = logging.getLogger("ScraperV2")


class FlightSearcher:
    """통합 항공권 검색 엔진."""

    _cache_lock = threading.Lock()
    _search_cache: "OrderedDict[tuple, tuple[float, List[Dict[str, Any]]]]" = OrderedDict()

    def __init__(self, telemetry_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.source: SearchSourceProtocol = create_search_source(
            InterparkAirSource.source_id,
            telemetry_callback=telemetry_callback,
        )
        self.scraper = getattr(self.source, "scraper", None)
        self.last_results: List[FlightResult] = []

    def search(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        cabin_class: str = "ECONOMY",
        max_results: int = 1000,
        progress_callback: Optional[Callable[[str], None]] = None,
        background_mode: bool = False,
        force_refresh: bool = False,
    ) -> List[FlightResult]:
        """항공권 검색 진입점."""

        def emit(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)
            logger.info(msg)

        cabin_label = {
            "ECONOMY": "이코노미",
            "BUSINESS": "비즈니스",
            "FIRST": "일등석",
        }.get(cabin_class.upper(), "이코노미")
        emit(f"🔍 {origin} → {destination} 항공권 검색 시작 ({cabin_label})")

        cache_key = self._build_cache_key(
            origin,
            destination,
            departure_date,
            return_date,
            adults,
            cabin_class,
            max_results,
        )
        cached_results = self._get_cached_results(cache_key, force_refresh=force_refresh)
        if cached_results is not None:
            self.last_results = cached_results
            if cached_results:
                cheapest = cached_results[0]
                emit(f"⚡ 캐시 사용: {len(cached_results)}개 결과, 최저가 {cheapest.price:,}원")
            else:
                emit("⚡ 캐시 사용: 결과 없음")
            return cached_results

        results = self.source.search(
            {
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date,
                "return_date": return_date,
                "adults": adults,
                "cabin_class": cabin_class,
                "max_results": max_results,
                "child": 0,
                "infant": 0,
            },
            emit,
            background_mode=background_mode,
        )
        self.last_results = results

        if results and not self.source.is_manual_mode():
            self._store_cached_results(cache_key, results)

        if results:
            cheapest = results[0]
            emit(f"✅ 검색 완료: {len(results)}개 발견, 최저가 {cheapest.price:,}원")
        elif self.source.is_manual_mode():
            emit("🖐️ 수동 모드 활성화 - 브라우저에서 결과 로딩 후 '추출' 버튼을 누르세요")
        else:
            emit("❌ 검색 결과 없음")

        return results

    def extract_manual(self) -> List[FlightResult]:
        """수동 모드에서 데이터 추출 재시도."""

        results = self.source.extract_manual()
        for result in results:
            if not result.extraction_source:
                result.extraction_source = "manual_extract"
            if result.extraction_source == "manual_extract":
                result.confidence = 0.5
        results.sort(key=lambda item: item.price if item.price > 0 else float("inf"))
        self.last_results = results
        return results

    def is_manual_mode(self) -> bool:
        return self.source.is_manual_mode()

    def get_manual_reason(self) -> str:
        scraper = getattr(self.source, "scraper", None)
        if scraper is None:
            return ""
        return str(getattr(scraper, "_manual_reason", "") or "")

    def close(self) -> None:
        self.source.close()

    def get_cheapest(self) -> Optional[FlightResult]:
        if self.last_results:
            return self.last_results[0]
        return None

    @staticmethod
    def _build_cache_key(
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str],
        adults: int,
        cabin_class: str,
        max_results: int,
    ) -> tuple:
        return (
            (origin or "").upper(),
            (destination or "").upper(),
            departure_date or "",
            return_date or "",
            int(adults or 1),
            (cabin_class or "ECONOMY").upper(),
            int(max_results or 0),
        )

    @classmethod
    def _prune_cache_locked(cls, now: float) -> None:
        ttl = max(1, int(getattr(scraper_config, "SEARCH_CACHE_TTL_SECONDS", 180)))
        max_entries = max(1, int(getattr(scraper_config, "SEARCH_CACHE_MAX_ENTRIES", 64)))

        expired_keys = [
            key for key, (saved_at, _) in cls._search_cache.items() if now - saved_at > ttl
        ]
        for key in expired_keys:
            cls._search_cache.pop(key, None)

        while len(cls._search_cache) > max_entries:
            cls._search_cache.popitem(last=False)

    @staticmethod
    def _deserialize_cached_results(payload: List[Dict[str, Any]]) -> List[FlightResult]:
        restored = []
        for row in payload:
            try:
                restored.append(FlightResult(**row))
            except Exception:
                continue
        restored.sort(key=lambda x: x.price if x.price > 0 else float("inf"))
        return restored

    @classmethod
    def _get_cached_results(
        cls,
        cache_key: tuple,
        *,
        force_refresh: bool = False,
    ) -> Optional[List[FlightResult]]:
        if force_refresh or not getattr(scraper_config, "ENABLE_SEARCH_CACHE", True):
            return None

        now = time.time()
        with cls._cache_lock:
            cls._prune_cache_locked(now)
            item = cls._search_cache.get(cache_key)
            if not item:
                return None
            saved_at, payload = item
            ttl = max(1, int(getattr(scraper_config, "SEARCH_CACHE_TTL_SECONDS", 180)))
            if now - saved_at > ttl:
                cls._search_cache.pop(cache_key, None)
                return None
            cls._search_cache.move_to_end(cache_key)
        return cls._deserialize_cached_results(payload)

    @classmethod
    def _store_cached_results(cls, cache_key: tuple, results: List[FlightResult]) -> None:
        if not results or not getattr(scraper_config, "ENABLE_SEARCH_CACHE", True):
            return

        payload = []
        for item in results:
            try:
                payload.append(item.to_dict())
            except Exception:
                continue
        if not payload:
            return

        now = time.time()
        with cls._cache_lock:
            cls._prune_cache_locked(now)
            cls._search_cache[cache_key] = (now, payload)
            cls._search_cache.move_to_end(cache_key)
            cls._prune_cache_locked(now)

    @classmethod
    def clear_cache(cls) -> None:
        with cls._cache_lock:
            cls._search_cache.clear()
