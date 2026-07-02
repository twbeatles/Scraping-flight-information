"""Shared Playwright page/API helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from scraping.interpark.adapter import InterparkAdapterConfig, get_interpark_adapter

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


def _ensure_search_key_cache(scraper: "PlaywrightScraper") -> Dict[str, List[str]]:
    cache = getattr(scraper, "_api_search_key_cache", None)
    if not isinstance(cache, dict):
        cache = {"domestic": [], "international": []}
        scraper._api_search_key_cache = cache
    return cache


def cache_search_key(scraper: "PlaywrightScraper", *, trip_kind: str, key: str) -> None:
    normalized = str(key or "").strip()
    if not normalized:
        return
    bucket = _ensure_search_key_cache(scraper).setdefault(trip_kind, [])
    if normalized not in bucket:
        bucket.append(normalized)


def get_cached_search_keys(scraper: "PlaywrightScraper", *, trip_kind: str) -> List[str]:
    cache = _ensure_search_key_cache(scraper)
    values = cache.get(trip_kind, [])
    return [str(item) for item in values if str(item).strip()]


def extract_search_key_from_url(
    url: str,
    *,
    adapter: InterparkAdapterConfig | None = None,
) -> Tuple[str, str]:
    """Return `(trip_kind, key)` parsed from an Interpark API URL."""

    config = adapter or get_interpark_adapter()
    text = str(url or "")
    if not text:
        return "", ""

    for trip_kind, prefix, path in (
        ("domestic", config.domestic_key_prefix, config.domestic_search_api_path),
        ("international", config.international_key_prefix, config.international_search_api_path),
    ):
        if prefix in text:
            start = text.index(prefix)
            token = text[start:].split("/")[0].split("?")[0]
            if token:
                return trip_kind, token
        if path in text:
            tail = text.split(path, 1)[-1]
            token = tail.split("/")[0].split("?")[0]
            if token.startswith(prefix):
                return trip_kind, token
    return "", ""


def extract_search_key_from_payload(payload: Dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        return ""
    for field in ("key", "searchKey", "search_key"):
        value = str(payload.get(field) or "").strip()
        if value:
            return value
    return ""


def find_search_keys(
    scraper: "PlaywrightScraper",
    *,
    trip_kind: str,
) -> List[str]:
    """Return search keys from cache and performance resources in stable order."""

    keys: List[str] = []
    for cached in get_cached_search_keys(scraper, trip_kind=trip_kind):
        if cached not in keys:
            keys.append(cached)
    for discovered in find_search_keys_from_performance(scraper, trip_kind=trip_kind):
        if discovered not in keys:
            keys.append(discovered)
    return keys


def find_search_keys_from_performance(
    scraper: "PlaywrightScraper",
    *,
    trip_kind: str,
) -> List[str]:
    """Return seen search keys from resource timing entries in order of first appearance."""

    if not scraper.page:
        return []

    adapter = get_interpark_adapter()
    prefix = adapter.domestic_key_prefix if trip_kind == "domestic" else adapter.international_key_prefix
    pattern = (
        adapter.domestic_search_api_path
        if trip_kind == "domestic"
        else adapter.international_search_api_path
    )
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


def resolve_search_key(
    scraper: "PlaywrightScraper",
    *,
    trip_kind: str,
    explicit_key: str | None = None,
) -> str:
    explicit = str(explicit_key or "").strip()
    if explicit:
        return explicit
    keys = find_search_keys(scraper, trip_kind=trip_kind)
    return keys[-1] if keys else ""


def find_latest_search_key(
    scraper: "PlaywrightScraper",
    *,
    trip_kind: str,
) -> str:
    return resolve_search_key(scraper, trip_kind=trip_kind)


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
