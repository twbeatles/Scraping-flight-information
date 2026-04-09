"""Shared Playwright page/API helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


def page_fetch_json(
    scraper: "PlaywrightScraper",
    url: str,
    *,
    method: str = "GET",
    body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Fetch JSON within the page context so same-origin cookies/session are reused."""

    if not scraper.page:
        return {}

    method_json = json.dumps(method.upper())
    url_json = json.dumps(url)
    body_expr = "undefined" if body is None else json.dumps(json.dumps(body, ensure_ascii=False))
    headers_expr = "{}" if body is None else '{"content-type":"application/json"}'
    script = f"""
    async () => {{
        try {{
            const response = await fetch({url_json}, {{
                method: {method_json},
                credentials: 'include',
                headers: {headers_expr},
                body: {body_expr} === undefined ? undefined : JSON.parse({body_expr}),
            }});
            const text = await response.text();
            try {{
                return JSON.parse(text || "{{}}");
            }} catch (error) {{
                return {{
                    status: response.status,
                    ok: response.ok,
                    raw: text,
                }};
            }}
        }} catch (error) {{
            return {{
                ok: false,
                error: String(error),
            }};
        }}
    }}
    """
    result = scraper.page.evaluate(script)
    return result if isinstance(result, dict) else {}


def find_search_keys(
    scraper: "PlaywrightScraper",
    *,
    trip_kind: str,
) -> List[str]:
    """Return seen search keys from resource timing entries in order of first appearance."""

    if not scraper.page:
        return []

    prefix = "DOMESTIC::" if trip_kind == "domestic" else "INTERNATIONAL::"
    pattern = "/domestic/flights/search/" if trip_kind == "domestic" else "/international/flights/search/v2/"
    script = f"""
    () => {{
        const resources = performance.getEntriesByType('resource')
            .map((entry) => String(entry.name || ''))
            .filter((name) => name.includes({json.dumps(pattern)}) && name.includes('/status'));
        const seen = [];
        for (const name of resources) {{
            const start = name.indexOf({json.dumps(prefix)});
            if (start < 0) continue;
            const tail = name.slice(start);
            const key = tail.split('/')[0];
            if (!seen.includes(key)) {{
                seen.push(key);
            }}
        }}
        return seen;
    }}
    """
    result = scraper.page.evaluate(script)
    if not isinstance(result, list):
        return []
    return [str(item) for item in result if str(item).strip()]


def find_latest_search_key(
    scraper: "PlaywrightScraper",
    *,
    trip_kind: str,
) -> str:
    keys = find_search_keys(scraper, trip_kind=trip_kind)
    return keys[-1] if keys else ""
