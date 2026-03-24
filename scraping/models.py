"""Scraper data models."""

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass
class FlightResult:
    """항공권 검색 결과."""

    airline: str
    price: int  # 총 가격 (왕복 합산)
    currency: str = "KRW"
    departure_time: str = ""
    arrival_time: str = ""
    duration: str = ""
    stops: int = 0
    flight_number: str = ""
    source: str = "Interpark"

    # 귀국편 정보 (왕복인 경우)
    return_departure_time: str = ""
    return_arrival_time: str = ""
    return_duration: str = ""
    return_stops: int = 0
    is_round_trip: bool = False

    # 국내선용: 가는편/오는편 가격 분리
    outbound_price: int = 0
    return_price: int = 0
    return_airline: str = ""
    benefit_price: int = 0
    benefit_label: str = ""

    confidence: float = 0.0
    extraction_source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
