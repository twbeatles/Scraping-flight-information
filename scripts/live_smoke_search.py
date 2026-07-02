"""Manual live smoke checks for Interpark scraping.

This script is intentionally not wired into CI because it depends on the
network, browser availability, and Interpark runtime behavior.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scraper_v2 import FlightSearcher


DEFAULT_ROUTES: List[Tuple[str, str, str, str | None]] = [
    ("domestic", "GMP", "CJU", None),
    ("domestic_roundtrip", "GMP", "CJU", "ret"),
    ("international", "ICN", "NRT", None),
]


def _future_date(days: int) -> str:
    return (datetime.now() + timedelta(days=days)).strftime("%Y%m%d")


def _run_route(kind: str, origin: str, dest: str, dep: str, ret: str | None, max_results: int) -> Dict[str, Any]:
    searcher = FlightSearcher()
    cleanup_ok = False
    started_at = time.monotonic()
    summary: Dict[str, Any] = {
        "kind": kind,
        "route": f"{origin}->{dest}",
        "result_count": 0,
        "first_source": "",
        "manual_reason": "",
        "metrics": {},
        "cleanup_ok": False,
        "duration_ms": 0,
    }
    try:
        results = searcher.search(
            origin,
            dest,
            dep,
            ret,
            adults=1,
            cabin_class="ECONOMY",
            max_results=max_results,
            background_mode=True,
        )
        scraper = getattr(getattr(searcher, "source", None), "scraper", None)
        metrics = dict(getattr(scraper, "_search_metrics", {}) or {})
        manual_reason = searcher.get_manual_reason() if hasattr(searcher, "get_manual_reason") else ""
        summary.update(
            {
                "result_count": len(results),
                "first_source": results[0].extraction_source if results else "",
                "manual_reason": manual_reason,
                "metrics": {
                    key: metrics.get(key)
                    for key in (
                        "api_total_count",
                        "fetched_pages",
                        "api_fetched_pages",
                        "api_item_count",
                        "api_failure_reason",
                        "prewait_api_failure_reason",
                        "api_page_cap",
                        "api_pages_truncated",
                        "api_total_pages_estimated",
                    )
                    if key in metrics
                },
            }
        )
    finally:
        try:
            searcher.close()
            cleanup_ok = True
        finally:
            if cleanup_ok:
                print(f"[cleanup] {kind} {origin}->{dest}: browser closed")
            else:
                print(f"[cleanup] {kind} {origin}->{dest}: browser cleanup incomplete")
            summary["cleanup_ok"] = cleanup_ok
            summary["duration_ms"] = int((time.monotonic() - started_at) * 1000)
    return summary


def _violates_smoke_thresholds(summary: Dict[str, Any], *, page_cap: int) -> bool:
    failed = False
    metrics = summary.get("metrics", {}) or {}
    fetched_pages = int(metrics.get("fetched_pages") or metrics.get("api_fetched_pages") or 0)
    if fetched_pages > page_cap:
        print(
            f"[fail] {summary['route']} fetched_pages={fetched_pages} exceeds cap={page_cap}",
            file=sys.stderr,
        )
        failed = True
    if summary.get("result_count", 0) > 0 and summary.get("manual_reason"):
        print(
            f"[fail] {summary['route']} succeeded with final manual_reason={summary['manual_reason']}",
            file=sys.stderr,
        )
        failed = True
    if not summary.get("cleanup_ok"):
        print(f"[fail] {summary['route']} browser cleanup incomplete", file=sys.stderr)
        failed = True
    return failed


def main() -> int:
    parser = argparse.ArgumentParser(description="Run manual live smoke searches.")
    parser.add_argument("--dep", default=_future_date(30), help="Departure date as YYYYMMDD")
    parser.add_argument("--ret", default=_future_date(33), help="Return date as YYYYMMDD")
    parser.add_argument("--max-results", type=int, default=20)
    parser.add_argument("--fail-on-cap", action="store_true", help="Fail if live search exceeds page caps or leaves stale final failure state.")
    parser.add_argument("--max-domestic-pages", type=int, default=30)
    parser.add_argument("--max-international-pages", type=int, default=50)
    parser.add_argument(
        "--selector-probe",
        action="store_true",
        help="After search smoke, run scripts/live_selector_probe.py against the live site.",
    )
    parser.add_argument("--selector-probe-wait-seconds", type=float, default=8.0)
    args = parser.parse_args()

    failed = False
    for route in DEFAULT_ROUTES:
        kind, origin, dest, ret_mode = route
        if ret_mode == "ret":
            ret = args.ret
        elif kind == "international":
            ret = args.ret
        else:
            ret = None
        summary = _run_route(kind, origin, dest, args.dep, ret, args.max_results)
        print(
            f"[{summary['kind']}] {summary['route']} "
            f"results={summary['result_count']} source={summary['first_source'] or '-'} "
            f"manual_reason={summary['manual_reason'] or '-'} duration_ms={summary['duration_ms']} "
            f"cleanup_ok={summary['cleanup_ok']} metrics={summary['metrics']}"
        )
        if args.fail_on_cap:
            if kind.startswith("domestic"):
                page_cap = args.max_domestic_pages
            else:
                page_cap = args.max_international_pages
            failed = _violates_smoke_thresholds(summary, page_cap=page_cap) or failed

    if args.selector_probe:
        probe_script = ROOT_DIR / "scripts" / "live_selector_probe.py"
        print("[selector-probe] starting live DOM selector probe")
        probe_exit = subprocess.run(
            [sys.executable, str(probe_script)],
            cwd=str(ROOT_DIR),
            check=False,
        ).returncode
        if probe_exit != 0:
            print("[selector-probe] failed", file=sys.stderr)
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
