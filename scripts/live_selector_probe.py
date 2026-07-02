"""Probe Interpark result-page selectors against the live site.

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
from scraping.playwright_api import resolve_search_key
from scraper_v2 import PlaywrightScraper


DEFAULT_PROBES = [
    ("domestic", "GMP", "CJU", False),
    ("international", "ICN", "NRT", False),
]


def _future_date(days: int) -> str:
    return (datetime.now() + timedelta(days=days)).strftime("%Y%m%d")


def _probe_selectors(
    *,
    origin: str,
    dest: str,
    dep: str,
    is_domestic: bool,
    wait_seconds: float,
) -> Dict[str, Any]:
    scraper = PlaywrightScraper()
    summary: Dict[str, Any] = {
        "route": f"{origin}->{dest}",
        "is_domestic": is_domestic,
        "selector_hits": {},
        "search_key": "",
        "key_source": "",
        "page_loaded": False,
        "error": "",
    }
    selectors = (
        scraper_config.DOMESTIC_WAIT_SELECTORS
        if is_domestic
        else scraper_config.INTERNATIONAL_WAIT_SELECTORS
    )
    try:
        scraper._init_browser(headless=True, block_resources=True)
        if scraper.context is None:
            raise RuntimeError("browser context was not initialized")
        scraper.page = scraper.context.new_page()
        attach_interpark_response_listener(scraper, scraper.page)
        url = scraper_config.build_interpark_search_url(origin, dest, dep)
        scraper.page.goto(url, wait_until="domcontentloaded", timeout=scraper_config.PAGE_LOAD_TIMEOUT_MS)
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
    args = parser.parse_args()

    adapter = get_interpark_adapter()
    print(f"[adapter] international_api_path={adapter.international_search_api_path}")

    failed = False
    for _kind, origin, dest, is_domestic in DEFAULT_PROBES:
        summary = _probe_selectors(
            origin=origin,
            dest=dest,
            dep=args.dep,
            is_domestic=is_domestic,
            wait_seconds=args.wait_seconds,
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
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())