"""Interpark Air API payload field contracts.

Keep response/request field names here so extractors do not hardcode site schema.
"""

from __future__ import annotations

# Search-key fields observed on initial/result API payloads.
SEARCH_KEY_FIELDS: tuple[str, ...] = ("key", "searchKey", "search_key")

# Result list buckets by trip kind.
DOMESTIC_RESULT_ITEM_BUCKETS: tuple[str, ...] = ("items",)
INTERNATIONAL_RESULT_ITEM_BUCKETS: tuple[str, ...] = ("bestFares", "contents")

# Shared page metadata object and fields.
PAGE_META_KEY: str = "page"
PAGE_TOTAL_COUNT_FIELD: str = "totalCount"
PAGE_SIZE_FIELD: str = "pageSize"
PAGE_NUMBER_FIELD: str = "pageNumber"
PAGE_CURRENT_FIELD: str = "currentPage"

# International async search status.
STATUS_PATH_SUFFIX: str = "/status"
STATUS_COMPLETE_VALUE: str = "COMPLETE"
STATUS_FIELD: str = "status"

# Common error-ish payload fields used for telemetry.
ERROR_CODE_FIELD: str = "code"
ERROR_MESSAGE_FIELDS: tuple[str, ...] = ("message", "title")

# Domestic request filter shape.
DOMESTIC_CABIN_FILTER_KEY: str = "byCabins"

# Default page size used when the API does not advertise one.
DEFAULT_API_PAGE_SIZE: int = 20
