# Project Audit

감사 기준일: 2026-07-02  
감사 범위: 기능 구현, Interpark(`travel.interpark.com`) 연동, 상태/비동기/데이터 흐름, 테스트·문서 정합성  
분석 방법: `README.md`, `Claude.md` 선독 → CodeGraph MCP(`codegraph_explore`) 호출 관계 분석 → 보조 grep/파일 열람

> 참고: 저장소 루트에 `.codegraph/` 디렉터리는 없으나 CodeGraph MCP 서버 인덱스를 통해 구조 분석을 수행했다.  
> 초기 감사 시점에는 프로젝트 `venv` 없이 전역 Python만 사용했고 `requirements.txt`가 설치되지 않아 `playwright` import 오류로 `pytest` 수집이 중단되었다(4 collection errors).  
> 후속 조치(2026-07-02): `pip install -r requirements.txt -c constraints.txt`, `playwright install chromium` 후 `python -m pytest -q` → **123 passed in 6.78s** (README/Claude.md 기준선과 일치).  
> 구현 반영(2026-07-02): 감사 1~3단계 권장사항 대부분 코드 반영 후 `python -m pytest -q` → **130 passed** (`tests/test_audit_improvements.py` 7건 추가).  
> 후속 완료(2026-07-02): network listener·adapter 분리·live selector probe·MainWindow E2E 테스트·PyInstaller hiddenimports 반영. `python -m pytest -q` → **137 passed** (추가 7건).  
> 캐시 정책 분리(2026-07-02): foreground(180s)·background(90s)·alert(45s) TTL, child/infant cache key, `AlertAutoCheckWorker` → `cache_mode="alert"`.

---

## 1. Executive Summary

**전체 위험도: Medium** (외부 사이트 의존도가 높고, 브라우저 자동화·API 계약 변경에 취약)

Flight Bot v2.5는 **Interpark Air 단일 출처**(`https://travel.interpark.com/air/search`, `.../air-api/inpark-air-web-api`)를 Playwright로 열고, **동일 출처 API 우선 → DOM fallback → 수동 모드** 순으로 항공권을 추출하는 PyQt6 데스크톱 앱이다. 아키텍처 분리(facade + `core/*`, `scraping/*`, `storage/*`, `ui/*`)와 회귀 테스트·live smoke 스크립트는 잘 갖춰져 있다.

다만 **실제 운영 사이트(Interpark) 관점**에서 보면 다음이 핵심 리스크다.

| 영역 | 요약 |
| --- | --- |
| Interpark API/DOM 계약 | URL 경로·search key·selector가 하드코딩되어 사이트 변경 시 조용히 실패 가능 |
| 국내선 왕복 | API-first 경로가 의도적으로 비활성화되어 DOM/클릭 흐름 의존도가 높음 |
| 취소/동시 실행 | UI worker 취소는 있으나 scraper 내부 장시간 루프에는 협조적 취소가 없음 |
| 가격 정확도 | 국내선 혜택가·왕복 조합 정책이 화면/알림/캐시에서 일관되지 않을 여지 |
| 기능 공백 | 소아/유아 인원, Interpark 외 소스, 라이브 DOM 회귀 검증 부족 |

이전 `PROJECT_AUDIT.md`(2026-06-11)는 **이미 구현 완료된 하드닝 항목**을 기록한 문서였고, 본 문서는 **현재 코드 기준 기능 감사**에 초점을 둔다.

---

## 2. Project Understanding

### 2.1 프로젝트 목적

- Interpark 항공권 검색 결과를 수집·비교·저장·보내기
- 국내선/국제선, 편도/왕복, 좌석 등급, 성인 인원 검색
- 즐겨찾기, 검색 기록, 세션, 가격 알림, CSV/Excel export, SQLite/JSONL telemetry

### 2.2 아키텍처 (CodeGraph + 문서 교차 확인)

```text
gui_v2.py
└─ app/main_window.py (MainWindow + feature mixins)
   ├─ app/mainwindow/search_single.py      # 단일 검색 시작
   ├─ app/mainwindow/worker_lifecycle.py   # 동시 실행/취소
   ├─ app/mainwindow/auto_alert.py         # 자동 가격 알림
   └─ ui/search_panel_*                    # 입력·검증·상태

scraper_v2.py (facade)
└─ scraping/searcher.py (FlightSearcher, 캐시)
   └─ scraping/search_sources.py (InterparkAirSource)
      └─ scraping/playwright_scraper.py
         └─ scraping/search_flow/orchestration.py (run_search)
            ├─ scraping/search_flow/api_first.py
            ├─ scraping/domestic/*           # 국내 API/DOM/왕복 조합
            ├─ scraping/international/*    # 국제 API/DOM
            └─ scraping/interpark/*          # URL, selector, runtime, JS

config.py / database.py (facade)
└─ core/*, storage/*
```

### 2.3 주요 실행 흐름 (단일 검색)

1. `SearchPanel._on_search()` — 공항 코드·날짜·국내선 모드 UI 검증 (`ui/search_panel_actions.py`)
2. `SearchSingleMixin._start_search()` — worker 중복 실행 차단, `SearchWorker` 생성 (`app/mainwindow/search_single.py`)
3. `SearchWorker.run()` — 취소 플래그 확인 후 `FlightSearcher.search()` 호출 (`ui/workers_search.py`)
4. `FlightSearcher` — 프로세스 공유 캐시 조회 후 `InterparkAirSource.search()` (`scraping/searcher.py`)
5. `run_search()` — Playwright 브라우저 기동 → Interpark URL 이동 → API-first → selector 대기 → DOM/수동 모드 (`scraping/search_flow/orchestration.py`)
6. `_search_finished()` — 결과 렌더링 우선, DB/로그/알림 저장 실패는 분리 처리 (`app/mainwindow/search_single.py`)

### 2.4 Interpark 연동 지점 (실사용 사이트 중심)

| 구분 | URL/경로 | 코드 위치 |
| --- | --- | --- |
| 검색 페이지 | `https://travel.interpark.com/air/search/{route}?...` | `scraping/interpark/urls.py` |
| 국제 API 검색 | `.../international/flights/search/{route}` | `build_interpark_international_api_search_url` |
| 국제 API 결과 | `.../international/flights/search/v2/{key}` + `/status` | `scraping/international/api.py` |
| 국내 API 결과 | `.../domestic/flights/search/{key}` (POST pagination) | `scraping/domestic/api.py` |
| search key 탐지 | `performance.getEntriesByType('resource')` URL 패턴 | `scraping/playwright_api.py` |
| DOM fallback | Playwright selector + in-page JS | `scraping/interpark/selectors.py`, `scraping/interpark/scripts/*` |

### 2.5 문서 vs 구현 정합성

| 항목 | 문서 | 실제 구현 | 판정 |
| --- | --- | --- | --- |
| API-first 우선 | README/Claude.md 일치 | 국제·국내 **편도**는 API-first 시도 | 일치 |
| API 성공 시 DOM 미실행 | 규칙 명시 | `extract_international_prices` / `extract_domestic_flights_data`에서 API 성공 시 DOM 생략 | 일치 |
| 국내선 왕복 dedup key | API key·혜택가·라벨 포함 | `combine_domestic_round_trip`는 포함, **편도 `build_domestic_results`는 미포함** | 부분 불일치 |
| child/infant 지원 | URL builder는 파라미터 보유 | GUI·`SearchWorker`·`run_search`에 child/infant 전달 반영 | **구현 완료** (2026-07-02) |
| 테스트 123 passed | README/Claude.md | 의존성 설치 후 `123 passed in 6.78s` 확인 | 일치 |
| `InterparkTicketSource` | placeholder | `NotImplementedError` | 의도적 비활성 |

---

## 3. High-Risk Issues

### 3.1 Interpark search key 탐지가 Performance API URL 패턴에 고정됨

* **위치:** `scraping/playwright_api.py` — `find_search_keys()`, `find_latest_search_key()`
* **문제:** search key를 브라우저 `performance` 리소스 URL에서 `DOMESTIC::` / `INTERNATIONAL::` 접두와 `/domestic/flights/search/`, `/international/flights/search/v2/` 문자열로 추출한다. Interpark가 API 경로·키 포맷·리소스 로딩 방식을 바꾸면 key를 찾지 못한다.
* **영향:** API 추출 전체 실패 → DOM fallback 또는 수동 모드로 강등. 백그라운드 검색(알림/다중검색)은 수동 모드 없이 **빈 결과** 가능.
* **근거:** `find_search_keys`의 `pattern`/`prefix` 하드코딩, `domestic/api.py`·`international/api.py`가 `find_latest_search_key`에 의존.
* **권장 수정 방향:** (1) 초기 search API 응답의 `key` 필드 우선 사용(국제선은 일부 구현됨), (2) network 이벤트 리스너로 응답 본문에서 key 캡처, (3) live smoke에 key-missing 실패율 메트릭 추가.
* **우선순위:** **High**

### 3.2 국제선 API status 폴링 상한이 짧을 수 있음

* **위치:** `scraping/international/api.py` — `_extract_international_prices_via_api()`
* **문제:** `max_polls = DATA_WAIT_TIMEOUT_SECONDS`(30)이고 루프마다 1초 대기. Interpark 검색이 30초 이상 `COMPLETE`가 아니면 `international_api_status_timeout`으로 종료된다.
* **영향:** 성수기·장거리 노선에서 결과가 있는데도 API 경로가 실패하고 DOM fallback으로 넘어가거나 백그라운드 모드에서 0건 처리.
* **근거:** `for attempt in range(max_polls)` + `page.wait_for_timeout(1000)`.
* **권장 수정 방향:** status 응답의 progress/backoff 힌트 반영, 폴링 상한을 runtime 상수로 분리(예: 60~90초), timeout telemetry를 UI에 노출.
* **우선순위:** **High**

### 3.3 국내선 왕복 검색이 API-first 경로에서 제외됨

* **위치:** `scraping/search_flow/api_first.py` — `_try_api_first_extraction()`
* **문제:** `is_domestic and is_round_trip`이면 즉시 `[]` 반환하여 API-first를 시도하지 않는다.
* **영향:** 왕복 국내선은 selector 대기·DOM 클릭·왕복 화면 전환(`_handle_domestic_round_trip`)에 의존. Interpark UI/DOM 변경에 취약하고 검색 시간이 길어진다.
* **근거:** `api_first.py` 31~32행; 왕복 처리는 `domestic_flow.py`의 클릭 기반 흐름.
* **권장 수정 방향:** Interpark 왕복 API 계약 조사 후 편도와 동일한 API-first 시도 추가. 최소한 왕복 전용 live smoke를 CI 주기 실행에 포함.
* **우선순위:** **High**

### 3.4 DOM fallback selector/JS가 Interpark UI 구조에 강하게 결합됨

* **위치:** `scraping/interpark/selectors.py`, `scraping/interpark/scripts/domestic.py`, `scraping/interpark/scripts/international.py`
* **문제:** 대기 selector가 `button:has-text("원")`, `li[data-index]` 등 UI 텍스트/속성에 의존. DOM 추출 JS도 fixture 기반 회귀만 존재.
* **영향:** API 실패 시 자동 추출 전체 중단. 수동 모드(foreground)로만 복구 가능.
* **근거:** `tests/test_selector_regression.py`는 HTML fixture 기반; live DOM 구조 변경 감지 테스트 없음.
* **권장 수정 방향:** live smoke에 selector wait 성공률 기록, selector 후보를 Interpark 실페이지에서 주기 검증, 실패 시 telemetry `selector_name` 집계 대시보드화.
* **우선순위:** **High**

### 3.5 Scraper 내부에 협조적 취소(checkpoint) 없음

* **위치:** `scraping/search_flow/orchestration.py`, `scraping/domestic/api.py`, `scraping/international/api.py`, `scraping/domestic/dom.py`
* **문제:** `is_cancelled`/`cancel` 처리는 `ui/workers_*.py`에만 존재. API pagination·status polling·DOM scroll 루프는 중간에 취소를 확인하지 않는다.
* **영향:** 사용자가 Esc로 취소해도 브라우저 `close()` 전까지 수십 초~수 분 CPU/네트워크 점유 가능. `worker.wait(5000)` 실패 시 좀비 작업 잔존(문서화된 "강제 종료 안 함" 정책).
* **근거:** `grep is_cancelled scraping/**` 결과 없음; `worker_lifecycle.py`는 wait 실패 시 경고만 표시.
* **권장 수정 방향:** `run_search`에 cancel token 전달, pagination/poll/scroll 루프마다 확인, Playwright context close 시 fetch 중단 보장.
* **우선순위:** **High**

### 3.6 국내선 편도 결과 dedup key가 프로젝트 계약과 불일치

* **위치:** `scraping/domestic/results.py` — `build_domestic_results()`
* **문제:** dedup key가 `f"{airline}_{dep_time}_{arr_time}_{price}"`만 사용. Claude.md 규칙(시간·편명·API key·혜택가/라벨 포함)과 다르다. 왕복 조합(`combine_domestic_round_trip`)은 상세 key를 쓰지만 편도 경로는 혜택가 다른 동일 기본가 항목이 누락될 수 있다.
* **영향:** 동일 편·동일 기본가·다른 카드 혜택가가 하나로 합쳐져 사용자에게 잘못된 최저 혜택가 표시 가능.
* **근거:** `build_domestic_results` 72~75행 vs `helpers.combine_domestic_round_trip` 49~65행.
* **권장 수정 방향:** 편도 dedup에 `item.get("key")`, `benefitPrice`, `benefitLabel`, `flightNumber` 포함. 회귀 테스트 추가.
* **우선순위:** **Medium**

### 3.7 자동 가격 알림이 기본가(`price`)만 비교함

* **위치:** `ui/workers_alerts.py` — `AlertAutoCheckWorker.run()`
* **문제:** `current_price = min(r.price for r in results)`만 사용. 국내선에서 실질 최저가가 `benefit_price`인 경우 알림이 누락되거나 늦게 발동.
* **영향:** 알림 신뢰도 저하(특히 국내선 LCC 카드 혜택가).
* **근거:** 106~107행; 국내선 API는 `benefit_price`/`benefit_label`을 채움(`scraping/domestic/api.py`).
* **권장 수정 방향:** `effective_price = benefit_price if benefit_price > 0 else price` 정책을 알림·히스토리·UI 최저가 표시에 통일.
* **우선순위:** **Medium**

### 3.8 백그라운드 검색 실패 시 수동 모드 미지원

* **위치:** `scraping/search_flow/orchestration.py` — `background_mode` 분기
* **문제:** DOM/API 실패 시 `background_mode=True`이면 수동 모드 전환 없이 break. 자동 알림·다중 목적지·날짜 범위 검색이 모두 `background_mode=True`.
* **영향:** Interpark 일시 장애 시 사용자 개입 없이 빈 결과·알림 실패 누적.
* **근거:** 231~233, 270~271, 316~318행 등.
* **권장 수정 방향:** 백그라운드 실패 원인을 `last_error`/알림 DB에 구조화 저장, 재시도 백오프, (추정) foreground 검색으로 사용자에게 재시도 유도.
* **우선순위:** **Medium**

### 3.9 병렬 검색 + 자동 알림의 Playwright 인스턴스 경합

* **위치:** `ui/workers_parallel.py`, `ui/workers_alerts.py`, `app/mainwindow/auto_alert.py`
* **문제:** 동시 worker 상한 2(`MAX_PARALLEL_WORKERS`). 각 worker가 독립 Playwright 브라우저를 띄움. 자동 알림은 검색 worker 실행 중 시작하지 않지만, 타이머는 검색 종료 후 즉시 재가동 가능.
* **영향:** 메모리 급증, Interpark rate limit·봇 차단 가능성 증가(추정), 저사양 PC에서 불안정.
* **근거:** `MultiSearchWorker` ThreadPoolExecutor, `AlertAutoCheckWorker` 알림마다 `FlightSearcher` 생성.
* **권장 수정 방향:** 브라우저 풀/단일 headless 세션 재사용, 알림 배치 검색 간 throttle, 동시 브라우저 수 설정화.
* **우선순위:** **Medium**

### 3.10 잘못된 날짜 문자열이 UI 밖 경로에서 런타임 예외 유발 가능

* **위치:** `core/search_params.py` — `normalize_search_date()`; `scraping/interpark/urls.py` — `normalize_interpark_date()`
* **문제:** `normalize_search_date`는 파싱 실패 시 **원문 문자열을 그대로 반환**. 이후 `run_search`에서 `normalize_interpark_date`가 `ValueError`를 던질 수 있다.
* **영향:** UI 검색은 `QDate`로 방어되지만, 세션 JSON·설정 import·프로그램matic 호출에서 검색 크래시.
* **근거:** `normalize_search_date` 18~23행; `normalize_interpark_date` 24행 raise.
* **권장 수정 방향:** `normalize_search_params`에서 invalid date를 `""`로 정규화하고 required-field 검증 강화.
* **우선순위:** **Medium**

### 3.11 `InterparkAirSource` 파라미터 키 불일치 (직접 호출 시)

* **위치:** `scraping/search_sources.py` — `InterparkAirSource.build_search_url()`, `.search()`
* **문제:** `destination`, `departure_date` 키를 기대. 앱 내부는 `dest`, `dep`를 `FlightSearcher`가 변환하지만, search source를 직접 쓰는 외부 코드는 빈 목적지/날짜로 URL이 생성될 수 있다.
* **영향:** facade 우회 호출 시 침묵 실패.
* **근거:** `search_sources.py` 52~54, 69~71행 vs `core/search_params.py` 49~52행.
* **권장 수정 방향:** `InterparkAirSource` 진입점에서 `normalize_search_params` 적용.
* **우선순위:** **Low**

### 3.12 API pagination cap으로 인한 결과 절단 (의도된 동작이나 사용자 인지 부족)

* **위치:** `scraping/domestic/api.py`, `scraping/international/api.py`, `scraping/interpark/runtime.py`
* **문제:** `DOMESTIC_API_MAX_PAGES=30`, `INTERNATIONAL_API_MAX_PAGES=50` 초과 시 truncation. telemetry에는 남지만 UI는 최저가만 강조.
* **영향:** 희귀 최저가가 cap 밖 페이지에 있으면 누락. live smoke도 cap 초과를 **통과 조건**으로만 다룸(`fail-on-cap` 옵션).
* **근거:** README live smoke 예시 `api_pages_truncated=True` 국제선; runtime 상수.
* **권장 수정 방향:** cap 절단 시 결과 테이블/로그에 경고 배지, 사용자 설정으로 cap 조정.
* **우선순위:** **Low**

---

## 4. Potential Functional Gaps

아래는 코드·문서 기반 **추정** 또는 **미구현** 항목이다.

| 항목 | 근거 | 확실도 |
| --- | --- | --- |
| 소아/유아 인원 검색 | GUI spin + `SearchWorker`/`run_search` 전달 | **구현 완료** |
| Interpark 왕복 국내선 API-first | `api_first.py` 조기 return 제거 | **구현 완료** |
| `InterparkTicketSource`(NOL ticket) 미구현 | `NotImplementedError` placeholder | **확실** |
| Windows 외 OS 공식 미지원 | README Requirements Windows 10/11, `LOCALAPPDATA` 경로 | **확실** |
| 실시간 Interpark DOM 구조 회귀 | `scripts/live_selector_probe.py` + `.github/workflows/live-smoke.yml` (workflow_dispatch) | **부분 완료** — CI는 수동 트리거 |
| 국내선 왕복 클릭이 최저가 가는편 1개만 선택 | `domestic_flow.py` `best_outbound = min(...)` | **확실** — Interpark UI가 특정 가는편 선택을 요구하는지는 **추정** |
| Interpark 봇/레이트리밋 대응 전략 부재 | headless+리소스 차단만 적용, 전용 backoff 없음 | **추정** |
| 검색 캐시 정책 | foreground 180s / background 90s / alert 45s (`cache_mode`) | **구현 완료** |
| 설정 import 시 history 일부 필드 즉시 정규화 안 됨 | `import_settings`가 리스트를 merge 후 save 시점에 정규화 | **추정** |
| 가격 알림에 `is_domestic`/혜택가 정책 필드 없음 | DB alert 스키마·worker 비교 로직에 혜택가 분기 없음 | **확실** |
| 국제선 `freeBaggageOnly=false` 고정 | `urls.py` 하드코딩, UI 옵션 없음 | **확실** |

### Interpark 사이트 변경 시 우선 점검할 코드 (수정 후보 맵)

| Interpark 변경 시나리오 | 영향 모듈 | 증상 |
| --- | --- | --- |
| API base path/version 변경 | `interpark/urls.py`, `playwright_api.py`, `international/api.py`, `domestic/api.py` | key missing, HTTP failed telemetry |
| search key prefix/format 변경 | `playwright_api.py` `find_search_keys` | domestic/international API 0건 |
| 국제 status 응답 스키마 변경 | `international/api.py`, `international/normalizer.py` | status_timeout, payload_mismatch |
| 국내 왕복 UI 플로우 변경 | `search_flow/domestic_flow.py`, `interpark/scripts` click JS | outbound_only 결과, manual_reason `domestic_return_key_missing` |
| 가격 카드 DOM 구조 변경 | `interpark/scripts/domestic.py`, `international.py`, `selectors.py` | DOM fallback 실패 |
| 리소스 차단/headless 탐지 강화 | `playwright_browser.py`, `orchestration.py` | BrowserInitError, 빈 페이지 |

---

## 5. Recommended Fix Plan

### 1단계 — 즉시 수정 (사용자 영향·Interpark 연동 안정성)

1. **Interpark key 캡처 이중화** — performance URL 패턴 + 초기 API 응답 `key` + (가능 시) network listener.
2. **국제선 status 폴링 상한·backoff 조정** — timeout telemetry를 UI/로그에 표시.
3. **Scraper 취소 checkpoint** — API pagination/status poll/DOM scroll 루프에 cancel token 전파.
4. **국내선 편도 dedup key 보강** — API key·혜택가·라벨·편명 반영(Claude.md 계약 정합).
5. **가격 알림 effective price 정책** — `benefit_price` 반영 및 테스트 추가.

### 2단계 — 안정성 개선

1. **국내선 왕복 API-first** 조사·구현 또는 왕복 전용 live smoke·실패율 모니터링 강화.
2. **백그라운드 실패 UX** — 알림/다중검색 실패 사유 구조화·재시도·사용자 알림.
3. **병렬 브라우저 자원 제한** — 동시 실행 수·throttle·브라우저 재사용.
4. **날짜 정규화 엄격화** — invalid date 조기 차단(세션/import/API 호출 포함).
5. **`InterparkAirSource` 입력 정규화** — `normalize_search_params` 공용 적용.
6. **API page cap 절단 UI 경고** — truncation 시 결과 신뢰도 표시.

### 3단계 — 구조 개선

1. ~~**Interpark adapter 계층**~~ — `scraping/interpark/adapter.py` (`InterparkAdapterConfig`, `get_interpark_adapter`).
2. ~~**Live DOM 회귀 파이프라인**~~ — `scripts/live_selector_probe.py`, `live_smoke_search.py --selector-probe`, `live-smoke.yml`.
3. ~~**소아/유아 UI**~~ — `ui/search_panel_build.py`, `search_panel_params.py`, `SearchWorker` 전달.
4. ~~**검색 캐시 정책 분리**~~ — `cache_mode` foreground/background/alert TTL + child/infant cache key.
5. ~~**MainWindow 통합 테스트**~~ — truncation 경고, child/infant worker, persist 실패 시 렌더링 (`tests/test_gui_behaviors.py`).
6. ~~**Network listener key 캡처**~~ — `scraping/interpark/network_listener.py`, orchestration/playwright_scraper 연결.

---

## 6. Test Recommendations

### 6.1 Interpark 연동 (최우선)

| 테스트 | 목적 | 유형 |
| --- | --- | --- |
| `find_search_keys` URL 패턴 변경 회귀 | resource URL 포맷 변경 감지 | unit + recorded HAR |
| 국제 status polling timeout 경계 | 30초·60초 mock 응답 | unit |
| 국내 왕복 `api_first` 비활성 계약 | 왕복 시 API-first 미호출 명시 | unit (현재 동작 고정) |
| domestic one-way dedup with benefit | 동일 기본가·다른 혜택가 2건 보존 | unit |
| alert effective price | benefit_price < target 시 hit | unit |
| live smoke 왕복 국내선 route 추가 | `GMP-CJU` 왕복 등 | manual/scheduled script |
| selector live probe | headless로 실제 Interpark 결과 페이지 selector match율 | scheduled smoke |

### 6.2 비동기·취소

| 테스트 | 목적 |
| --- | --- |
| pagination 중 cancel → N초 내 run 종료 | scraper checkpoint 검증 |
| `MultiSearchWorker` 취소 후 executor shutdown | 좀비 future 없음 |
| 검색 중 alert timer fire → alert 미시작 | `auto_alert.py` 가드 |

### 6.3 데이터·입력 검증

| 테스트 | 목적 |
| --- | --- |
| `normalize_search_params({"dep": "invalid"})` | scrape 전 차단 |
| session JSON invalid date load | 예외 없이 거부 또는 빈 dep |
| `InterparkAirSource.search({"dest": "NRT", ...})` | normalize 후 정상 URL |

### 6.4 문서/환경 정합성

| 테스트 | 목적 |
| --- | --- |
| CI/dev container에 `playwright install chromium` | README 123 passed 재현 |
| `scripts/live_smoke_search.py` 왕복·혜택가 시나리오 확장 | 문서 baseline 갱신 |

### 6.5 CodeGraph 기준 테스트 공백 (우선 보강 후보)

CodeGraph blast radius상 **caller는 많으나 dedicated test가 없거나 약한** 심볼:

- `normalize_search_params` / `validate_airport_code`
- `wait_for_results`
- `_try_api_first_extraction`
- `_recover_database_file`
- `MainWindow` mixin 통합(검색→결과→persist 흐름)

---

## 부록: 감사 시 수행한 분석 명령

- CodeGraph MCP: `PlaywrightScraper search flow`, `SearchWorker cancel`, `run_search api_first`, `find_latest_search_key`, `FlightDatabase migration`, `search_single MainWindow` 등
- 보조 grep: Interpark URL 참조, `is_cancelled`, `child`/`infant`, dedup, `destination` 키 사용처
- `pytest`: 초기에는 `playwright` 미설치로 collection error → 후속 설치 후 `123 passed in 6.78s`