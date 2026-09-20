"""In-page JSON fetching with shared session (SRP: fetch only)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Dict, Optional

from scraping.interpark.adapter import get_interpark_adapter
from scraping.playwright_api.cache import cache_search_key
from scraping.playwright_api.keys import extract_search_key_from_payload, extract_search_key_from_url
from scraping.playwright_api.meta import _record_api_meta, get_api_meta

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
                body: {body_expr},
            }});
            const text = await response.text();
            const meta = {{
                status: response.status,
                ok: response.ok,
                url: response.url || {url_json},
                method: {method_json},
            }};
            try {{
                const parsed = JSON.parse(text || "{{}}");
                if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {{
                    parsed.__flightbot_api_meta = {{
                        ...meta,
                        payload_keys: Object.keys(parsed).slice(0, 20),
                    }};
                    return parsed;
                }}
                return {{
                    data: parsed,
                    __flightbot_api_meta: {{
                        ...meta,
                        payload_keys: ['data'],
                    }},
                }};
            }} catch (error) {{
                return {{
                    status: response.status,
                    ok: response.ok,
                    raw: text,
                    __flightbot_api_meta: {{
                        ...meta,
                        payload_keys: ['raw'],
                    }},
                }};
            }}
        }} catch (error) {{
            return {{
                ok: false,
                error: String(error),
                __flightbot_api_meta: {{
                    status: 0,
                    ok: false,
                    url: {url_json},
                    method: {method_json},
                    error: String(error),
                    payload_keys: ['error'],
                }},
            }};
        }}
    }}
    """
    try:
        result = scraper.page.evaluate(script)
    except Exception as exc:
        failure = {
            "ok": False,
            "error": str(exc),
            "__flightbot_api_meta": {
                "status": 0,
                "ok": False,
                "url": url,
                "method": method.upper(),
                "error": str(exc),
                "payload_keys": ["error"],
            },
        }
        _record_api_meta(scraper, failure)
        return failure
    if not isinstance(result, dict):
        failure = {
            "ok": False,
            "error": "non_dict_payload",
            "__flightbot_api_meta": {
                "status": 0,
                "ok": False,
                "url": url,
                "method": method.upper(),
                "error": "non_dict_payload",
                "payload_keys": ["error"],
            },
        }
        _record_api_meta(scraper, failure)
        return failure
    _record_api_meta(scraper, result)
    meta = get_api_meta(result)
    if meta and not bool(meta.get("ok", True)):
        metrics = getattr(scraper, "_search_metrics", None)
        if isinstance(metrics, dict):
            metrics["last_api_http_ok"] = False
            metrics["last_api_http_status"] = int(meta.get("status") or 0)
    else:
        metrics = getattr(scraper, "_search_metrics", None)
        if isinstance(metrics, dict):
            metrics["last_api_http_ok"] = True
            if meta:
                metrics["last_api_http_status"] = int(meta.get("status") or 0)
    _maybe_cache_search_key_from_fetch(scraper, url, result)
    return result


def _maybe_cache_search_key_from_fetch(
    scraper: "PlaywrightScraper",
    url: str,
    payload: Dict[str, Any],
) -> None:
    adapter = get_interpark_adapter()
    payload_key = extract_search_key_from_payload(payload)
    if payload_key:
        if adapter.domestic_search_api_path in url or payload_key.startswith(adapter.domestic_key_prefix):
            cache_search_key(scraper, trip_kind="domestic", key=payload_key)
        if adapter.international_search_api_path in url or payload_key.startswith(adapter.international_key_prefix):
            cache_search_key(scraper, trip_kind="international", key=payload_key)
        return

    trip_kind, token = extract_search_key_from_url(url, adapter=adapter)
    if trip_kind and token:
        cache_search_key(scraper, trip_kind=trip_kind, key=token)
