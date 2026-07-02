"""Internal search-source abstractions."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

import scraper_config
from core.search_params import normalize_search_params
from scraping.models import FlightResult
from scraping.playwright_scraper import PlaywrightScraper

SearchParams = Dict[str, Any]
ProgressEmitter = Optional[Callable[[str], None]]


def _normalize_interpark_params(params: SearchParams) -> Dict[str, Any]:
    normalized = normalize_search_params(
        {
            "origin": params.get("origin", ""),
            "dest": params.get("destination", params.get("dest", "")),
            "dep": params.get("departure_date", params.get("dep", "")),
            "ret": params.get("return_date", params.get("ret")),
            "adults": params.get("adults", 1),
            "cabin_class": params.get("cabin_class", "ECONOMY"),
            "is_domestic": params.get("is_domestic"),
        }
    )
    try:
        child = max(0, int(params.get("child", 0) or 0))
    except Exception:
        child = 0
    try:
        infant = max(0, int(params.get("infant", 0) or 0))
    except Exception:
        infant = 0
    return {
        "origin": normalized.get("origin", ""),
        "destination": normalized.get("dest", ""),
        "departure_date": normalized.get("dep", ""),
        "return_date": normalized.get("ret"),
        "adults": normalized.get("adults", 1),
        "cabin_class": normalized.get("cabin_class", "ECONOMY"),
        "child": child,
        "infant": infant,
        "max_results": params.get("max_results", 1000),
        "is_domestic": normalized.get("is_domestic", False),
    }


@runtime_checkable
class SearchSourceProtocol(Protocol):
    source_id: str
    metadata: Dict[str, Any]

    def build_search_url(self, params: SearchParams) -> str: ...

    def search(
        self,
        params: SearchParams,
        emit: ProgressEmitter = None,
        background_mode: bool = False,
    ) -> List[FlightResult]: ...

    def extract_manual(self) -> List[FlightResult]: ...

    def is_manual_mode(self) -> bool: ...

    def close(self) -> None: ...


class InterparkAirSource:
    """Runtime-backed Interpark Air source."""

    source_id = "interpark_air"
    metadata = {
        "display_name": "Interpark Air",
        "status": "active",
        "base_url": scraper_config.INTERPARK_SEARCH_URL_BASE,
        "supports_runtime_search": True,
    }

    def __init__(self, telemetry_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.scraper = PlaywrightScraper(telemetry_callback=telemetry_callback)

    def build_search_url(self, params: SearchParams) -> str:
        normalized = _normalize_interpark_params(params)
        return scraper_config.build_interpark_search_url(
            normalized["origin"],
            normalized["destination"],
            normalized["departure_date"],
            normalized["return_date"],
            cabin=normalized["cabin_class"],
            adults=normalized["adults"],
            infant=normalized["infant"],
            child=normalized["child"],
        )

    def search(
        self,
        params: SearchParams,
        emit: ProgressEmitter = None,
        background_mode: bool = False,
    ) -> List[FlightResult]:
        normalized = _normalize_interpark_params(params)
        return self.scraper.search(
            normalized["origin"],
            normalized["destination"],
            normalized["departure_date"],
            normalized["return_date"],
            adults=int(normalized["adults"] or 1),
            cabin_class=str(normalized["cabin_class"] or "ECONOMY"),
            max_results=int(normalized.get("max_results", 1000) or 1000),
            emit=emit,
            background_mode=background_mode,
            child=int(normalized.get("child", 0) or 0),
            infant=int(normalized.get("infant", 0) or 0),
        )

    def extract_manual(self) -> List[FlightResult]:
        return self.scraper.extract_from_current_page()

    def is_manual_mode(self) -> bool:
        return self.scraper.is_manual_mode()

    def close(self) -> None:
        self.scraper.close()


class InterparkTicketSource:
    """Placeholder adapter for future Interpark/NOL ticket integration."""

    source_id = "interpark_ticket"
    metadata = {
        "display_name": "Interpark Ticket",
        "status": "inactive",
        "base_url": "https://nol.interpark.com/ticket",
        "legacy_url": "https://tickets.interpark.com/",
        "supports_runtime_search": False,
    }

    def build_search_url(self, params: SearchParams) -> str:
        return self.metadata["base_url"]

    def search(
        self,
        params: SearchParams,
        emit: ProgressEmitter = None,
        background_mode: bool = False,
    ) -> List[FlightResult]:
        raise NotImplementedError("Interpark ticket search adapter is not implemented yet.")

    def extract_manual(self) -> List[FlightResult]:
        raise NotImplementedError("Interpark ticket manual extraction is not implemented yet.")

    def is_manual_mode(self) -> bool:
        return False

    def close(self) -> None:
        return None


SEARCH_SOURCE_TYPES = {
    InterparkAirSource.source_id: InterparkAirSource,
    InterparkTicketSource.source_id: InterparkTicketSource,
}
ACTIVE_SEARCH_SOURCE_IDS = (InterparkAirSource.source_id,)


def create_search_source(
    source_id: str = InterparkAirSource.source_id,
    telemetry_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> SearchSourceProtocol:
    source_type = SEARCH_SOURCE_TYPES.get(source_id)
    if source_type is None:
        raise KeyError(f"Unknown search source: {source_id}")
    if source_type is InterparkAirSource:
        return source_type(telemetry_callback=telemetry_callback)
    return source_type()