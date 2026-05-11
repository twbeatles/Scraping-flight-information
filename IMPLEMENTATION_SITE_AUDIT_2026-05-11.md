# Flight Bot implementation and live-site audit - 2026-05-11

- 대상 저장소: `D:\twbeatles-repos\Scraping-flight-information`
- 기준 문서: `README.md`, `claude.md`, `SCRAPING_AUDIT.md`
- 실제 사이트 확인 대상: NOL 인터파크 투어 항공 검색 `https://travel.interpark.com/air/search`
- 점검 기준일: 2026-05-11
- 최초 작성 checkout: `main` at `c691dae`, `origin/main`보다 1 commit behind
- pull 이후 재점검 checkout: `main` at `0ef2406`, `origin/main`과 일치

## 요약

최초 감사 및 pull 이후 재점검 시점에는 로컬 테스트와 타입 검사가 통과해도 실제 인터파크 항공 사이트에서 문서의 핵심 계약인 "국내선/국제선 API-first 추출"이 깨져 있었다. 사이트 API 자체는 살아 있었지만, 앱의 공통 API POST helper가 JSON body를 잘못 전달하고 국내선 filter payload도 실제 사이트 계약보다 넓어 API payload mismatch로 떨어졌다. 그 결과 국제선과 국내선 모두 실제 실행에서는 API 경로가 아니라 DOM fallback에 의존했다.

pull 이후 들어온 `0ef2406 Stabilize scraping diagnostics and packaging`은 `manual_reason` 라벨, API 실패 metadata, `scripts/live_smoke_search.py`, `scraping.manual_reasons` 패키징 반영을 추가해 진단성은 개선했다. 하지만 live smoke 결과 기준으로 API-first 실패 자체는 해결되지 않았다.

2026-05-11 구현으로 아래 항목은 모두 반영했다.

1. `page_fetch_json()` POST body 직렬화 수정 및 회귀 테스트 추가
2. 인터파크 초기 API URL builder를 실제 사이트의 `CITY`/`AIRPORT` route type과 맞춤
3. 검색 패널 직접 공항 코드 입력이 이전 콤보 선택값으로 덮이는 문제 수정
4. DOM selector 대기 이후 API 추출을 시도하는 흐름을 진짜 API-first로 재배치
5. 국제선 카드/결제 조건과 API 실패 사유 telemetry를 보강

구현 후 live smoke 기준으로 국내선 `GMP->CJU`는 `source=domestic_api`, 국제선 `ICN->NRT`는 `source=international_api`로 복구됐다.

## 2026-05-11 구현 완료 결과

수정 반영 항목:

- `scraping/playwright_api.py`: POST body를 JSON 문자열로 전달하도록 수정
- `scraping/playwright_domestic.py`: 국내선 API filter를 최소 `byCabins` payload로 조정하고 실패 code/message telemetry 추가
- `scraper_config.py`: 국제선 API fallback URL을 `CITY:`/`AIRPORT:` route type으로 생성
- `ui/search_panel_params.py`: editable 공항 콤보 직접 입력값 우선 처리
- `scraping/playwright_search.py`: page load 직후 API 추출을 먼저 시도하고 실패 시 DOM wait/fallback으로 전환
- `scraping/playwright_results.py`: 국제선 API fare의 혜택가/혜택 라벨 보존
- `scripts/live_smoke_search.py`: 문서 명령 그대로 실행되도록 repo root import path 보정

구현 후 검증:

```text
pytest -q
-> 97 passed

pyright --warnings
-> 0 errors, 0 warnings, 0 informations

python scripts\check_tracked_text.py --check-lf
-> Checked 112 tracked text files: OK

python scripts\live_smoke_search.py --dep 20260615 --ret 20260618 --max-results 5
-> domestic GMP->CJU results=5 source=domestic_api manual_reason=- metrics={'api_total_count': 173, 'fetched_pages': 9, 'api_item_count': 173}
-> international ICN->NRT results=5 source=international_api manual_reason=- metrics={'api_total_count': 2800, 'fetched_pages': 140, 'api_item_count': 2800}

python -m PyInstaller --clean --noconfirm FlightBot_v2.5.spec
-> dist\FlightBot_v2.5.exe 생성

dist\FlightBot_v2.5.exe
-> 6초 실행 스모크 통과
```

## 2026-05-11 DB 마이그레이션 후속 조치

사용자 테스트 중 다음 오류가 확인됐다.

```text
sqlite3.OperationalError: no such column: dedup_key
```

원인:

- 구버전 사용자 DB의 `favorites` 테이블에는 `dedup_key` 컬럼이 없을 수 있다.
- `_init_db()`가 `CREATE TABLE IF NOT EXISTS favorites (...)`를 실행해도 기존 테이블에는 새 컬럼이 추가되지 않는다.
- 그런데 `_init_db()` 내부에서 `_migrate_schema_if_needed()`보다 먼저 `idx_fav_dedup_key` 인덱스를 생성해 기존 DB에서 앱 시작이 실패했다.

수정:

- `storage/schema.py`에서 `idx_fav_dedup_key` 생성 책임을 `_migrate_schema_if_needed()` 쪽으로 단일화했다.
- 마이그레이션은 `favorites.dedup_key` 컬럼을 먼저 보강한 뒤 인덱스를 생성하고, 이후 `_backfill_favorite_dedup_keys()`가 기존 즐겨찾기 row를 채운다.
- `tests/test_config_and_database.py`에 구버전 `favorites` 테이블을 직접 만든 뒤 `FlightDatabase()` 초기화가 성공하고 인덱스까지 생성되는 회귀 테스트를 추가했다.

정합성 점검:

- `flight_bot.spec`, `FlightBot_v2.5.spec`, `FlightBot_Simple.spec`는 이미 `storage.schema`, `storage.flight_database`, `storage.db_favorites` hiddenimport를 포함한다. 이번 수정은 기존 모듈 내부 순서 변경이라 spec 추가 변경은 필요하지 않다.
- `.gitignore`는 기존 `.db`/`.db-*` ignore에 더해 `*.sqlite`, `*.sqlite3`, `*.sqlite-journal`, `*.sqlite3-journal`도 명시적으로 제외하도록 보강했다.

검증:

```text
pytest -q
-> 98 passed

pyright --warnings
-> 0 errors, 0 warnings, 0 informations

python scripts\check_tracked_text.py --check-lf
-> Checked 112 tracked text files: OK
```

## 2026-05-11 pull 이후 재점검

현재 상태:

- `git status --short --branch` -> `## main...origin/main`, 감사 문서만 untracked
- 새 HEAD: `0ef2406 Stabilize scraping diagnostics and packaging`
- 주요 추가/변경: `scraping/manual_reasons.py`, `scripts/live_smoke_search.py`, API metadata 기록, docs/spec hiddenimport 보강

재검증 결과:

```text
python scripts\check_tracked_text.py --check-lf
-> Checked 110 tracked text files: OK

pyright --warnings
-> 0 errors, 0 warnings, 0 informations

pytest -q
-> 91 passed

python scripts\live_smoke_search.py --dep 20260615 --ret 20260618 --max-results 5
-> ModuleNotFoundError: No module named 'scraper_v2'

$env:PYTHONPATH='.'; python scripts\live_smoke_search.py --dep 20260615 --ret 20260618 --max-results 5
-> domestic GMP->CJU results=5 source=domestic_scroll manual_reason=domestic_api_payload_mismatch
-> international ICN->NRT results=5 source=international_primary manual_reason=international_api_payload_mismatch
```

pull 이후 바뀐 판단:

- 기존 Critical #1은 여전히 유효하다. 실패 표시가 `BAD_REQUEST` 직접 관찰에서 `domestic_api_payload_mismatch` / `international_api_payload_mismatch`로 더 잘 드러날 뿐, 실제 결과는 여전히 DOM fallback이다.
- 기존 Low #7(API 실패 telemetry 부족)은 일부 완화됐다. `api_failure_reason`, recent API metadata, 사용자 친화 `manual_reason` label이 추가됐다.
- 새 감사 항목이 생겼다. 문서에는 `python scripts/live_smoke_search.py`를 수동 실행 명령으로 안내하지만, 현재 PowerShell에서 그대로 실행하면 repo root가 `sys.path`에 없어 실패한다.

## 실제 사이트 확인 결과

### 국제선: `ICN -> NRT`, 2026-06-15 ~ 2026-06-18

앱 실행 경로:

- URL: `https://travel.interpark.com/air/search/c:SEL-c:TYO-20260615/c:TYO-c:SEL-20260618?cabin=ECONOMY&infant=0&child=0&adult=1`
- 결과: 5건 반환, 최저가 295,400원
- 실제 결과 source: `Interpark (Auto)`, `extraction_source = international_primary`
- 검색 metrics: `dom_seen_indices`, `dom_gap_detected`만 기록됨

의미:

- 결과는 반환됐지만 API가 아니라 DOM fallback 경로다.
- 실제 네트워크에는 `/international/flights/search/v2/INTERNATIONAL::.../status`와 최종 POST API가 존재했다.
- 같은 페이지 context에서 `JSON.stringify({pageNumber:1,pageSize:20,filter:{}})`로 POST하면 `bestFares`, `contents`, `page.totalCount = 2929`가 정상 반환됐다.
- 반면 현재 `page_fetch_json()` 경로로 POST하면 `{"code":"BAD_REQUEST","message":"올바르지 않은 요청입니다."}`가 반환됐다.

### 국내선: `GMP -> CJU`, 2026-06-15 ~ 2026-06-18

앱 실행 경로:

- URL: `https://travel.interpark.com/air/search/c:SEL-c:CJU-20260615/c:CJU-c:SEL-20260618?cabin=ECONOMY&infant=0&child=0&adult=1`
- 결과: 5건 반환, 최저가 116,000원
- 실제 결과 source: `domestic_combined`
- metrics: `api_total_count = 138`, `fetched_pages = 0`
- `manual_reason = domestic_return_key_missing`

추가 네트워크 확인:

- 첫 화면에는 `DOMESTIC::...` outbound key가 있고, outbound 선택 후 실제 사이트는 return-leg용 새 `DOMESTIC::...` key를 추가로 발급한다.
- 현재 `page_fetch_json()`으로 국내선 최종 POST를 호출하면 동일하게 `BAD_REQUEST`가 반환된다.
- 동일 URL에 `JSON.stringify({pageNumber:1,pageSize:20,filter:{byCabins:["ECONOMY"]}})`로 POST하면 `items`, `page.totalCount = 177`이 정상 반환됐다.

## 주요 발견 사항

아래 항목은 수정 전 발견 근거와 권장 수정 내용이다. 실제 구현 반영 상태와 최신 live smoke 결과는 상단의 "2026-05-11 구현 완료 결과"를 기준으로 본다.

### 1. Critical - API POST body 직렬화 오류로 API-first가 실제로 동작하지 않음

관련 코드:

- `scraping/playwright_api.py:26`
- `scraping/playwright_api.py:35`
- `scraping/playwright_results.py:236`
- `scraping/playwright_domestic.py:210`

현재 `page_fetch_json()`은 body를 JS 객체로 `fetch()`에 넘긴다.

```python
body_expr = "undefined" if body is None else json.dumps(json.dumps(body, ensure_ascii=False))
...
body: {body_expr} === undefined ? undefined : JSON.parse({body_expr}),
```

브라우저 `fetch()`의 body에는 plain object가 아니라 문자열화된 JSON이 들어가야 한다. 실제 사이트에서 이 경로는 API payload mismatch를 재현했고, 같은 payload를 `JSON.stringify(...)`로 보내면 정상 응답을 받았다.

영향:

- 국제선 `_extract_international_prices_via_api()`가 실패하고 DOM fallback으로 내려간다.
- 국내선 `_extract_domestic_api_flights_data()`가 실패하고 DOM fallback으로 내려간다.
- 문서의 API pagination, API item count, API-first 안정성 계약이 실제 운영에서 보장되지 않는다.
- DOM fallback은 가상 스크롤/selector 변화에 취약하므로 날짜 범위 검색, 다중 목적지, 자동 알림 점검 안정성이 떨어진다.

권장 수정:

- `page_fetch_json()`에서 body 객체를 `JSON.stringify()`한 문자열로 전달한다.
- 응답이 `{code, message}`인 경우 호출자가 API 실패 사유를 telemetry에 남길 수 있게 최소한 `code`를 보존한다.
- 테스트는 fake `evaluate()`의 substring 검사 대신 생성된 JS가 `JSON.stringify` 또는 문자열 body를 사용하는지 검증해야 한다.

pull 이후 상태:

- `0ef2406`에서 API metadata 기록은 추가됐지만 `scraping/playwright_api.py`의 body 전달은 여전히 `JSON.parse({body_expr})`다.
- live smoke는 국내선 `domestic_scroll`, 국제선 `international_primary`를 반환했다.

### 2. High - 국제선 API fallback URL builder가 실제 사이트의 route type과 다름

관련 코드:

- `scraper_config.py:95`
- `scraper_config.py:115`
- `scraper_config.py:117`
- `scraping/playwright_results.py:63`

실제 사이트가 만든 초기 API URL:

```text
/flights/search/CITY:SEL-CITY:TYO/2026-06-15/CITY:TYO-CITY:SEL/2026-06-18
```

현재 코드의 fallback builder:

```text
/flights/search/AIRPORT:ICN-AIRPORT:NRT/2026-06-15/AIRPORT:NRT-AIRPORT:ICN/2026-06-18
```

정상 경로에서는 resource timing에서 `INTERNATIONAL::key`를 잡기 때문에 이 fallback이 자주 쓰이지 않을 수 있다. 하지만 timing entry가 비었거나 API 추출을 더 빨리 시작하도록 바꾸면 이 URL 차이가 결과 범위 불일치로 이어질 수 있다.

권장 수정:

- `build_interpark_international_api_search_url()`도 `resolve_interpark_location()` 결과를 사용한다.
- Interpark path prefix `c`/`a`를 API route type `CITY`/`AIRPORT`로 변환한다.
- `ICN/GMP -> SEL`, `NRT/HND -> TYO` 같은 문서화된 도시 코드 매핑과 API fallback이 같은 계약을 쓰도록 맞춘다.

### 3. High - 검색 패널 직접 공항 코드 입력이 이전 선택값으로 덮일 수 있음

관련 코드:

- `ui/search_panel_params.py:20`
- `ui/search_panel_params.py:21`
- `README.md` 직접 입력 설명

README는 직접 입력 시 3자리 영문 코드를 허용한다고 설명한다. 그러나 현재 helper는 `currentData()`를 먼저 읽고, 값이 있으면 `currentText()`를 보지 않는다.

오프스크린 Qt 확인 결과:

```text
initial: currentText=ICN (...), currentData=ICN
after setEditText("HND"): currentText=HND, currentData=ICN, currentIndex=0
after lineEdit().setText("KIX"): currentText=KIX, currentData=ICN, currentIndex=0
```

영향:

- 사용자가 출발지/도착지 콤보에 직접 `HND`, `KIX`, `JFK` 등을 입력해도 실제 검색은 이전 선택값으로 실행될 수 있다.
- 특히 국제선 custom airport를 빠르게 타이핑하는 사용자에게는 결과가 완전히 다른 노선으로 나올 수 있다.

권장 수정:

- editable combo에서는 line edit text를 우선 읽되, 현재 텍스트가 선택 item label과 동일할 때만 `currentData()`를 사용한다.
- `config._extract_airport_code()` 또는 동등한 public helper로 `ABC (이름)`과 `ABC`를 모두 정규화한다.
- 직접 입력 회귀 테스트를 추가한다.

### 4. Medium - API-first라기보다 DOM wait-first 흐름임

관련 코드:

- `scraping/playwright_search.py:180`
- `scraping/playwright_search.py:191`
- `scraping/playwright_search.py:211`
- `scraping/playwright_search.py:222`
- `scraping/playwright_search.py:224`
- `scraper_config.py:131`

현재 검색 흐름은 페이지 로드 후 먼저 DOM selector 후보를 순차 대기하고, 그 다음에 API 추출을 시도한다. 실제 국제선 확인에서 `li[data-index]`, `div[data-index]`, `li[class*="result"]`가 먼저 timeout 되고 마지막 가격 text selector 이후에야 추출이 시작됐다. 최종 검색은 52초가 걸렸다.

영향:

- API가 이미 준비됐어도 selector timeout만큼 대기할 수 있다.
- DOM selector 변경이 API 경로까지 지연시키므로 API-first의 안정성 장점이 줄어든다.
- 국내선 background mode는 `found_data`가 없으면 API 시도 전에 종료할 수 있다.

권장 수정:

- 국제선은 page 로드 후 `find_latest_search_key()` 또는 초기 search API를 먼저 확인하고 status/final API를 poll한다.
- 국내선도 DOM result selector가 없더라도 search key가 있으면 API page를 먼저 요청한다.
- DOM wait는 API 실패 후 fallback 진입 시점으로 늦긴다.
- selector health telemetry는 "최종 성공 selector"와 "중간 후보 timeout"을 구분해 실패율이 과장되지 않게 한다.

### 5. Medium - API 경로 테스트가 실제 fetch body 계약을 검증하지 못함

관련 코드:

- `tests/test_workers_and_scraper.py:134`
- `tests/test_workers_and_scraper.py:149`
- `tests/test_workers_and_scraper.py:265`

현재 API path 테스트는 fake page의 `evaluate(script)`에서 URL substring과 `"POST"` 포함 여부만 본다. 그래서 `fetch()` body에 plain object가 들어가는 치명적인 live-site 오류를 잡지 못했다.

권장 추가 테스트:

- `page_fetch_json()`이 `body: JSON.stringify(...)` 또는 동등한 문자열 body를 생성하는지 직접 검증한다.
- fake page가 script에서 `JSON.parse(...)` object body 패턴을 만나면 실패하도록 만든다.
- 작은 Playwright route mock을 써서 요청 본문을 실제로 읽고 JSON parse 가능 여부를 확인한다.

pull 이후 상태:

- 테스트 수는 87개에서 91개로 늘었고 API 실패 metadata 테스트도 추가됐다.
- 하지만 실제 body serialization 계약 검증은 아직 없다. 현재 `pytest -q`는 통과하지만 live smoke는 API payload mismatch로 fallback한다.

### 6. Medium - 국제선 결제 조건/혜택 정보가 결과 모델에 남지 않음

관련 코드:

- `scraping/playwright_results.py:335`
- `scraping/playwright_results.py:340`
- `scraping/playwright_results.py:344`
- `ui/export_helpers.py`

실제 국제선 페이지는 가격 옆에 `삼성카드 외 3개`, `NOL 카드 외 ...` 같은 결제 조건을 표시한다. API 응답의 `fares[].items[].promotionPrinciple.promotionName`에도 카드/프로모션 정보가 들어 있다. 하지만 현재 국제선 정규화는 `adultPrice`만 `price`로 가져오고 `benefit_label`이나 별도 결제 조건을 채우지 않는다.

영향:

- 사용자는 최저가가 특정 카드/프로모션 조건인지 알기 어렵다.
- CSV/Excel에는 혜택 컬럼이 있지만 국제선에서는 비어 있을 가능성이 높다.

권장 수정:

- 최저 `adultPrice` fare를 고른 뒤 `promotionPrinciple.promotionName`, `tags`, `avail`을 함께 저장한다.
- 기존 `benefit_label`을 재사용하거나, 국제선용 `payment_condition` 필드를 추가할지 결정한다.
- 표시/툴팁/export에서 "조건부 가격"임을 노출한다.

### 7. Low - API 실패 telemetry가 원인 추적에 부족함

관련 코드:

- `scraping/playwright_results.py:60`
- `scraping/playwright_domestic.py:143`
- `scraping/playwright_search.py:312`

실제 failure는 `BAD_REQUEST`였지만 앱 로그와 metrics만 보면 `international_primary` DOM fallback, `domestic_return_key_missing`, `fetched_pages = 0` 정도로 보인다. API가 왜 실패했는지 운영자가 바로 알기 어렵다.

권장 수정:

- API 응답 payload에 `code`/`message`가 있으면 `manual_reason` 또는 telemetry details에 `api_error_code`, `api_error_message`로 저장한다.
- `domestic_return_key_missing`은 key가 정말 없을 때만 설정하고, key는 있었지만 POST 실패인 경우 별도 사유로 분리한다.

pull 이후 상태:

- 이 항목은 일부 해결됐다.
- `scraping/manual_reasons.py`가 추가되어 raw reason code와 사용자 친화 라벨을 분리한다.
- `api_failure_reason`과 `api_recent_resources`가 metrics에 남는다.
- 다만 payload mismatch의 구체 원인인 POST body serialization까지 바로 드러나지는 않는다.

### 8. Medium - 새 live smoke 스크립트가 문서 안내대로 직접 실행되지 않음

관련 코드/문서:

- `scripts/live_smoke_search.py`
- `README.md`의 `python scripts/live_smoke_search.py` 안내
- `SCRAPING_AUDIT.md`, `claude.md`, `gemini.md`의 live smoke 수동 실행 안내

증상:

```text
python scripts\live_smoke_search.py --dep 20260615 --ret 20260618 --max-results 5
-> ModuleNotFoundError: No module named 'scraper_v2'
```

원인:

- Python은 script 파일을 직접 실행할 때 `scripts/`를 `sys.path[0]`로 잡는다.
- repo root가 import path에 없으므로 root-level facade인 `scraper_v2.py`를 찾지 못한다.

영향:

- 새 커밋이 추가한 핵심 운영 검증 도구를 문서 그대로 실행하면 실패한다.
- 릴리스 전 live smoke 습관을 만들려는 목적과 어긋난다.

권장 수정:

- 스크립트 상단에서 repo root를 `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))`로 넣는다.
- 또는 문서를 `python -m scripts.live_smoke_search` / `$env:PYTHONPATH='.'; python scripts\live_smoke_search.py` 중 하나로 통일한다.
- 초보 사용자 기준으로는 스크립트 자체에서 root path를 보정하는 쪽이 더 안전하다.

## 감사 당시 검증 결과

수정 전 로컬 정적/테스트 검증:

```text
python scripts\check_tracked_text.py --check-lf
-> Checked 110 tracked text files: OK

pyright --warnings
-> 0 errors, 0 warnings, 0 informations

pytest -q
-> 91 passed
```

수정 전 실제 사이트 검증:

```text
최초 감사: 국제선 ICN->NRT 2026-06-15/2026-06-18
-> 앱 결과 5건 반환, 하지만 extraction_source = international_primary
-> page_fetch_json POST는 BAD_REQUEST
-> JSON.stringify POST는 bestFares/contents/page 정상 반환

최초 감사: 국내선 GMP->CJU 2026-06-15/2026-06-18
-> 앱 결과 5건 반환, 하지만 API fetched_pages = 0
-> page_fetch_json POST는 BAD_REQUEST
-> JSON.stringify POST는 items/page 정상 반환

pull 이후 live smoke: 국내선 GMP->CJU 2026-06-15
-> results=5, source=domestic_scroll, manual_reason=domestic_api_payload_mismatch

pull 이후 live smoke: 국제선 ICN->NRT 2026-06-15/2026-06-18
-> results=5, source=international_primary, manual_reason=international_api_payload_mismatch
```

## 완료된 구현 항목

1. `scraping/playwright_api.py`의 POST body 직렬화를 수정했다.
2. `scripts/live_smoke_search.py`가 문서 명령 그대로 실행되도록 import path를 보정했다.
3. `build_interpark_international_api_search_url()`의 route type을 실제 사이트와 맞췄다.
4. `ui/search_panel_params.py`에서 editable combo 직접 입력을 우선 처리했다.
5. DOM wait-first 흐름을 API-first 흐름으로 재배치했다.
6. 국내선 API filter payload를 실제 사이트 계약에 맞게 최소화했다.
7. 국제선 결제 조건/혜택 label 보존과 API 실패 code/message telemetry를 보강했다.
8. 위 항목을 `pytest`, `pyright`, live smoke 2건으로 검증했다.
