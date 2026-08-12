# Project Audit

감사 기준일: 2026-08-12  
감사 범위: 기능 구현(특히 최근 추가된 사이트 계약/URL/키 만료/확장 필드/export), Interpark 연동, 상태·비동기·데이터 흐름, 테스트·문서 정합성  
분석 방법: `README.md`, `claude.md` 선독 → CodeGraph MCP(`codegraph_explore`) 호출 관계·영향 범위 → 보조 grep/파일 열람 → `python -m pytest -q`

> 후속 구현 (2026-08-12): 본 문서 High-Risk / Fix Plan / Test Recommendations를 코드에 반영.  
> 검증: `pytest` **153 passed**, `pyright` 0 errors, LF check OK.  
> 문서/스펙/gitignore 정합성 동기화 후 본 기준선을 운영 기준으로 사용한다.  
> 추정 사항은 **(추정)** 으로 명시한다.

## 0. Remediation Status (2026-08-12)

| ID | 상태 | 요약 |
| --- | --- | --- |
| H1 | **Fixed** | 국내 왕복 API-first → `domestic_flow` 조합 경로 |
| H2 | **Fixed** | 키 만료 시 exclude 대기 + soft reload 재시도 |
| H3 | **Fixed** | ResultTable 공항/수하물/잔여석 컬럼 |
| H4 | **Fixed** | `combine_domestic_round_trip` 메타 전파 |
| H5 | **Fixed** | README/claude.md 기준선·규칙 갱신 |
| H6 | **Fixed** | Multi/DateRange child·infant 전달 |
| H7 | **Fixed** | 테이블 최저가/색상 `effective_flight_price` |
| H8 | **Fixed** | `alert_hit_modal_enabled` 설정 |
| H9 | **Improved** | 국내 공항 필드 추출 휴리스틱 확장 |
| H10 | **Improved** | `page_fetch_json` 실패 meta/metrics 기록 |

---

## 1. Executive Summary

**전체 위험도: Medium–High** (외부 Interpark 계약 의존 + 최근 확장 필드의 UI 미연결 + 국내 왕복 API-first 경로 버그 가능성)

Flight Bot v2.5는 Playwright로 Interpark Air를 열고 **동일 출처 API 우선 → DOM fallback → 수동 모드**로 결과를 추출하는 PyQt6 데스크톱 앱이다. facade/`core`/`scraping`/`storage`/`ui` 분리, page-cap, telemetry, formula-safe export, 회귀 테스트(현재 149 passed)는 비교적 견고하다.

최근 구현(국내 `a:GMP` URL, 키 만료 재시도, `FlightResult` 공항/수하물/좌석 필드, export 확장, wait selector 정리)은 **스크래핑 계약 내구성**을 높였지만, 아래가 기능적으로 가장 위험하다.

| 영역 | 요약 | 우선순위 |
| --- | --- | --- |
| 국내 왕복 + API-first | `is_round_trip`이 무시되어 편도 결과로 early-return할 수 있음 | **Critical** |
| 키 만료 재시도 | 페이지 재진입 없이 exclude 대기 → 실효성 제한적 | **High** |
| 확장 필드 UX | 모델/export에는 있으나 결과 테이블·필터·알림 UI 미사용 | **High** |
| 문서 기준선 | README/claude.md가 `123 passed` 등 구 기준선 유지 | **Medium** |
| 왕복 조합 메타 유실 | `combine_domestic_round_trip`이 공항/좌석 등 신규 필드 미전파 | **Medium** |
| 병렬 worker 파라미터 | Multi/DateRange 경로 child/infant 미전달 | **Medium** |

**한 줄 결론:** 스크래핑 인프라는 강화됐지만, **국내 왕복 오케스트레이션 버그 가능성과 “수집만 하고 화면에 안 보이는” 확장 필드**가 사용자 체감 기능 리스크의 중심이다.

---

## 2. Project Understanding

### 2.1 목적 (README / claude.md)

- Interpark 항공권 검색 결과 수집·비교·저장·내보내기
- 국내/국제, 편도/왕복, 좌석 등급, 인원(성인·소아·유아 UI 존재)
- 즐겨찾기, 기록, 세션, 가격 알림, CSV/Excel, SQLite/JSONL telemetry
- 공개 facade 유지: `gui_v2`, `scraper_v2`, `config`, `database`, `scraper_config`

### 2.2 아키텍처 (문서 + CodeGraph)

```text
gui_v2.py
└─ app/main_window.py + app/mainwindow/*   # UI mixins, worker lifecycle, auto alert

ui/workers_* → FlightSearcher (scraping/searcher.py)
  └─ InterparkAirSource → PlaywrightScraper.search
       └─ search_flow/orchestration.run_search
            ├─ build_interpark_search_url (국내 a:/국제 c: 분리)
            ├─ network_listener → search key 캐시
            ├─ api_first → domestic/international API extract
            ├─ wait selectors → DOM fallback
            └─ domestic_flow (왕복 클릭·키 대기·조합)

FlightResult (scraping/models.py)
  → ResultTable / export_helpers / session_manager / DB / alerts
```

**주요 blast radius (CodeGraph):**

| 심볼 | 영향 |
| --- | --- |
| `FlightResult` | search_flow, searcher, international/api, UI, DB, 테스트 등 다수 |
| `FlightSearcher` | workers, live_smoke, alerts |
| `extract_domestic_api_flights_data` | results, scraper facade, key-expiry 경로 |
| `wait_for_search_key` | domestic API, domestic_flow, playwright_search facade |
| `effective_flight_price` | alerts, 일부 결과 처리 |
| `ResultTable` | UI 결과 표시 (확장 필드 미사용) |

### 2.3 검색 실행 흐름 (현재 코드)

1. UI worker → `FlightSearcher.search` (캐시 키: origin/dest/date/cabin/adults/child/infant)
2. `run_search`: 국내 여부 추론, context 설정, browser + listener
3. `build_interpark_search_url(..., is_domestic=...)`  
   - 국내: `a:GMP-a:CJU`  
   - 국제: `c:SEL-c:TYO`
4. `_try_api_first_extraction` → 국내 `_extract_domestic_prices` / 국제 `_extract_prices`
5. 성공 시 **즉시 break** (DOM/왕복 분기 스킵)
6. 실패 시 wait selector → 국내 왕복이면 `domestic_flow` → 아니면 DOM/API 재추출
7. 실패 시 manual mode (background면 중단)

### 2.4 최근 추가 기능 맵

| 기능 | 구현 위치 | 소비자 |
| --- | --- | --- |
| 국내 공항 URL | `urls.resolve_interpark_location` | orchestration, search_sources |
| 키 만료 재시도 | `domestic/api.py` | extract path only |
| 확장 FlightResult 필드 | models + international normalizer | export, session load |
| export 확장 컬럼 | `ui/export_helpers.py` | CSV/Excel |
| wait selector 정리 | `selectors.py` | wait_for_results, probe |

### 2.5 현재 검증 상태 (실측)

```text
python -m pytest -q  → 149 passed
```

문서에 적힌 `123 passed` / `140 passed`는 **현행 기준선과 불일치**.

---

## 3. High-Risk Issues

### H1. 국내 왕복이 API-first 성공 시 편도 결과로 종료될 수 있음

* **위치:** `scraping/search_flow/api_first.py` (`_try_api_first_extraction`),  
  `scraping/search_flow/orchestration.py` (`run_search`, api_first 성공 분기)
* **문제:**  
  - orchestration은 `is_round_trip=bool(return_date)`를 넘기지만, `api_first`는 **파라미터를 사용하지 않음**.  
  - 국내 왕복에서도 `_extract_domestic_prices()`(편도 목록 API)만 호출.  
  - 결과가 비어 있지 않으면 orchestration이 즉시 `break`하여  
    `_handle_domestic_round_trip`(클릭·오는편 키·조합)에 **도달하지 않음**.
* **영향:** 국내 왕복 검색이 가는편 편도 리스트만 반환 → 가격·UX 오판, 알림 오동작 가능.
* **근거:**  
  - `api_first.py`: `is_round_trip` 인자 존재하나 본문 미사용.  
  - `orchestration.py`: `if api_first_results: ... break` 후  
    `if is_domestic and normalized_return_date and found_data: _handle_domestic_round_trip` 는 **api_first 실패 경로에서만** 실행.
* **권장 수정 방향:**  
  - 국내+왕복이면 api_first에서 편도 성공 시 early-return 금지, 또는  
    api_first 단계에서 바로 `domestic_flow` 호출.  
  - 회귀 테스트: 왕복 + domestic API mock 성공 시 `is_round_trip=True` 조합 결과 필수.
* **우선순위:** **Critical**

---

### H2. 국내 `INVALID_CACHE_SEARCH_KEY` 재시도가 “새 키 수신”에 의존해 실효성이 낮을 수 있음

* **위치:** `scraping/domestic/api.py` (`_refresh_domestic_search_key`, `_is_invalid_cache_search_key`)
* **문제:** 만료 시 `wait_for_search_key(exclude_keys={expired})`만 수행.  
  페이지를 다시 열거나 검색을 재트리거하지 않으면 performance/cache에 **대체 키가 없을** 수 있음.  
  유닛 테스트는 mock으로 새 키를 주입하므로 통과하지만, 라이브에서는 재시도 실패 → `domestic_api_key_expired` 후 DOM/manual로 떨어질 가능성.
* **영향:** 국내 API 안정성 개선 체감이 제한적; headless 자동 검색/알림 실패율 유지 가능.
* **근거:**  
  - `_refresh_domestic_search_key`는 wait/resolve만 수행, `page.goto`/재검색 없음.  
  - 실사이트 감사에서 동일 키 재POST 시 `INVALID_CACHE_SEARCH_KEY` 관찰된 바 있음.
* **권장 수정 방향:**  
  - 만료 시 (1) 짧은 대기 + 네트워크 재캡처, 실패 시 (2) 동일 URL soft reload 또는 orchestration 레벨 1회 재시도.  
  - 키 age telemetry (`key_captured_at` → fetch latency).
* **우선순위:** **High**

---

### H3. 확장 필드가 결과 테이블·필터에 연결되어 있지 않음 (기능 “반쪽” 구현)

* **위치:**  
  - 생산: `scraping/models.py`, `international/normalizer.py`, `domestic/results.py`  
  - 소비: `ui/export_helpers.py`, `app/session_manager.py`  
  - **미소비:** `ui/components_result_table.py` (컬럼: 항공사/가격/시간/경유/출처만)
* **문제:** 공항 코드, 수하물, 잔여석, 추천 태그, +N일 도착이 수집·export만 되고 **메인 UI에서 확인 불가**.  
  필터 패널도 해당 필드 조건 없음.
* **영향:** “추가 기능” 사용자 가치가 export 사용자에게만 국한.  
  국제 멀티공항(NRT/HND) 구분 목적이 UI에서 달성되지 않음.
* **근거:** CodeGraph/grep 상 `departure_airport`/`baggage` 참조가 models·export·session·tests에 편중.  
  `ResultTable` 헤더는 9컬럼 고정, 확장 필드 미표시.
* **권장 수정 방향:**  
  - 테이블 컬럼 또는 상세 툴팁에 공항/수하물/잔여석 표시.  
  - 최소: 가격 툴팁·항공사 툴팁에 확장 메타 포함.
* **우선순위:** **High**

---

### H4. 국내 왕복 조합 시 신규 메타데이터 유실

* **위치:** `scraping/domestic/helpers.py` (`combine_domestic_round_trip`)
* **문제:** 조합 시 `FlightResult`에 airline/time/price/benefit만 설정.  
  `depAirport`/`arrAirport`/`seatAvailability` 등이 raw item에 있어도 조합 결과에 반영 안 됨.
* **영향:** 왕복 결과 export/세션에서 확장 필드 공란.
* **근거:** `combine_domestic_round_trip` 생성자 인자 목록에 확장 필드 없음 (CodeGraph 소스).
* **권장 수정 방향:** outbound/return 공항·좌석·편명을 조합 결과에 매핑.
* **우선순위:** **Medium**

---

### H5. 문서·검증 기준선 불일치

* **위치:** `README.md`, `claude.md`, `SCRAPING_AUDIT.md`, (구) audit 메모
* **문제:** 문서 기준선 `123 passed` / 일부 `140 passed` vs 현재 **149 passed**.  
  사이트 계약·contract 패키지 설명은 README 구조에 일부 반영됐으나 기준일(2026-06-11)과 최신 기능 설명이 혼재.
* **영향:** 에이전트/개발자가 구 기준선으로 회귀 오판, 완료 조건 혼선.
* **근거:** 문서 문자열 `123 passed` 다수 vs `pytest` 149.
* **권장 수정 방향:** 기준일·pytest 수·live smoke 결과 일괄 갱신.  
  최근 기능(국내 a: URL, 키 만료, 확장 필드)을 claude.md Scraping/UI 규칙에 명시.
* **우선순위:** **Medium**

---

### H6. Multi/DateRange 병렬 검색이 child/infant를 전달하지 않음

* **위치:** `ui/workers_parallel.py` (`MultiSearchWorker`, `DateRangeWorker` 생성/search 호출)
* **문제:** 단일 검색 UI/worker는 child/infant를 넘기지만, 다중 목적지·날짜 범위 경로는 성인/캐빈 중심.  
  (검색 패널에 spin_child/infant 존재)
* **영향:** 소아/유아 포함 다중 검색 시 Interpark 인원 파라미터 불일치 → 가격 오차.
* **근거:** `MultiSearchWorker.search(...)` 시그니처/호출에 child/infant 없음.  
  `FlightSearcher`/`SearchWorker`는 지원.
* **권장 수정 방향:** worker 인자·UI 연결·캐시 키까지 동일 스키마 정렬.
* **우선순위:** **Medium**

---

### H7. UI 가격 정렬/색상이 기본가 기준 — 알림은 혜택가 반영

* **위치:**  
  - `ui/components_result_table.py` (`flight.price`로 최저가 배지·색상)  
  - `scraping/models.effective_flight_price` (alerts, 일부 로직)
* **문제:** 알림 비교는 `min(price, benefit_price)`인데 테이블 하이라이트는 base `price`.  
  혜택가가 더 낮은 항공편이 “최저가”로 안 보일 수 있음.
* **영향:** 사용자 인지와 알림 발동 기준 불일치.
* **근거:** ResultTable min_price = `min(r.price)`; alerts = `effective_flight_price`.
* **권장 수정 방향:** 표시/정렬 키를 effective price로 통일하거나, 혜택가 병기·토글.
* **우선순위:** **Medium**

---

### H8. 자동 알림 적중 시 모달 사용 (규칙과의 긴장)

* **위치:** `app/mainwindow/auto_alert.py` (`_on_auto_alert_hit` → `QMessageBox.information`)
* **문제:** claude.md는 자동 알림 **실패**를 모달 대신 상태/로그로 두라고 함(준수).  
  적중은 모달을 띄움 — 백그라운드 장기 운영 시 모달 스택/포커스 방해 가능.
* **영향:** 운영 UX; 기능 오류는 아님.
* **근거:** 코드 상 hit 시 QMessageBox 호출.
* **권장 수정 방향:** 설정으로 모달/토스트/로그 전용 선택; 기본은 비모달 알림 검토.
* **우선순위:** **Low**

---

### H9. 국내 공항 필드 추출 필드명이 실 API와 어긋날 수 있음 **(추정 포함)**

* **위치:** `scraping/domestic/api.py` (`_normalize_domestic_api_item`)
* **문제:** `departureAirport`/`originAirport` 등 휴리스틱 키를 읽음.  
  라이브 덤프에서 국내 item shape가 항상 확인되진 않았고, 키가 다르면 공항 필드가 항상 빈 문자열.
* **영향:** 국내 확장 공항 컬럼 공란 (export 포함).
* **근거:** 코드 휴리스틱; 국제선은 segment path로 실측 확인됨. 국내 필드명은 **추정 리스크**.
* **권장 수정 방향:** live payload fixture 고정 후 키 확정; contract/schemas에 문서화.
* **우선순위:** **Medium** (확정 전 추정)

---

### H10. `page.evaluate` 기반 fetch — 인젝션 위험은 낮으나 유지보수 취약

* **위치:** `scraping/playwright_api.page_fetch_json`
* **문제:** URL/body를 JS 문자열로 삽입. 값은 `json.dumps`로 감싸 상대적으로 안전.  
  외부 URL을 그대로 넣지 않는 한 XSS/주입 위험은 낮음.  
  다만 대형 스크립트 문자열은 디버깅·오류 처리가 어렵고, evaluate 실패 시 `{}`로 삼켜 telemetry만 남을 수 있음.
* **영향:** 실패 원인 파악 지연; 보안 이슈보다 관측성 이슈.
* **근거:** `credentials: 'include'`, 실패 시 empty dict.
* **권장 수정 방향:** meta.ok=false를 상위에서 명시 실패로 승격하는 경로 보강.
* **우선순위:** **Low–Medium**

---

## 4. Potential Functional Gaps

| 갭 | 설명 | 확실성 |
| --- | --- | --- |
| 국내 왕복 API-only 경로 | 클릭 없이도 오는편 키를 얻는 공식 API 여부 미확인 | **추정** |
| UI 확장 필드 | 공항/수하물/좌석 테이블·필터 부재 | **확실** |
| API filter/sort 카탈로그 | 국제 payload의 `filter`/`sort` 미사용 | **확실** (고도화) |
| bestItems | 국내 payload 키 존재 이력, 미사용 | **확실** (활용은 선택) |
| 키 만료 후 soft reload | 재시도 전략에 없음 | **확실** |
| Multi/DateRange child·infant | 미전달 | **확실** |
| 결과 테이블 effective price | 혜택가 정렬 미적용 | **확실** |
| DB schema for new fields | 결과는 JSON/dict 저장 가능성 높음; 정규 컬럼 없음 | **추정** (스키마 의존) |
| 알림 조건 확장 | 직항/공항/수하물 조건 없음 | **확실** (미구현 기능) |
| 문서 기준선 | 123/140 vs 149 | **확실** |
| live smoke CI 상시화 | workflow_dispatch 수준으로 추정 | **추정** |
| 국제 freeBaggageOnly 토글 | URL 쿼리 고정 `false` | **확실** |

---

## 5. Recommended Fix Plan

### 1단계 — 즉시 수정 (기능 정확성)

1. **국내 왕복 + API-first 분기 수정** (H1)  
   - 왕복이면 편도 api_first 성공으로 break 금지  
   - 테스트: 왕복 mock → combined round-trip only
2. **키 만료 시 페이지 재진입 또는 orchestration 재시도** (H2)  
   - exclude-wait만으로 부족할 때의 2차 전략
3. **문서 기준선 갱신** (H5)  
   - README/claude.md: 149 passed, 최근 기능 bullet

### 2단계 — 안정성·체감 개선

4. ResultTable/툴팁에 공항·수하물·잔여석·혜택가 표시 (H3, H7)
5. `combine_domestic_round_trip` 메타 전파 (H4)
6. Multi/DateRange child·infant 정렬 (H6)
7. 국내 공항 필드 live fixture 고정 (H9)

### 3단계 — 구조 개선

8. API filter/sort/bestItems 연동 설계
9. 알림 조건 확장(공항/직항/수하물) 및 모달 정책 옵션 (H8)
10. contract 패키지 + live probe를 릴리스 게이트로 고정
11. `page_fetch_json` 실패 전파·관측 강화 (H10)

---

## 6. Test Recommendations

### 필수 추가

| 테스트 | 목적 |
| --- | --- |
| `test_domestic_round_trip_skips_one_way_api_first_break` | H1 회귀 — 왕복+return_date에서 api_first 편도 성공이어도 조합 경로 진입 |
| `test_refresh_key_requires_new_key_or_reload` | H2 — exclude 후 키 없을 때 expired reason, reload 전략 단위 테스트 |
| `test_combine_round_trip_preserves_airports_and_seats` | H4 |
| `test_result_table_shows_or_tooltips_extended_fields` | H3 (UI 반영 후) |
| `test_multi_search_worker_forwards_child_infant` | H6 |

### 보강

| 테스트 | 목적 |
| --- | --- |
| 국제 normalizer: `addDay>0`, QUANTITY 수하물, 왕복 schedules[1] | 확장 필드 완전성 |
| export 컬럼 수/헤더 회귀 스냅샷 | export 정책 고정 |
| `build_interpark_search_url` GMP/ICN/SEL/국제 매트릭스 | URL 계약 |
| session load/save roundtrip of new FlightResult fields | session_manager |
| live: `live_selector_probe --require-search-key --check-api-shape` | 릴리스 전 수동/CI optional |

### 현재 테스트 강점

- 국내 page-cap, 키 만료 mock 재시도, 국제 normalizer 공항/수하물, export 확장 컬럼, URL 공항 유지 등은 **이미 커버**.
- 약점: **orchestration 통합 경로(왕복+api_first)**, UI 테이블, 병렬 worker 인원 파라미터.

---

## Appendix A. 문서 vs 구현 정합표

| 항목 | 문서 | 구현 | 상태 |
| --- | --- | --- | --- |
| API-first | claude.md | search_flow | 일치 (왕복 예외 버그 가능) |
| page-cap telemetry | claude.md | domestic/international api | 일치 |
| 혜택가 분리 | claude.md | models + domestic | 일치; UI 정렬은 base price |
| 국내 왕복 dedup | claude.md | combine helpers | 일치 (확장 필드 미포함) |
| formula-safe export | claude.md | export_helpers | 일치 + 컬럼 확장 |
| 자동 알림 실패 non-modal | claude.md | auto_alert DB fail path | 실패 경로 일치; hit는 modal |
| pytest 123 | README/claude | 149 passed | **불일치** |
| 국내 a: 공항 URL | docs/interpark_site_contract | urls.py | 일치 |
| 확장 필드 UI | (문서 미기재) | 모델/export only | 문서 공백 |

---

## Appendix B. 최근 추가 기능 감사 요약

| 기능 | 구현 품질 | 잔여 리스크 |
| --- | --- | --- |
| 국내 `a:GMP` URL | 양호, 단위 테스트 있음 | 실사이트 smoke로 김포-only 결과 재확인 권장 |
| 키 만료 재시도 | 구조 있음, mock 테스트 있음 | 라이브 재진입 전략 부족 (H2) |
| FlightResult 확장 | normalizer/export/session 반영 | UI 미연결 (H3), 왕복 조합 유실 (H4) |
| wait selector 정리 | 실측 반영 | DOM fallback 자체 취약성은 여전 |
| contract 패키지 | 엔드포인트 집중화 | 페이로드 필드 문서/fixture 지속 갱신 필요 |

---

*End of audit. 코드 변경 없음 — 리포트 전용.*
