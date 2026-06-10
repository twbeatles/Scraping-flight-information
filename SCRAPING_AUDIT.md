# Flight Bot Scraping Audit

- 기준일: 2026-06-11
- 대상 저장소: `Scraping-flight-information`
- 범위: scraping flow, facade compatibility, packaging, docs, ignore rules

## Current Result

현재 코드베이스는 2026-05-11 API-first 복구와 DB 마이그레이션 후속 조치, 2026-06-11 page-cap/복구성 보강을 반영한 상태다. 이전 감사의 상세 실패 항목은 운영 기준에서 제거하고, 아래 현재 구조와 검증 기준을 최신 기준으로 둔다.

## Current Scraping Structure

| 영역 | 현재 위치 | 비고 |
| --- | --- | --- |
| Interpark URL/date/location builder | `scraping/interpark/urls.py` | `scraper_config.py` facade 유지 |
| Interpark selectors/regex | `scraping/interpark/selectors.py` | wait selector와 pattern 분리 |
| Interpark runtime constants | `scraping/interpark/runtime.py` | timeout, retry, cache, scroll tuning |
| JS script builders | `scraping/interpark/scripts/*` | `ScraperScripts` 호환 class 유지 |
| 국제선 API/DOM 추출 | `scraping/international/*` | `scraping.playwright_results` wrapper 유지 |
| 국내선 API/DOM 추출 | `scraping/domestic/*` | `scraping.playwright_domestic` wrapper 유지 |
| 검색 orchestration | `scraping/search_flow/*` | `scraping.playwright_search` wrapper 유지 |
| scraper public API | `scraper_v2.py` | `FlightSearcher`, `PlaywrightScraper`, `ParallelSearcher` 유지 |

## Current Contracts

- 국내선/국제선 모두 동일 출처 API-first 흐름을 우선한다.
- API 성공 시 DOM fallback은 실행하지 않는다.
- API 실패, key 미확인, 수동 개입 필요 시에만 DOM fallback 또는 manual mode로 내려간다.
- API pagination은 runtime page cap을 지키고 cap으로 잘린 경우 `api_pages_truncated`, `api_page_cap`, `api_total_pages_estimated`를 telemetry에 남긴다.
- API 성공 후 pre-wait 실패 사유를 최종 `api_failure_reason`으로 유지하지 않는다.
- `manual_reason`, `api_total_count`, `fetched_pages`, `api_fetched_pages`, `api_item_count`, `dom_seen_indices`, `dom_gap_detected`를 telemetry에 남긴다.
- 국내선 `price`는 기본가, `benefit_price`/`benefit_label`은 혜택가 정보다.
- 공개 import 경로와 검색 결과 shape는 유지한다.

## Packaging Check

`FlightBot_v2.5.spec`, `FlightBot_Simple.spec`, `flight_bot.spec`는 다음 범위를 hiddenimports에 포함한다.

- `core.airports`, `core.file_io`, `core.search_params`, `core.preferences`
- `scraping.interpark.*`
- `scraping.domestic.*`
- `scraping.international.*`
- `scraping.search_flow.*`
- 기존 compatibility modules: `scraping.playwright_*`, `scraping.playwright_api`, `scraping.search_sources`, `scraping.manual_reasons`
- UI/storage split modules: `ui.search_panel_params`, `ui.airport_options`, `ui.export_helpers`, `storage.schema`, `storage.flight_database`, `storage.db_favorites`

## Ignore Check

`.gitignore`는 현재 운영 산출물을 제외한다.

- Python/test cache
- build/dist/PyInstaller output
- Playwright profile
- logs and telemetry JSONL
- SQLite DB and journal files
- session/preferences runtime files
- local code index `.codegraph/`

## Validation Baseline

```text
python -m pytest -q
-> 123 passed

pyright --warnings
-> 0 errors, 0 warnings

python scripts\check_tracked_text.py --check-lf
-> Checked 142 tracked text files: OK

python scripts\live_smoke_search.py --max-results 5 --fail-on-cap --max-domestic-pages 30 --max-international-pages 50
-> domestic GMP->CJU 5 results, fetched_pages=10, cleanup_ok=True
-> international ICN->NRT 5 results, fetched_pages=50, api_pages_truncated=True, cleanup_ok=True

python -m PyInstaller --clean --noconfirm FlightBot_v2.5.spec
-> dist\FlightBot_v2.5.exe generated

dist\FlightBot_v2.5.exe
-> 6 second smoke passed
```

## Audit Notes

- 현재 문서는 고정된 과거 실패 목록이 아니라 최신 구조의 검증 기준을 기록한다.
- 실사이트 API 계약은 외부 서비스 변경 영향을 받으므로 릴리스 전에는 `python scripts/live_smoke_search.py --fail-on-cap`으로 page-cap, stale manual reason, browser cleanup을 별도 확인한다.
- 구조 리팩터링 후 기능 누락 방지는 facade import 테스트와 직접 package import 테스트로 확인한다.
