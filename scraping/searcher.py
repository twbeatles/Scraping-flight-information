"""High-level single-route searcher."""

import logging
from typing import Any, Callable, Dict, List, Optional

from scraping.models import FlightResult
from scraping.search_sources import InterparkAirSource, SearchSourceProtocol, create_search_source

logger = logging.getLogger("ScraperV2")


class FlightSearcher:
    """통합 항공권 검색 엔진."""

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
            result.confidence = 0.5
            result.extraction_source = "manual_extract"
        results.sort(key=lambda item: item.price if item.price > 0 else float("inf"))
        self.last_results = results
        return results

    def is_manual_mode(self) -> bool:
        return self.source.is_manual_mode()

    def close(self) -> None:
        self.source.close()

    def get_cheapest(self) -> Optional[FlightResult]:
        if self.last_results:
            return self.last_results[0]
        return None
