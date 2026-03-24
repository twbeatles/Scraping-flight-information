# Flight Bot 기능/구현 점검 메모 (2026-03-24)

## 범위

- 내부 문서: `README.md`, `claude.md`, `SCRAPING_AUDIT.md`
- 핵심 구현: `scraping/`, `app/mainwindow/`, `ui/`, `tests/`
- 외부 기준:
  - 인터파크 항공 실페이지: `https://travel.interpark.com/air/search/...`
  - 인터파크 티켓 실페이지: `https://tickets.interpark.com/` -> `https://nol.interpark.com/ticket`

## 빠른 결론

- 가장 큰 리스크는 **국제선 추출 로직이 현재 라이브 DOM과 어긋나 primary extractor가 사실상 죽어 있고, fallback에 의존한다**는 점이다.
- 두 번째는 **설정 저장/복원 경로가 실제로 깨져 있어 국내선(`SEL -> CJU`) 복원이 실패한다**는 점이다.
- 세 번째는 **README가 말하는 “결과 행 더블클릭으로 예약 페이지 열기”가 실제로는 선택 항공편 deep link가 아니라 일반 검색 URL 재오픈**이라는 점이다.
- 인터파크 티켓은 현재 **NOL 티켓으로 리다이렉트되고 별도 사이트/구조**를 갖고 있으므로, 향후 지원이 필요하면 항공 스크래퍼와 분리된 source adapter 구조가 먼저 필요하다.

## 기준선 확인

- `python scripts/check_tracked_text.py` 실행 결과: `Checked 101 tracked text files: OK`
- `pytest -q --basetemp=.pytest_tmp` 실행 결과: `1 failed, 64 passed`
- 실패 테스트:
  - `tests/test_gui_behaviors.py:338-349`
  - `SEL -> CJU` 저장/복원이 깨져 있음
- 참고:
  - 기본 `pytest -q`는 이 환경에서 사용자 temp 디렉터리 권한 문제로 실패했다.
  - 기능 판단은 `--basetemp=.pytest_tmp` 기준이 더 유효했다.

## 우선순위 높은 이슈

### 1. 국제선 primary extractor가 현재 인터파크 DOM을 못 읽는다

관련 코드:

- `scraper_config.py:228-289`
- `scraping/playwright_results.py:51-63`

문제:

- 현재 국제선 primary extractor는 `li[data-index]` 내부에서 `span`만 읽는다.
- 시간 추출도 `span`에서 `HH:MM`만 찾고, 가격도 `span`의 `123,000원` 패턴만 찾는다.

라이브 확인:

- 2026-03-24 기준 실페이지에서 국제선 카드의 시간/가격은 `p` 태그에 들어가 있었다.
- 브라우저 점검 결과:
  - `spanTimes = []`
  - `pTimes = ["11:20 - 13:50", "13:30 - 16:15"]`
  - `spanPrices = []`
  - `pPrices = ["355,800원"]`
- 같은 페이지에서 현재 로직을 그대로 흉내 내면:
  - `primaryCount = 0`
  - `fallbackCount = 7`

영향:

- 국제선 자동 추출은 지금도 “동작은 할 수 있지만” 사실상 fallback 전용이다.
- `confidence=0.9`, `international_primary` 기준선이 문서와 달리 의미가 약하다.
- DOM이 조금만 더 바뀌면 결과 0건 또는 수동모드 전환 빈도가 급증할 수 있다.

권장 수정:

1. primary extractor를 현재 DOM 기준으로 다시 작성한다.
2. `span` 전용 가정을 버리고 `p, span, div` 조합으로 시간/가격을 읽게 한다.
3. live snapshot fixture를 추가하고, primary extractor가 실제로 결과를 뽑는 테스트를 만든다.

### 2. 국제선 fallback이 항공사명을 오염시키고, 왕복 복합 항공사를 잃어버린다

관련 코드:

- `scraper_config.py:319-383`
- 특히 `scraper_config.py:345-349`

문제:

- fallback은 `img[alt]` 중 첫 번째 항목만 보고 항공사명을 정한다.
- 현재 실페이지에는 카드 내부에 항공사 로고 외 `크로스셀링` 이미지도 섞여 있다.
- 왕복 카드에서 가는편/오는편 항공사가 다를 수 있는데, 현재 모델은 국제선에서 첫 번째 항공사만 기록한다.

라이브 확인:

- 실제 국제선 카드 예시:
  - 로고 배열 `["제주항공 로고", "파라타항공 로고"]`
  - 또는 `["크로스셀링", "제주항공 로고", "파라타항공 로고"]`
- 현재 fallback 결과 샘플 중 하나가 실제로:
  - `airline = "크로스셀링"`

영향:

- 항공사 필터링/LCC-FSC 분류가 틀릴 수 있다.
- UI 표/즐겨찾기/내보내기에서 왕복 복합 항공편 정보가 유실된다.
- 텔레메트리와 회귀 기준에서 “정상 추출”처럼 보여도 데이터 품질이 떨어진다.

권장 수정:

1. 국제선 카드에서 `img[alt$="로고"]`만 대상으로 읽도록 바꾼다.
2. 첫 번째/두 번째 항공사 로고를 각각 읽어 `airline`, `return_airline`에 저장한다.
3. 항공사명이 비항공사 텍스트(`크로스셀링`, 배너 alt 등)인 경우 버리는 방어 로직을 넣는다.

### 3. 검색 패널 설정 저장/복원이 실제로 깨져 있다

관련 코드:

- `ui/search_panel_state.py:63-92`
- `ui/search_panel_params.py:34-90`
- 실패 테스트: `tests/test_gui_behaviors.py:338-349`

문제:

- 테스트상 `SEL -> CJU` 국내선 저장 후 복원 시 `rb_domestic`가 `False`로 돌아온다.
- 실제 재현에서도 `QSettings("FlightBot", "FlightComparisonBot")`에서 저장 직후 `origin`, `dest`, `is_domestic`를 다시 읽으면 `None`이었다.

영향:

- 프로그램 재시작 후 마지막 검색/설정 복원 품질이 떨어진다.
- README/claude.md가 기대하는 `SEL` 도시코드 round-trip 보장이 깨진다.

가능성이 높은 원인:

- `ui/search_panel_state.py:65-75`의 저장 경로가 `setValue()`만 호출하고 flush/sync 보장이 약하다.
- 복원 로직은 `apply_search_params()` 자체는 괜찮아 보이므로, 저장 실패 쪽 가능성이 높다.

권장 수정:

1. `save_settings()` 후 `settings.sync()`를 명시한다.
2. 저장 직후 round-trip 테스트를 유지한다.
3. `SEL`, `GMP`, `ICN` 같은 도시/공항 혼합 케이스를 별도 회귀 테스트로 고정한다.

### 4. 더블클릭 동작이 “선택한 항공편 예약”이 아니라 “같은 검색 재오픈”이다

관련 코드:

- `README.md:139-145`
- `app/mainwindow/ui_bootstrap.py:52-84`

문제:

- README는 결과 행 더블클릭으로 예약 페이지를 연다고 설명한다.
- 실제 구현은 선택한 row의 상세 정보로 deep link를 만들지 않고, 현재 검색 조건 기반 `build_interpark_search_url()`만 다시 연다.

라이브 확인:

- 국내선은 실제 선택 후 URL이 `/air/anchor-search/domestic/...__DOMESTIC::...` 형식으로 바뀐다.
- 즉, 예약 단계에는 선택한 인벤토리/편명/가격 문맥이 들어간다.
- 현재 앱 더블클릭은 이런 정보 없이 일반 검색 URL만 연다.

영향:

- 사용자가 클릭한 항공편과 다른 정렬/광고/가격 상태로 다시 열릴 수 있다.
- “예약 페이지 열기”라는 UX 약속 대비 체감이 어긋난다.

권장 수정:

1. 결과 row에 deep-link 가능한 식별자를 저장하도록 추출 모델을 확장한다.
2. deep link가 불가능한 경우 UI 문구를 “같은 조건으로 인터파크 검색 열기”로 바꾸는 편이 정직하다.

## 중간 우선순위 이슈 / 추가 권장사항

### 5. DOM 스크래핑만으로 가는 구조는 이제 유지비가 크다

관련 근거:

- `scraper_config.py:29`
- `claude.md:895-918`

라이브 확인:

- 항공 페이지 네트워크에서 다음이 실제로 확인됐다.
  - `GET /air/air-api/inpark-air-web-api/flights/search/AIRPORT:ICN-AIRPORT:NRT/...`
  - `GET /air/air-api/inpark-air-web-api/international/flights/search/v2/{key}/status`
- 첫 응답 JSON은 `{"key": "...", "data": {...}}` 형태였다.

의미:

- 지금은 브라우저 렌더 결과를 다시 파싱하는 2차 스크래핑인데, 이미 동일 출처 JSON API가 존재한다.
- DOM 기반은 광고/배너/마케팅 이미지에 쉽게 오염된다.

권장 수정:

1. 1차 경로를 API 기반으로 바꾸고, DOM 추출은 fallback으로 내린다.
2. 텔레메트리에 `api_primary`, `dom_primary`, `dom_fallback` 같은 source type을 남긴다.
3. API 실패 시에만 수동모드/DOM fallback으로 가도록 재설계한다.

### 6. 회귀 테스트 fixture가 라이브 DOM을 못 따라간다

관련 코드:

- `tests/fixtures/interpark_sample_result.html`
- `tests/test_selector_regression.py:16-26`

문제:

- fixture는 `span` 기반의 단순 예제다.
- 현재 라이브 국제선 카드는 `p` 태그, 다중 로고, 광고/크로스셀링 요소를 포함한다.

영향:

- 테스트가 통과해도 라이브에서 primary extractor가 죽어 있는 상태를 놓친다.

권장 수정:

1. 현재 실페이지 기준 sanitized fixture를 새로 저장한다.
2. “primary extractor가 1건 이상 추출된다”를 명시적으로 검증한다.
3. “비항공사 alt는 airline으로 쓰지 않는다” 테스트를 추가한다.

### 7. 국내선 가격 기준을 명확히 정해야 한다

관련 코드:

- `scraper_config.py:143-160`
- `scraping/playwright_domestic.py:200-229`

문제:

- 현재 국내선 카드는 기본가와 카드 캐시백가를 함께 보여준다.
- 현재 로직은 첫 번째 exact price를 읽기 때문에 보통 기본가를 저장한다.

라이브 예시:

- `35,410원`
- `삼성카드 2.5% 캐시백 적용 시 34,550원`

질문 포인트:

- 제품 목표가 “누구나 결제 가능한 기본가”인지
- 아니면 “노출된 최저 체감가”인지

권장 수정:

1. 정책을 먼저 확정한다.
2. 필요하면 `base_price`, `benefit_price`, `benefit_label` 필드를 별도 저장한다.
3. 가격 알림은 어떤 기준가를 쓸지 명확히 분리한다.

### 8. 인터파크 티켓 확장을 고려한다면 지금 구조로는 바로 못 붙인다

관련 근거:

- 현재 저장소는 항공 전용 URL/모델/용어(`FlightResult`, `PlaywrightScraper`, `build_interpark_search_url`)에 강하게 묶여 있다.
- `tickets.interpark.com`은 현재 `nol.interpark.com/ticket`으로 리다이렉트된다.
- 티켓 홈은 항공과 다른 정보 구조(랭킹/오픈예정/영상/할인 섹션)와 프런트엔드 조합을 사용한다.

의미:

- “인터파크”라는 브랜드만 같고, 항공과 티켓은 같은 스크래퍼로 묶을 수 있는 수준이 아니다.

권장 수정:

1. `scraping/interpark_air/`, `scraping/interpark_ticket/`처럼 source adapter를 분리한다.
2. 공용 계층은 브라우저/리트라이/텔레메트리만 남기고, 도메인 모델은 분리한다.
3. `claude.md:895-918`의 “새 검색 소스 추가” 가이드를 실제 폴더 구조 기준으로 구체화하는 것이 좋다.

## 수정 우선순위 제안

1. 국제선 extractor를 현재 DOM 또는 API 기준으로 재작성
2. fallback airline 오염/return_airline 누락 수정
3. `SearchPanel.save_settings()` 저장 flush 보강 및 회귀 테스트 복구
4. 더블클릭 UX 문구 또는 deep-link 동작 정합화
5. 라이브 기준 fixture/test 세트 갱신
6. 이후에야 인터파크 티켓 분리 소스 설계 검토

## 문서 정합성 메모

- README의 “최대 1,000개 결과”, “예약 페이지 열기” 표현은 현재 구현/라이브 사이트 구조와 약간의 간극이 있다.
- `claude.md`의 확장 가이드는 방향은 맞지만, 실제로는 “새 source 추가”보다 먼저 “기존 Interpark Air를 DOM-only에서 API+DOM hybrid로 재설계”하는 편이 효율적이다.

## 외부 확인 링크

- 인터파크 항공 검색: <https://travel.interpark.com/air/search/a:ICN-a:NRT-20260415/a:NRT-a:ICN-20260418?adult=1&child=0&infant=0&cabin=ECONOMY>
- 인터파크 티켓 진입: <https://tickets.interpark.com/>
- 리다이렉트 후 티켓 홈: <https://nol.interpark.com/ticket>
