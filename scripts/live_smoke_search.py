"""Manual live smoke checks for Interpark scraping.

This script is intentionally not wired into CI because it depends on the
network, browser availability, and Interpark runtime behavior.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from scraper_v2 import FlightSearcher


DEFAULT_ROUTES: List[Tuple[str, str, str]] = [
    ("domestic", "GMP", "CJU"),
    ("international", "ICN", "NRT"),
]


def _future_date(days: int) -> str:
    return (datetime.now() + timedelta(days=days)).strftime("%Y%m%d")


def _run_route(kind: str, origin: str, dest: str, dep: str, ret: str | None, max_results: int) -> Dict[str, Any]:
    searcher = FlightSearcher()
    cleanup_ok = False
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
        return {
            "kind": kind,
            "route": f"{origin}->{dest}",
            "result_count": len(results),
            "first_source": results[0].extraction_source if results else "",
            "manual_reason": manual_reason,
            "metrics": {
                key: metrics.get(key)
                for key in ("api_total_count", "fetched_pages", "api_item_count", "api_failure_reason")
                if key in metrics
            },
        }
    finally:
        try:
            searcher.close()
            cleanup_ok = True
        finally:
            if cleanup_ok:
                print(f"[cleanup] {kind} {origin}->{dest}: browser closed")
            else:
                print(f"[cleanup] {kind} {origin}->{dest}: browser cleanup incomplete")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run manual live smoke searches.")
    parser.add_argument("--dep", default=_future_date(30), help="Departure date as YYYYMMDD")
    parser.add_argument("--ret", default=_future_date(33), help="Return date as YYYYMMDD")
    parser.add_argument("--max-results", type=int, default=20)
    args = parser.parse_args()

    for kind, origin, dest in DEFAULT_ROUTES:
        ret = None if kind == "domestic" else args.ret
        summary = _run_route(kind, origin, dest, args.dep, ret, args.max_results)
        print(
            f"[{summary['kind']}] {summary['route']} "
            f"results={summary['result_count']} source={summary['first_source'] or '-'} "
            f"manual_reason={summary['manual_reason'] or '-'} metrics={summary['metrics']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
