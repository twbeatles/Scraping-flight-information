"""Domestic API failure recording (SRP: failure telemetry only)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict

from scraping.interpark.adapter import get_interpark_adapter
from scraping.playwright_api import get_api_meta, recent_api_resource_urls

if TYPE_CHECKING:
    from scraping.playwright_scraper import PlaywrightScraper


logger = logging.getLogger("ScraperV2")

DOMESTIC_API_FAILURE_REASONS = {
    "domestic_api_key_missing",
    "domestic_api_key_timeout",
    "domestic_api_key_expired",
    "domestic_api_result_fetch_failed",
    "domestic_api_payload_mismatch",
    "domestic_api_failed",
}


def clear_domestic_api_failure_after_success(scraper: "PlaywrightScraper") -> None:
    """Move stale domestic API failure state out of the final search status."""

    metrics = getattr(scraper, "_search_metrics", None)
    stale_reason = ""
    if isinstance(metrics, dict):
        stale_reason = str(metrics.pop("api_failure_reason", "") or "")
        if stale_reason:
            metrics.setdefault("prewait_api_failure_reason", stale_reason)
        for key in (
            "api_failure_payload_keys",
            "api_failure_code",
            "api_failure_message",
            "api_failure_meta",
            "api_recent_resources",
        ):
            if key in metrics:
                metrics[f"prewait_{key}"] = metrics.pop(key)

    manual_reason = str(getattr(scraper, "_manual_reason", "") or "")
    if manual_reason in DOMESTIC_API_FAILURE_REASONS or manual_reason == stale_reason:
        scraper._manual_reason = ""


def _record_domestic_api_failure(
    scraper: "PlaywrightScraper",
    reason: str,
    payload: Dict[str, Any],
) -> None:
    if not getattr(scraper, "_manual_reason", ""):
        scraper._manual_reason = reason
    metrics = getattr(scraper, "_search_metrics", None)
    if not isinstance(metrics, dict):
        return
    adapter = get_interpark_adapter()
    meta = get_api_meta(payload) if isinstance(payload, dict) else {}
    metrics["api_failure_reason"] = reason
    metrics["api_failure_payload_keys"] = list(payload.keys())[:20] if isinstance(payload, dict) else []
    if isinstance(payload, dict):
        code = payload.get(adapter.error_code_field)
        if code:
            metrics["api_failure_code"] = str(code)
        for message_field in adapter.error_message_fields:
            message = payload.get(message_field)
            if message:
                metrics["api_failure_message"] = str(message)
                break
    if meta:
        metrics["api_failure_meta"] = {
            "status": int(meta.get("status") or 0),
            "ok": bool(meta.get("ok")),
            "payload_keys": [str(item) for item in meta.get("payload_keys", [])[:20]],
        }
    resources = recent_api_resource_urls(scraper, trip_kind="domestic")
    if resources:
        metrics["api_recent_resources"] = resources
