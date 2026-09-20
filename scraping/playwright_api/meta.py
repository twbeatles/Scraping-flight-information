"""API response metadata helpers (SRP: meta attach/record/sanitize only)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


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

