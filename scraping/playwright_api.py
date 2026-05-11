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
    except Exception:
        return {}
    if not isinstance(result, dict):
        return {}
    _record_api_meta(scraper, result)
    return result


def get_api_meta(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return metadata attached by page_fetch_json, if present."""

    meta = payload.get("__flightbot_api_meta")
    return meta if isinstance(meta, dict) else {}


def _record_api_meta(scraper: "PlaywrightScraper", payload: Dict[str, Any]) -> None:
    meta = get_api_meta(payload)
    if not meta:
        return
    clean_meta = {
        "status": int(meta.get("status") or 0),
        "ok": bool(meta.get("ok")),
        "method": str(meta.get("method") or ""),
        "url": _sanitize_resource_url(str(meta.get("url") or "")),
        "payload_keys": [str(item) for item in meta.get("payload_keys", [])[:20]],
    }
    if meta.get("error"):
        clean_meta["error"] = str(meta.get("error"))
    setattr(scraper, "_last_api_meta", clean_meta)
    metrics = getattr(scraper, "_search_metrics", None)
    if isinstance(metrics, dict):
        recent = metrics.setdefault("api_recent", [])
        if isinstance(recent, list):
            recent.append(clean_meta)
            del recent[:-5]
        if not clean_meta["ok"]:
            failures = metrics.setdefault("api_failures", [])
            if isinstance(failures, list):
                failures.append(clean_meta)
                del failures[:-5]


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
            .filter((name) => name.includes({json.dumps(pattern)}));
        const seen = [];
        for (const name of resources) {{
            const start = name.indexOf({json.dumps(prefix)});
            if (start < 0) continue;
            const tail = name.slice(start);
            const key = tail.split(/[/?#]/)[0];
            if (!seen.includes(key)) {{
                seen.push(key);
            }}
        }}
        return seen;
    }}
    """
    try:
        result = scraper.page.evaluate(script)
    except Exception:
        return []
    if not isinstance(result, list):
        return []
    return [str(item) for item in result if str(item).strip()]


def recent_api_resource_urls(
    scraper: "PlaywrightScraper",
    *,
    trip_kind: str,
    limit: int = 5,
) -> List[str]:
    """Return sanitized recent Interpark API resource URLs for diagnostics."""

    if not scraper.page:
        return []

    pattern = "/domestic/flights/search/" if trip_kind == "domestic" else "/international/flights/search/v2/"
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


def find_latest_search_key(
    scraper: "PlaywrightScraper",
    *,
    trip_kind: str,
) -> str:
    keys = find_search_keys(scraper, trip_kind=trip_kind)
    return keys[-1] if keys else ""


def _sanitize_resource_url(url: str) -> str:
    if not url:
        return ""
    base = url.split("#", 1)[0].split("?", 1)[0]
    for prefix in ("DOMESTIC::", "INTERNATIONAL::"):
        if prefix in base:
            start = base.index(prefix) + len(prefix)
            end = start
            while end < len(base) and base[end] not in "/?#":
                end += 1
            token = base[start:end]
            if len(token) > 14:
                base = base[:start] + token[:6] + "..." + token[-4:] + base[end:]
    return base[-220:]
