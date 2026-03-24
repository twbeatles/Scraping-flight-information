"""Internal search-source abstractions."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

import scraper_config
from scraping.models import FlightResult
from scraping.playwright_scraper import PlaywrightScraper

SearchParams = Dict[str, Any]
ProgressEmitter = Optional[Callable[[str], None]]


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
        "base_url": scraper_config.INTERPARK_SEARCH_URL_BASE,
        "supports_runtime_search": True,
    }

    def __init__(self, telemetry_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.scraper = PlaywrightScraper(telemetry_callback=telemetry_callback)

    def build_search_url(self, params: SearchParams) -> str:
        return scraper_config.build_interpark_search_url(
            params.get("origin", ""),
            params.get("destination", ""),
            params.get("departure_date", ""),
            params.get("return_date"),
            cabin=params.get("cabin_class", "ECONOMY"),
            adults=params.get("adults", 1),
            infant=params.get("infant", 0),
            child=params.get("child", 0),
        )

    def search(
        self,
        params: SearchParams,
        emit: ProgressEmitter = None,
        background_mode: bool = False,
    ) -> List[FlightResult]:
        return self.scraper.search(
            params.get("origin", ""),
            params.get("destination", ""),
            params.get("departure_date", ""),
            params.get("return_date"),
            adults=int(params.get("adults", 1) or 1),
            cabin_class=str(params.get("cabin_class", "ECONOMY") or "ECONOMY"),
            max_results=int(params.get("max_results", 1000) or 1000),
            emit=emit,
            background_mode=background_mode,
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
