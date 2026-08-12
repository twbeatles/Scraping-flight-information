"""Probe Interpark result-page selectors and API shape against the live site.

This script is optional and network-dependent. Use it locally or from the
`live-smoke` GitHub workflow (workflow_dispatch).
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import scraper_config
from scraping.interpark.adapter import get_interpark_adapter
from scraping.interpark.network_listener import attach_interpark_response_listener
from scraping.playwright_api import page_fetch_json, resolve_search_key
from scraper_v2 import PlaywrightScraper


# (kind_label, origin, dest, is_domestic)
DEFAULT_PROBES = [
    ("domestic", "GMP", "CJU", True),
    ("international", "ICN", "NRT", False),
]


def _future_date(days: int) -> str:
    return (datetime.now() + timedelta(days=days)).strftime("%Y%m%d")


def _ensure_page(scraper: PlaywrightScraper, *, headless: bool) -> None:
    """Initialize browser and ensure a usable page/context exist."""

    scraper._init_browser(headless=headless, block_resources=headless)
    if scraper.context is None:
        if scraper.browser is None:
            raise RuntimeError("browser was not initialized")
        scraper.context = scraper.browser.new_context(
            viewport={"width": 1400, "height": 900},
            locale="ko-KR",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            ),
        )
        scraper._configure_resource_blocking(headless)
    if scraper.page is None:
        scraper.page = scraper.context.new_page()


def _probe_api_shape(
    scraper: PlaywrightScraper,
    *,
    is_domestic: bool,
    search_key: str,
) -> Dict[str, Any]:
    """Fetch one result page and report contract-relevant payload keys."""

    adapter = get_interpark_adapter()
    summary: Dict[str, Any] = {
        "attempted": False,
        "ok": False,
        "payload_keys": [],
        "has_page_meta": False,
        "has_items": False,
        "status": "",
        "error": "",
    }
    if not search_key or not scraper.page:
        return summary

    summary["attempted"] = True
    try:
        if is_domestic:
            url = adapter.build_domestic_result_url(search_key)
            payload = page_fetch_json(
                scraper,
                url,
                method="POST",
                body=adapter.domestic_result_request_body(
                    page_number=1,
                    page_size=adapter.default_api_page_size,
                    cabin="ECONOMY",
                ),
            )
            buckets = adapter.domestic_result_buckets
        else:
            status_url = adapter.build_international_status_url(search_key)
            status_payload = page_fetch_json(scraper, status_url)
            summary["status"] = str(status_payload.get(adapter.status_field) or "")
            url = adapter.build_international_result_url(search_key)
            payload = page_fetch_json(
                scraper,
                url,
                method="POST",
                body=adapter.international_result_request_body(
                    page_number=1,
                    page_size=adapter.default_api_page_size,
                ),
            )
            buckets = adapter.international_result_buckets

        if not isinstance(payload, dict):
            summary["error"] = "payload_not_dict"
            return summary

        keys = [str(key) for key in payload.keys() if not str(key).startswith("__")]
        summary["payload_keys"] = keys[:20]
        page_meta = payload.get(adapter.page_meta_key)
        summary["has_page_meta"] = isinstance(page_meta, dict)
        summary["has_items"] = any(
            isinstance(payload.get(bucket), list) and bool(payload.get(bucket))
            for bucket in buckets
        )
        summary["ok"] = bool(summary["has_page_meta"] or summary["has_items"] or keys)
    except Exception as exc:
        summary["error"] = str(exc)
    return summary


def _probe_selectors(
    *,
    origin: str,
    dest: str,
    dep: str,
    is_domestic: bool,
    wait_seconds: float,
    check_api_shape: bool,
) -> Dict[str, Any]:
    scraper = PlaywrightScraper()
    summary: Dict[str, Any] = {
        "route": f"{origin}->{dest}",
        "is_domestic": is_domestic,
        "selector_hits": {},
        "search_key": "",
        "key_source": "",
        "page_loaded": False,
        "api_shape": {},
        "error": "",
    }
    selectors = (
        scraper_config.DOMESTIC_WAIT_SELECTORS
        if is_domestic
        else scraper_config.INTERNATIONAL_WAIT_SELECTORS
    )
    try:
        _ensure_page(scraper, headless=True)
        if scraper.page is None:
            raise RuntimeError("browser page was not initialized")
        attach_interpark_response_listener(scraper, scraper.page)
        url = scraper_config.build_interpark_search_url(origin, dest, dep)
        scraper.page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=scraper_config.PAGE_LOAD_TIMEOUT_MS,
        )
        summary["page_loaded"] = True
        time.sleep(max(wait_seconds, 0.5))
        per_timeout = max(int(wait_seconds * 1000) // max(len(selectors), 1), 500)
        for selector in selectors:
            try:
                scraper.page.wait_for_selector(selector, timeout=per_timeout)
                summary["selector_hits"][selector] = True
            except Exception:
                summary["selector_hits"][selector] = False
        trip_kind = "domestic" if is_domestic else "international"
        summary["search_key"] = resolve_search_key(scraper, trip_kind=trip_kind)
        metrics = getattr(scraper, "_search_metrics", {}) or {}
        key_sources = metrics.get("api_key_sources", {}) if isinstance(metrics, dict) else {}
        if isinstance(key_sources, dict):
            summary["key_source"] = str(key_sources.get(trip_kind, "") or "")
        if check_api_shape and summary["search_key"]:
            summary["api_shape"] = _probe_api_shape(
                scraper,
                is_domestic=is_domestic,
                search_key=str(summary["search_key"]),
            )
    except Exception as exc:
        summary["error"] = str(exc)
    finally:
        scraper.close()
    return summary


def _print_summary(summary: Dict[str, Any]) -> None:
    hits = summary.get("selector_hits", {}) or {}
    matched = sum(1 for value in hits.values() if value)
    total = len(hits)
    print(
        f"[probe] {summary['route']} domestic={summary['is_domestic']} "
        f"loaded={summary['page_loaded']} selectors={matched}/{total} "
        f"search_key={'yes' if summary.get('search_key') else 'no'} "
        f"key_source={summary.get('key_source') or '-'} "
        f"error={summary.get('error') or '-'}"
    )
    for selector, ok in hits.items():
        status = "OK" if ok else "MISS"
        print(f"  - [{status}] {selector}")
    api_shape = summary.get("api_shape") or {}
    if api_shape.get("attempted"):
        print(
            f"  - [API] ok={api_shape.get('ok')} "
            f"page_meta={api_shape.get('has_page_meta')} "
            f"items={api_shape.get('has_items')} "
            f"status={api_shape.get('status') or '-'} "
            f"keys={api_shape.get('payload_keys') or []} "
            f"error={api_shape.get('error') or '-'}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe Interpark live DOM selectors.")
    parser.add_argument("--dep", default=_future_date(30))
    parser.add_argument("--wait-seconds", type=float, default=8.0)
    parser.add_argument(
        "--min-selector-hits",
        type=int,
        default=1,
        help="Fail if fewer than this many selectors match per route.",
    )
    parser.add_argument(
        "--require-search-key",
        action="store_true",
        help="Fail when no Interpark API search key is captured.",
    )
    parser.add_argument(
        "--check-api-shape",
        action="store_true",
        help="After capturing a search key, fetch one result page and verify shape.",
    )
    parser.add_argument(
        "--require-api-shape",
        action="store_true",
        help="Fail when API shape check does not see page meta or items.",
    )
    args = parser.parse_args()
    check_api_shape = bool(args.check_api_shape or args.require_api_shape)

    adapter = get_interpark_adapter()
    print(f"[adapter] international_api_path={adapter.international_search_api_path}")
    print(f"[adapter] domestic_api_path={adapter.domestic_search_api_path}")
    print(f"[adapter] status_suffix={adapter.status_path_suffix}")

    failed = False
    for _kind, origin, dest, is_domestic in DEFAULT_PROBES:
        summary = _probe_selectors(
            origin=origin,
            dest=dest,
            dep=args.dep,
            is_domestic=is_domestic,
            wait_seconds=args.wait_seconds,
            check_api_shape=check_api_shape,
        )
        _print_summary(summary)
        hits = summary.get("selector_hits", {}) or {}
        matched = sum(1 for value in hits.values() if value)
        if summary.get("error"):
            failed = True
        if matched < args.min_selector_hits:
            print(
                f"[fail] selector hits {matched} < required {args.min_selector_hits}",
                file=sys.stderr,
            )
            failed = True
        if args.require_search_key and not summary.get("search_key"):
            print("[fail] search key was not captured", file=sys.stderr)
            failed = True
        if args.require_api_shape:
            api_shape = summary.get("api_shape") or {}
            if not api_shape.get("ok"):
                print("[fail] API shape check failed", file=sys.stderr)
                failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
