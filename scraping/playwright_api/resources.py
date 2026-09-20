"""Performance-resource URL diagnostics (SRP: resource URL reads only)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, List

from scraping.interpark.adapter import get_interpark_adapter
from scraping.playwright_api.meta import _sanitize_resource_url

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


def recent_api_resource_urls(
    scraper: "PlaywrightScraper",
    *,
    trip_kind: str,
    limit: int = 5,
) -> List[str]:
    """Return sanitized recent Interpark API resource URLs for diagnostics."""

    if not scraper.page:
        return []

    adapter = get_interpark_adapter()
    pattern = (
        adapter.domestic_search_api_path
        if trip_kind == "domestic"
        else adapter.international_search_api_path
    )
    script = f"""
    () => performance.getEntriesByType('resource')
        .map((entry) => String(entry.name || ''))
        .filter((name) => name.includes({json.dumps(pattern)}))
        .slice(-{max(int(limit), 1)})
    """
    try:
        result = scraper.page.evaluate(script)
    except Exception:
        return []
    if not isinstance(result, list):
        return []
    return [_sanitize_resource_url(str(item)) for item in result if str(item).strip()]
