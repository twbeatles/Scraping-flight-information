# Flight Bot Scraping Audit

- 기준일: 2026-08-12
- 대상 저장소: `Scraping-flight-information`
- 범위: scraping flow, facade compatibility, packaging, docs, ignore rules

## Current Result

현재 코드베이스는 API-first 복구, page-cap, 국내 공항 단위 URL, search-key 만료 재시도,
확장 필드(공항/수하물/잔여석), 국내 왕복 API-first 조합 경로, ResultTable effective-price 반영까지
포함한 상태다. 운영 기준은 아래 현재 구조와 검증 기준을 우선한다.

기능 감사 상세: `PROJECT_AUDIT.md` (2026-08-12 remediation 반영).

## Current Scraping Structure

| 영역 | 현재 위치 | 비고 |
| --- | --- | --- |
| Interpark URL/date/location builder | `scraping/interpark/urls.py` | 국내 `a:GMP`, 국제 city map |
| Interpark site/API adapter + schema | `scraping/interpark/adapter.py`, `scraping/interpark/contract/*` | endpoints, payload fields, carriers |
| Interpark selectors/regex | `scraping/interpark/selectors.py` | wait selector 실측 우선순위 |
| Interpark runtime constants | `scraping/interpark/runtime.py` | timeout, retry, key wait, page cap |
| Site contract memo | `docs/interpark_site_contract.md` | URL/API/DOM 계약 요약 |
| JS script builders | `scraping/interpark/scripts/*` | `ScraperScripts` 호환 class 유지 |
| 국제선 API/DOM 추출 | `scraping/international/*` | 공항/수하물/좌석/추천 태그 정규화 |
| 국내선 API/DOM 추출 | `scraping/domestic/*` | 키 만료 재시도, 왕복 메타 전파 |
| 검색 orchestration | `scraping/search_flow/*` | 왕복은 조합 경로 (api_first 포함) |
| scraper public API | `scraper_v2.py` | `FlightSearcher`, `PlaywrightScraper`, `ParallelSearcher` 유지 |
| live diagnostics | `scripts/live_selector_probe.py`, `live_api_payload_dump.py`, `live_dom_api_audit.py`, `live_smoke_search.py` | 선택 실행 |

## Current Contracts

- 국내선/국제선 모두 동일 출처 API-first 흐름을 우선한다.
- 국내 **왕복**은 API-first에서 편도 목록으로 early-return 하지 않고 `domestic_flow` 조합을 사용한다.
- API 성공 시 DOM fallback은 실행하지 않는다.
- search key가 없으면 `wait_for_search_key`로 network/performance를 폴링한다.
- `INVALID_CACHE_SEARCH_KEY` 시 exclude 대기 후 soft reload로 1회 재시도한다.
- 국내 왕복은 가는편 후보 다건 클릭 + return key 대기 후 조합한다.
- API 실패, key 미확인, 수동 개입 필요 시에만 DOM fallback 또는 manual mode로 내려간다.
- API pagination은 runtime page cap을 지키고 cap으로 잘린 경우 `api_pages_truncated`, `api_page_cap`, `api_total_pages_estimated`를 telemetry에 남긴다.
- API 성공 후 pre-wait 실패 사유를 최종 `api_failure_reason`으로 유지하지 않는다.
- `manual_reason`, `api_total_count`, `fetched_pages`, `api_fetched_pages`, `api_item_count`, `dom_seen_indices`, `dom_gap_detected`를 telemetry에 남긴다.
- 국내선 `price`는 기본가, `benefit_price`/`benefit_label`은 혜택가 정보다.
- 비교/알림/테이블 최저가 하이라이트는 `effective_flight_price`를 우선한다.
- 공개 import 경로와 검색 결과 shape는 유지한다 (`FlightResult` 확장 필드는 optional default).

## Packaging Check

`FlightBot_v2.5.spec`, `FlightBot_Simple.spec`, `flight_bot.spec`는 다음 범위를 hiddenimports에 포함한다.

- `core.airports`, `core.file_io`, `core.search_params`, `core.preferences`
- `scraping.interpark.*` (`adapter`, `contract`, `contract.carriers`, `contract.schemas`, `urls`, `selectors`, `scripts`, `network_listener`, `runtime`)
- `scraping.domestic.*`
- `scraping.international.*`
- `scraping.search_flow.*`
- 기존 compatibility modules: `scraping.playwright_*`, `scraping.playwright_api`, `scraping.search_sources`, `scraping.manual_reasons`
- UI/storage split modules: `ui.search_panel_params`, `ui.airport_options`, `ui.export_helpers`, `storage.schema`, `storage.flight_database`, `storage.db_favorites`

## Ignore Check

`.gitignore`는 운영 산출물과 로컬 에이전트/세션 산출물을 제외한다.

- Python/test cache
- build/dist/PyInstaller output
- Playwright profile
- logs and telemetry JSONL
- SQLite DB and journal files
- session/preferences runtime files
- local code index `.codegraph/`
- local agent dumps (`agent-tools/`, `terminals/`, `mcps/`)

## Validation Baseline

```text
python -m pytest -q
-> 153 passed

pyright --warnings
-> 0 errors, 0 warnings

python scripts\check_tracked_text.py --check-lf
-> Checked 150 tracked text files: OK

python scripts\live_selector_probe.py --require-search-key --check-api-shape
-> 릴리스 전 권장 (실사이트)

python scripts\live_smoke_search.py --max-results 5 --fail-on-cap --max-domestic-pages 30 --max-international-pages 50
-> 릴리스 전 권장 (실사이트)

python -m PyInstaller --clean --noconfirm FlightBot_v2.5.spec
-> dist\FlightBot_v2.5.exe generated
```

## Audit Notes

- 현재 문서는 고정된 과거 실패 목록이 아니라 최신 구조의 검증 기준을 기록한다.
- 실사이트 API 계약은 외부 서비스 변경 영향을 받으므로 릴리스 전에는 live probe/smoke로 확인한다.
- 구조 리팩터링 후 기능 누락 방지는 facade import 테스트와 직접 package import 테스트로 확인한다.
- 기능 감사 이슈 추적: `PROJECT_AUDIT.md` Remediation Status.
