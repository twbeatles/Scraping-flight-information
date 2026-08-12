"""Interpark site/API adapter configuration."""

from __future__ import annotations

from dataclasses import dataclass

from scraping.interpark.contract.schemas import (
    DEFAULT_API_PAGE_SIZE,
    DOMESTIC_CABIN_FILTER_KEY,
    DOMESTIC_RESULT_ITEM_BUCKETS,
    ERROR_CODE_FIELD,
    ERROR_MESSAGE_FIELDS,
    INTERNATIONAL_RESULT_ITEM_BUCKETS,
    PAGE_CURRENT_FIELD,
    PAGE_META_KEY,
    PAGE_NUMBER_FIELD,
    PAGE_SIZE_FIELD,
    PAGE_TOTAL_COUNT_FIELD,
    SEARCH_KEY_FIELDS,
    STATUS_COMPLETE_VALUE,
    STATUS_FIELD,
    STATUS_PATH_SUFFIX,
)
from scraping.interpark.runtime import INTERPARK_INTERNATIONAL_API_VERSION


@dataclass(frozen=True)
class InterparkAdapterConfig:
    """Canonical Interpark Air endpoints, path fragments, and payload schema."""

    site_origin: str = "https://travel.interpark.com"
    search_url_base: str = "https://travel.interpark.com/air/search"
    air_api_base: str = "https://travel.interpark.com/air/air-api/inpark-air-web-api"
    international_api_version: str = INTERPARK_INTERNATIONAL_API_VERSION
    domestic_key_prefix: str = "DOMESTIC::"
    international_key_prefix: str = "INTERNATIONAL::"

    # Payload / status schema (single source for extractors).
    search_key_fields: tuple[str, ...] = SEARCH_KEY_FIELDS
    domestic_result_buckets: tuple[str, ...] = DOMESTIC_RESULT_ITEM_BUCKETS
    international_result_buckets: tuple[str, ...] = INTERNATIONAL_RESULT_ITEM_BUCKETS
    page_meta_key: str = PAGE_META_KEY
    page_total_count_field: str = PAGE_TOTAL_COUNT_FIELD
    page_size_field: str = PAGE_SIZE_FIELD
    page_number_field: str = PAGE_NUMBER_FIELD
    page_current_field: str = PAGE_CURRENT_FIELD
    status_path_suffix: str = STATUS_PATH_SUFFIX
    status_field: str = STATUS_FIELD
    status_complete_value: str = STATUS_COMPLETE_VALUE
    error_code_field: str = ERROR_CODE_FIELD
    error_message_fields: tuple[str, ...] = ERROR_MESSAGE_FIELDS
    domestic_cabin_filter_key: str = DOMESTIC_CABIN_FILTER_KEY
    default_api_page_size: int = DEFAULT_API_PAGE_SIZE

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

    def build_domestic_result_url(self, search_key: str) -> str:
        return f"{self.air_api_base}{self.domestic_search_api_path}{search_key}"

    def build_international_result_url(self, search_key: str) -> str:
        return f"{self.air_api_base}{self.international_search_api_path}{search_key}"

    def build_international_status_url(self, search_key: str) -> str:
        suffix = self.status_path_suffix if self.status_path_suffix.startswith("/") else f"/{self.status_path_suffix}"
        return f"{self.build_international_result_url(search_key)}{suffix}"

    def domestic_result_request_body(
        self,
        *,
        page_number: int,
        page_size: int,
        cabin: str,
    ) -> dict:
        return {
            self.page_number_field: page_number,
            self.page_size_field: page_size,
            "filter": {
                self.domestic_cabin_filter_key: [cabin],
            },
        }

    def international_result_request_body(
        self,
        *,
        page_number: int,
        page_size: int,
    ) -> dict:
        return {
            self.page_number_field: page_number,
            self.page_size_field: page_size,
            "filter": {},
        }


DEFAULT_INTERPARK_ADAPTER = InterparkAdapterConfig()


def get_interpark_adapter() -> InterparkAdapterConfig:
    return DEFAULT_INTERPARK_ADAPTER
