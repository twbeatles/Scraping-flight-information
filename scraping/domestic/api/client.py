"""Domestic result-page HTTP client (SRP: page fetch only)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from scraping.interpark.adapter import get_interpark_adapter

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


def _fetch_domestic_search_page(
    scraper: "PlaywrightScraper",
    search_key: str,
    *,
    page_number: int,
    page_size: int,
    cabin: str,
) -> Dict[str, Any]:
    from scraping.domestic import api as api_package

    adapter = get_interpark_adapter()
    url = adapter.build_domestic_result_url(search_key)
    payload = api_package.page_fetch_json(
        scraper,
        url,
        method="POST",
        body=adapter.domestic_result_request_body(
            page_number=page_number,
            page_size=page_size,
            cabin=cabin,
        ),
    )
    return payload if isinstance(payload, dict) else {}
