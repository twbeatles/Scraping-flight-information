"""Interpark site/API adapter configuration."""

from __future__ import annotations

from dataclasses import dataclass

from scraping.interpark.runtime import INTERPARK_INTERNATIONAL_API_VERSION


@dataclass(frozen=True)
class InterparkAdapterConfig:
    """Canonical Interpark Air endpoints and API path fragments."""

    site_origin: str = "https://travel.interpark.com"
    search_url_base: str = "https://travel.interpark.com/air/search"
    air_api_base: str = "https://travel.interpark.com/air/air-api/inpark-air-web-api"
    international_api_version: str = INTERPARK_INTERNATIONAL_API_VERSION
    domestic_key_prefix: str = "DOMESTIC::"
    international_key_prefix: str = "INTERNATIONAL::"

    @property
    def domestic_search_api_path(self) -> str:
        return "/domestic/flights/search/"

    @property
    def international_search_api_path(self) -> str:
        version = (self.international_api_version or "v2").strip("/")
        return f"/international/flights/search/{version}/"

    @property
    def international_initial_search_api_path(self) -> str:
        return "/flights/search/"


DEFAULT_INTERPARK_ADAPTER = InterparkAdapterConfig()


def get_interpark_adapter() -> InterparkAdapterConfig:
    return DEFAULT_INTERPARK_ADAPTER