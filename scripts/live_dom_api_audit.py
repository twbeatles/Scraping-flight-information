"""One-shot live audit of Interpark DOM counts and API payload shapes.

Network-dependent. Prints JSON summary to stdout.
"""

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
from scraping.playwright_api import page_fetch_json, resolve_search_key


DOM_STATS_JS = r"""
() => {
  const q = (sel) => document.querySelectorAll(sel).length;
  const body = (document.body && document.body.innerText) || '';
  const priceButtons = Array.from(document.querySelectorAll('button')).filter((b) =>
    (b.textContent || '').includes('원')
  );
  const sampleButtons = priceButtons.slice(0, 6).map((b) =>
    (b.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 180)
  );
  const dataIndex = Array.from(document.querySelectorAll('[data-index]'))
    .slice(0, 4)
    .map((n) => ({
      tag: n.tagName,
      index: n.getAttribute('data-index'),
      cls: String(n.className || '').slice(0, 100),
      text: (n.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 140),
    }));
  const imgs = Array.from(document.querySelectorAll('img[alt]'))
    .map((i) => i.getAttribute('alt') || '')
    .filter(Boolean)
    .slice(0, 25);
  const classHits = {};
  for (const el of document.querySelectorAll('[class]')) {
    const cn = String(el.className || '');
    for (const part of cn.split(/\s+/)) {
      if (/flight|result|list|ticket|fare|schedule|price|card|item|scroll|virtual/i.test(part)) {
        classHits[part] = (classHits[part] || 0) + 1;
      }
    }
  }
  const topClasses = Object.entries(classHits)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 30);
  return {
    url: location.href,
    title: document.title,
    counts: {
      button: q('button'),
      buttonWon: priceButtons.length,
      buttonDirect: Array.from(document.querySelectorAll('button')).filter((b) =>
        (b.textContent || '').includes('직항')
      ).length,
      liDataIndex: q('li[data-index]'),
      divDataIndex: q('div[data-index]'),
      anyDataIndex: q('[data-index]'),
      imgLogo: q('img[alt$="로고"]'),
      main: q('main'),
      roleList: q('[role="list"]'),
      roleListitem: q('[role="listitem"]'),
      bodyLen: body.length,
    },
    flags: {
      hasComing: body.includes('오는편'),
      hasGoing: body.includes('가는편'),
      hasWon: body.includes('원'),
      hasDirect: body.includes('직항'),
      hasStop: body.includes('경유'),
      hasCashback: body.includes('캐시백') || body.includes('혜택'),
      hasSeatType: /특가|일반석|비즈니스|할인석|특가석/.test(body),
      hasLoading: /로딩|검색 중|결과 없음|항공권을 찾고/.test(body),
      hasFilter: /직항만|무료 수하물|경유/.test(body),
      hasSort: /최저가|빠른|추천/.test(body),
    },
    sampleButtons,
    sampleImgs: imgs,
    dataIndexSamples: dataIndex,
    topClasses,
  };
}
"""


def _future_date(days: int = 30) -> str:
    return (datetime.now() + timedelta(days=days)).strftime("%Y%m%d")


def _ensure_page(scraper: PlaywrightScraper) -> None:
    scraper._init_browser(headless=True, block_resources=True)
    if scraper.context is None:
        if scraper.browser is None:
            raise RuntimeError("browser missing")
        scraper.context = scraper.browser.new_context(
            viewport={"width": 1400, "height": 900},
            locale="ko-KR",
        )
        scraper._configure_resource_blocking(True)
    scraper.page = scraper.context.new_page()


def _shallow(value: object) -> object:
    if isinstance(value, dict):
        out = {}
        for idx, (key, item) in enumerate(value.items()):
            if idx >= 25:
                break
            if isinstance(item, (str, int, float, bool)) or item is None:
                out[key] = item
            elif isinstance(item, list):
                out[key] = f"list[{len(item)}]"
            elif isinstance(item, dict):
                out[key] = f"dict[{len(item)}]"
            else:
                out[key] = type(item).__name__
        return out
    return type(value).__name__


def _inspect_payload(payload: dict) -> dict:
    clean = {k: v for k, v in payload.items() if not str(k).startswith("__")}
    report: dict = {"keys": list(clean.keys())[:40]}
    page_meta = clean.get("page")
    if isinstance(page_meta, dict):
        report["page"] = page_meta
    for bucket in ("items", "bestItems", "bestFares", "contents", "airlines", "locations"):
        value = clean.get(bucket)
        if isinstance(value, list):
            report[f"{bucket}_len"] = len(value)
            if value and isinstance(value[0], dict):
                report[f"{bucket}_item0_keys"] = list(value[0].keys())[:40]
                report[f"{bucket}_item0_shallow"] = _shallow(value[0])
                schedule = value[0].get("schedule")
                schedules = value[0].get("schedules")
                if isinstance(schedule, dict):
                    report[f"{bucket}_schedule_keys"] = list(schedule.keys())[:30]
                if isinstance(schedules, list) and schedules and isinstance(schedules[0], dict):
                    report[f"{bucket}_schedules0_keys"] = list(schedules[0].keys())[:30]
                    segments = schedules[0].get("segments")
                    if isinstance(segments, list) and segments and isinstance(segments[0], dict):
                        report[f"{bucket}_segment0_keys"] = list(segments[0].keys())[:30]
                fares = value[0].get("fares")
                if isinstance(fares, list) and fares and isinstance(fares[0], dict):
                    report[f"{bucket}_fare0_keys"] = list(fares[0].keys())[:30]
                    report[f"{bucket}_fare0_shallow"] = _shallow(fares[0])
                    benefits = fares[0].get("benefits")
                    if isinstance(benefits, list) and benefits and isinstance(benefits[0], dict):
                        report[f"{bucket}_benefit0_keys"] = list(benefits[0].keys())[:30]
    for key in ("filter", "sort", "tripType"):
        if key in clean:
            report[key] = _shallow(clean[key]) if isinstance(clean[key], (dict, list)) else clean[key]
    return report


def inspect_route(origin: str, dest: str, *, is_domestic: bool, wait_seconds: float = 10.0) -> dict:
    scraper = PlaywrightScraper()
    adapter = get_interpark_adapter()
    out: dict = {"route": f"{origin}->{dest}", "is_domestic": is_domestic}
    try:
        _ensure_page(scraper)
        assert scraper.page is not None
        attach_interpark_response_listener(scraper, scraper.page)
        url = scraper_config.build_interpark_search_url(origin, dest, _future_date(30))
        scraper.page.goto(url, wait_until="domcontentloaded", timeout=scraper_config.PAGE_LOAD_TIMEOUT_MS)
        time.sleep(wait_seconds)
        trip = "domestic" if is_domestic else "international"
        key = resolve_search_key(scraper, trip_kind=trip)
        out["search_key_present"] = bool(key)
        out["dom"] = scraper.page.evaluate(DOM_STATS_JS)
        resources = scraper.page.evaluate(
            """() => performance.getEntriesByType('resource')
                .map((e) => e.name)
                .filter((n) => n.includes('air-api') || n.includes('flights/search'))
                .slice(-40)"""
        )
        out["api_resources"] = [str(item).split("?", 1)[0][-140:] for item in resources or []]
        if key:
            if is_domestic:
                payload = page_fetch_json(
                    scraper,
                    adapter.build_domestic_result_url(key),
                    method="POST",
                    body=adapter.domestic_result_request_body(
                        page_number=1,
                        page_size=5,
                        cabin="ECONOMY",
                    ),
                )
            else:
                status = page_fetch_json(scraper, adapter.build_international_status_url(key))
                out["status"] = {
                    k: status.get(k)
                    for k in list(status.keys())[:15]
                    if not str(k).startswith("__")
                }
                # wait briefly if not complete
                for _ in range(8):
                    if str(status.get("status") or "").upper() == "COMPLETE":
                        break
                    scraper.page.wait_for_timeout(1000)
                    status = page_fetch_json(scraper, adapter.build_international_status_url(key))
                    out["status"] = {
                        k: status.get(k)
                        for k in list(status.keys())[:15]
                        if not str(k).startswith("__")
                    }
                payload = page_fetch_json(
                    scraper,
                    adapter.build_international_result_url(key),
                    method="POST",
                    body=adapter.international_result_request_body(page_number=1, page_size=5),
                )
            if isinstance(payload, dict):
                out["api"] = _inspect_payload(payload)
    except Exception as exc:
        out["error"] = str(exc)
    finally:
        scraper.close()
    return out


def main() -> int:
    reports = [
        inspect_route("GMP", "CJU", is_domestic=True),
        inspect_route("ICN", "NRT", is_domestic=False),
        # domestic round-trip surface
        inspect_route("GMP", "CJU", is_domestic=True),
    ]
    # dedicated round-trip page
    scraper = PlaywrightScraper()
    try:
        _ensure_page(scraper)
        assert scraper.page is not None
        attach_interpark_response_listener(scraper, scraper.page)
        dep = _future_date(30)
        ret = _future_date(37)
        url = scraper_config.build_interpark_search_url("GMP", "CJU", dep, ret)
        scraper.page.goto(url, wait_until="domcontentloaded", timeout=scraper_config.PAGE_LOAD_TIMEOUT_MS)
        time.sleep(10)
        rt = {
            "route": "GMP->CJU roundtrip",
            "dom": scraper.page.evaluate(DOM_STATS_JS),
            "search_key": bool(resolve_search_key(scraper, trip_kind="domestic")),
        }
        reports.append(rt)
    except Exception as exc:
        reports.append({"route": "GMP->CJU roundtrip", "error": str(exc)})
    finally:
        scraper.close()

    print(json.dumps(reports, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
