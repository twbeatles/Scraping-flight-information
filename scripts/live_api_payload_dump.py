"""Dump Interpark API payload shapes after a successful search-key capture."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scraper_config
from scraper_v2 import PlaywrightScraper
from scraping.interpark.adapter import get_interpark_adapter
from scraping.interpark.network_listener import attach_interpark_response_listener
from scraping.playwright_api import page_fetch_json, resolve_search_key, wait_for_search_key


def _dep(days: int = 30) -> str:
    return (datetime.now() + timedelta(days=days)).strftime("%Y%m%d")


def _ensure(scraper: PlaywrightScraper) -> None:
    scraper._init_browser(headless=True, block_resources=True)
    if scraper.context is None:
        browser = scraper.browser
        if browser is None:
            raise RuntimeError("browser missing")
        scraper.context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            locale="ko-KR",
        )
        scraper._configure_resource_blocking(True)
    if scraper.context is None:
        raise RuntimeError("context missing")
    scraper.page = scraper.context.new_page()


def _typeish(value: object) -> object:
    if isinstance(value, dict):
        return {k: _typeish(v) for k, v in list(value.items())[:40]}
    if isinstance(value, list):
        if not value:
            return []
        return [_typeish(value[0]), f"... total {len(value)}"]
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, str) and len(value) > 80:
            return value[:80] + "..."
        return value
    return type(value).__name__


def dump_route(origin: str, dest: str, *, is_domestic: bool) -> dict:
    scraper = PlaywrightScraper()
    adapter = get_interpark_adapter()
    out: dict = {"route": f"{origin}->{dest}", "is_domestic": is_domestic}
    try:
        _ensure(scraper)
        assert scraper.page is not None
        attach_interpark_response_listener(scraper, scraper.page)
        url = scraper_config.build_interpark_search_url(origin, dest, _dep())
        out["url"] = url
        scraper.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(8)
        trip = "domestic" if is_domestic else "international"
        key = resolve_search_key(scraper, trip_kind=trip) or wait_for_search_key(
            scraper, trip_kind=trip, timeout_seconds=15
        )
        out["search_key"] = bool(key)
        if not key:
            out["error"] = "no_search_key"
            # DOM quick facts
            out["dom"] = scraper.page.evaluate(
                """() => ({
                  buttons: document.querySelectorAll('button').length,
                  wonButtons: Array.from(document.querySelectorAll('button')).filter(b => (b.textContent||'').includes('원')).length,
                  dataIndex: document.querySelectorAll('[data-index]').length,
                  bodySnippet: (document.body.innerText||'').slice(0, 300)
                })"""
            )
            return out

        if is_domestic:
            payload = page_fetch_json(
                scraper,
                adapter.build_domestic_result_url(key),
                method="POST",
                body=adapter.domestic_result_request_body(
                    page_number=1, page_size=5, cabin="ECONOMY"
                ),
            )
        else:
            for _ in range(20):
                status = page_fetch_json(scraper, adapter.build_international_status_url(key))
                out["status"] = str(status.get("status") or "")
                if out["status"].upper() == "COMPLETE":
                    break
                scraper.page.wait_for_timeout(1000)
            payload = page_fetch_json(
                scraper,
                adapter.build_international_result_url(key),
                method="POST",
                body=adapter.international_result_request_body(page_number=1, page_size=5),
            )

        clean = {k: v for k, v in (payload or {}).items() if not str(k).startswith("__")}
        out["top_keys"] = list(clean.keys())
        out["page"] = clean.get("page")
        out["filter"] = _typeish(clean.get("filter"))
        out["sort"] = _typeish(clean.get("sort"))
        if "tripType" in clean:
            out["tripType"] = clean.get("tripType")
        for bucket in ("items", "bestItems", "bestFares", "contents", "airlines", "locations"):
            value = clean.get(bucket)
            if not isinstance(value, list):
                continue
            out[f"{bucket}_len"] = len(value)
            if value and isinstance(value[0], dict):
                out[f"{bucket}_sample"] = _typeish(value[0])

        # DOM after data load
        out["dom"] = scraper.page.evaluate(
            """() => {
              const wonButtons = Array.from(document.querySelectorAll('button'))
                .filter(b => (b.textContent||'').includes('원'));
              const cards = Array.from(document.querySelectorAll('li[data-index], div[data-index]'));
              return {
                wonButtons: wonButtons.length,
                dataIndex: cards.length,
                sampleButton: wonButtons[0] ? (wonButtons[0].textContent||'').replace(/\\s+/g,' ').trim().slice(0,200) : '',
                sampleCard: cards[0] ? (cards[0].textContent||'').replace(/\\s+/g,' ').trim().slice(0,200) : '',
                hasDirectText: (document.body.innerText||'').includes('직항'),
                hasStopText: (document.body.innerText||'').includes('경유'),
                hasCashback: (document.body.innerText||'').includes('캐시백'),
                hasSeatClass: /특가석|할인석|일반석|비즈니스/.test(document.body.innerText||''),
                hasBaggage: /수하물|무료 수하물/.test(document.body.innerText||''),
              };
            }"""
        )
    except Exception as exc:
        out["error"] = str(exc)
    finally:
        scraper.close()
    return out


def main() -> int:
    reports = [
        dump_route("GMP", "CJU", is_domestic=True),
        dump_route("ICN", "NRT", is_domestic=False),
    ]
    print(json.dumps(reports, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
