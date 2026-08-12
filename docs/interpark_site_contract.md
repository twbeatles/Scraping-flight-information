# Interpark Air Site Contract

- 기준일: 2026-08-12
- 소스: 코드 계약(`scraping/interpark/adapter.py`, `scraping/interpark/contract/*`) + 기존 live smoke 기준선
- 라이브 probe (2026-08-12 로컬):
  - probe 초기화 버그 수정 후 재실행 성공
  - GMP→CJU 국내: page loaded, search_key=yes (`network_url`), selectors 1/3 (가격 regex OK)
  - ICN→NRT 국제: page loaded, search_key=yes (`network_url`), selectors 1/4 (가격 regex OK; `data-index`는 짧은 wait에서 MISS — API 키는 확보됨)
  - 네트워크/사이트 상태 변동이 있으므로 릴리스 전 `live_selector_probe` / `live_smoke_search`를 재실행한다.

## Surface (검색 페이지)

| 항목 | 계약 |
| --- | --- |
| Origin | `https://travel.interpark.com` |
| Search URL base | `https://travel.interpark.com/air/search` |
| Location prefix | **국내:** 공항 `a:GMP`/`a:ICN` (도시 접기 안 함, `SEL`만 `c:SEL`). **국제:** `CITY_CODES_MAP` (`ICN→SEL`) |
| Date (path) | `YYYYMMDD` |
| Query | `cabin`, `adult`, `child`, `infant` |

예:

```text
https://travel.interpark.com/air/search/a:GMP-a:CJU-20260911?cabin=ECONOMY&infant=0&child=0&adult=1
https://travel.interpark.com/air/search/c:SEL-c:TYO-20260911/c:TYO-c:SEL-20260918?cabin=ECONOMY&adult=1
```

코드: `build_interpark_search_url()` (`scraping/interpark/urls.py`)

## API base

```text
https://travel.interpark.com/air/air-api/inpark-air-web-api
```

호출 방식: Playwright page context `fetch(..., credentials: 'include')` (same-origin session).

## Endpoints

| 용도 | Method | Path |
| --- | --- | --- |
| 국제 초기 검색(키 발급) | GET | `/flights/search/{CITY\|AIRPORT:...}/{YYYY-MM-DD}/...` |
| 국제 status | GET | `/international/flights/search/v2/{INTERNATIONAL::key}/status` |
| 국제 결과 | POST | `/international/flights/search/v2/{INTERNATIONAL::key}` |
| 국내 결과 | POST | `/domestic/flights/search/{DOMESTIC::key}` |

버전 상수: `INTERPARK_INTERNATIONAL_API_VERSION = "v2"` (`runtime.py`)

### Search key

| Trip | Prefix | Payload fields |
| --- | --- | --- |
| domestic | `DOMESTIC::` | `key`, `searchKey`, `search_key` |
| international | `INTERNATIONAL::` | 동일 |

키 획득 순서:

1. network listener (URL 또는 JSON)
2. performance resource timing
3. 국제선만: initial GET bootstrap

국내선은 현재 **페이지 네트워크 트래픽에 의존** (initial bootstrap 미구현 → 후속 Phase 2).

### Request body

국내 결과 POST:

```json
{
  "pageNumber": 1,
  "pageSize": 20,
  "filter": { "byCabins": ["ECONOMY"] }
}
```

국제 결과 POST:

```json
{
  "pageNumber": 1,
  "pageSize": 20,
  "filter": {}
}
```

### Response shape (앱이 읽는 필드)

공통 page meta:

- `page.totalCount`
- `page.pageSize`
- `page.currentPage` (국제)
- `page.pageNumber` (요청 필드명)

국내 items:

- bucket: `items[]`
- `schedule.departureAt`, `schedule.arrivalAt`, `schedule.marketingCarrier`, `schedule.flightNumber`
- `fares[].totalPrice`, `fares[].benefits[].discountedPrice` / `cardCashback`

국제 items:

- buckets: `bestFares[]`, `contents[]`
- `schedules[]` + fare 필드 다형 매핑 (`adultPrice`/`totalPrice`/…)
- status payload: `status == "COMPLETE"`, 오류 시 `code`

## DOM wait selectors

국내:

- `button:has-text("원")`
- `text=/\d{1,3}(,\d{3})+\s*원/`
- `button:has-text("직항")`

국제:

- `li[data-index]`, `div[data-index]`
- `li[class*="result"]`
- 가격 regex

## Runtime caps

| 상수 | 기본값 |
| --- | --- |
| `DOMESTIC_API_MAX_PAGES` | 30 |
| `INTERNATIONAL_API_MAX_PAGES` | 50 |
| `INTERNATIONAL_STATUS_MAX_POLLS` | 60 |

## 코드에서 수정할 위치 (우선순위)

사이트 변경 시 아래 순서:

1. `scraping/interpark/adapter.py` — base/path/version + schema fields
2. `scraping/interpark/contract/schemas.py` — 필드명/버킷
3. `scraping/interpark/contract/carriers.py` — 항공사 맵
4. `scraping/interpark/urls.py` — URL builder
5. `scraping/interpark/selectors.py` / `scripts/*` — DOM
6. `scraping/domestic/*`, `scraping/international/*` — 정규화 로직만

## 키 대기 / 왕복

| 항목 | 계약 |
| --- | --- |
| Search key wait | `SEARCH_KEY_WAIT_TIMEOUT_SECONDS` (기본 12s), poll `SEARCH_KEY_WAIT_POLL_MS` |
| Return key wait | `SEARCH_KEY_RETURN_WAIT_TIMEOUT_SECONDS` (기본 10s), outbound key exclude |
| Round-trip click candidates | `DOMESTIC_ROUND_TRIP_CLICK_CANDIDATES` (기본 5) |

실패 reason:

- `domestic_api_key_missing` / `domestic_api_key_timeout`
- `domestic_api_key_expired` (`INVALID_CACHE_SEARCH_KEY` — 1회 키 재확보 후 재시도)
- `domestic_return_key_missing` (DOM fallback 가능)

DOM wait (2026-08 live):

- 국내 우선: `button:has-text("원")`, 가격 regex (`직항` 버튼 wait 제거)
- 국제 우선: `li[data-index]`, 가격 regex

## 검증

```powershell
python -m pytest -q
python scripts\live_selector_probe.py --require-search-key --check-api-shape
python scripts\live_smoke_search.py --max-results 5 --fail-on-cap --max-domestic-pages 30 --max-international-pages 50
```
