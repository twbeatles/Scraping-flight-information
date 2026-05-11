# Flight Bot v2.5 Scraping Audit

- 작성일: 2026-02-25
- 최종 갱신: 2026-05-11
- 대상 저장소: `Scraping-flight-information`
- 점검 범위: 스크래퍼, 워커, GUI, DB, 패키징, CI, 문서

---

## 2026-05-11 실사이트 API-first 복구 기준선

- `page_fetch_json()`은 POST body를 JS object가 아니라 JSON 문자열로 `fetch()`에 전달한다.
- 국내선 paging API 요청은 실제 사이트가 받는 최소 filter(`byCabins`)만 보낸다.
- 국제선 fallback API URL은 검색 URL과 같은 도시 매핑을 사용하며, `ICN/GMP -> CITY:SEL`, `NRT/HND -> CITY:TYO` 형태로 생성된다.
- 검색 흐름은 page load 직후 API 추출을 먼저 시도하고, 실패했을 때만 기존 DOM wait/fallback으로 내려간다.
- 검색 패널 editable 공항 콤보는 사용자가 직접 입력한 3자리 코드를 이전 `currentData()`보다 우선한다.
- 국제선 API fare의 카드/프로모션/혜택 정보는 `FlightResult.benefit_price`/`benefit_label`에 보존된다.
- `scripts/live_smoke_search.py`는 repo root를 import path에 추가하므로 문서 명령 그대로 실행된다.
- live smoke 기준:
  - `python scripts/live_smoke_search.py --dep 20260615 --ret 20260618 --max-results 5`
  - `GMP->CJU` -> `source=domestic_api`, `api_total_count=173`, `fetched_pages=9`
  - `ICN->NRT` -> `source=international_api`, `api_total_count=2800`, `fetched_pages=140`
- 로컬 품질 기준선:
  - `pyright --warnings` -> `0 errors, 0 warnings`
  - `pytest -q` -> `97 passed`
  - `python scripts/check_tracked_text.py --check-lf` -> `Checked 112 tracked text files: OK`
  - `python -m PyInstaller --clean --noconfirm FlightBot_v2.5.spec` -> `dist/FlightBot_v2.5.exe`
  - `dist/FlightBot_v2.5.exe` 6초 실행 스모크 통과

---

## 2026-05-03 기준선

- 2026-05-03 안정화 계획 반영 항목:
  - CI 정책은 기존대로 텍스트 무결성 + `pyright --warnings`를 유지하고, `pytest -q`는 PyQt/Playwright가 준비된 로컬 필수 검증으로 둔다.
  - 재현 가능한 로컬 설치를 위해 `constraints.txt`를 추가했으며, 권장 명령은 `pip install -r requirements.txt -c constraints.txt`이다.
  - 릴리스 전 외부 서비스 변화 확인용 수동 스모크 스크립트는 `python scripts/live_smoke_search.py`로 실행한다.
  - `.spec` 3종은 신규 사용자 친화 manual reason helper인 `scraping.manual_reasons`를 hiddenimport에 포함한다.
  - `.gitignore`는 build/dist/logs/db/profile/cache 산출물을 이미 커버하며, 신규 `constraints.txt`와 `scripts/live_smoke_search.py`는 추적 대상이다.
- 공개 실행 및 import 진입점은 유지된다.
  - `python gui_v2.py`
  - `from database import FlightDatabase`
  - `from scraper_v2 import FlightSearcher, PlaywrightScraper`
  - `from ui.components import ...`
  - `from ui.dialogs import ...`
  - `from ui.workers import ...`
- URL/국내선 기준선:
  - `SEL -> CJU`는 인터파크 검색 URL에서 `c:SEL-c:CJU`로 생성된다
  - 기존 `ICN/GMP -> SEL`, `NRT/HND -> TYO` 도시코드 매핑은 유지된다
  - 국내선 왕복 dedup key는 출발/도착 시간, 편명, API key, 혜택가/혜택 라벨을 포함한다
- UI/설정 기준선:
  - 공항 콤보 옵션은 `ui.airport_options` 공용 helper를 사용한다
  - 기본 검색 패널, 다중 목적지, 날짜 범위, 가격 알림은 같은 국내선/국제선 공항 목록 정책을 따른다
  - 고급 검색 다이얼로그는 국내선/국제선 라디오를 제공하되 기존 signal signature를 유지한다
- export 기준선:
  - CSV/Excel export는 `ui.export_helpers` 공용 helper를 사용한다
  - 메인 CSV, 결과 테이블 CSV/Excel, 설정 Excel export는 동일 컬럼을 쓴다
  - 공통 컬럼은 `return_airline`, `benefit_price`, `benefit_label`, `outbound_price`, `return_price`를 포함한다
- 가격 알림 기준선:
  - `AlertAutoCheckWorker`는 검색 예외와 0건 결과를 분리한다
  - 0건 결과는 `alert_no_result` signal로 전달되고 `last_error = "NO_RESULT: 검색 결과 없음"`으로 저장된다
  - 알림 목록은 `NO_RESULT` prefix를 `점검 실패`가 아니라 `결과 없음` 상태로 표시한다
  - 자동 가격 알림 설정에는 `지금 검사`와 최근/다음 점검 상태 요약이 제공된다
- 고급 검색 기록 기준선:
  - `PreferenceManager`는 `advanced_search_history`와 `add_advanced_history()`/`get_advanced_history()`를 제공한다
  - 다중 목적지 검색은 목적지별 최저가 summary를, 날짜 범위 검색은 날짜별 최저가 summary를 최대 20개까지 저장한다
  - 검색 기록 탭에서는 고급 검색 항목을 read-only 요약으로 표시한다
  - DB `search_logs`에는 다중 검색은 목적지별, 날짜 범위 검색은 날짜별 summary row를 남긴다
  - 전체 raw 결과의 앱 재시작 복원/세션 저장은 현재 범위가 아니다
- 패키징 기준선:
  - PyInstaller spec 3종은 `ui.airport_options`, `ui.export_helpers`, `scraping.manual_reasons` hiddenimport를 포함한다
  - 기존 facade 경로, package roots, split modules, `scraping.playwright_api`, `scraping.search_sources` hiddenimport를 유지한다
  - `pyinstaller --clean FlightBot_v2.5.spec` 빌드가 성공했고 산출물은 `dist/FlightBot_v2.5.exe`다
- 로컬 품질 기준선:
  - `pyright --warnings` -> `0 errors, 0 warnings`
  - `pytest -q` -> `91 passed`
  - `python scripts/check_tracked_text.py --check-lf` -> `Checked 110 tracked text files: OK`
- 저장소 운영 기준선:
  - `.gitignore`는 현재 `build/`, `dist/`, `logs/`, `playwright_profile/`, `.pytest_tmp/`, `.pre-commit-cache/`, DB/세션/로그 산출물을 커버한다
- 관측성 기준선:
  - 검색 telemetry/details에 `api_total_count`, `fetched_pages`, `api_item_count`, `dom_seen_indices`, `dom_gap_detected`, `manual_reason`, API status/ok/payload key/recent resource URL 요약을 남긴다
  - UI `manual_mode_activated`, `ui_manual_extract_finished` 이벤트도 `manual_reason`를 포함한다
  - UI에는 raw `manual_reason`과 함께 `scraping.manual_reasons.describe_manual_reason()`의 사용자 친화 라벨을 표시한다

---

## 2026-03-24 기준선

- 공개 실행 및 import 진입점은 유지된다.
  - `python gui_v2.py`
  - `from database import FlightDatabase`
  - `from scraper_v2 import FlightSearcher, PlaywrightScraper`
  - `from ui.components import ...`
  - `from ui.dialogs import ...`
  - `from ui.workers import ...`
- 국제선 기준선:
  - 국제선 추출은 동일 출처 API 우선(`flights/search -> status -> final POST {}`), 실패 시 DOM fallback 사용
  - DOM fallback은 `img[alt$="로고"]`만 항공사 후보로 사용하고 `크로스셀링` alt는 버린다
  - mixed-carrier 왕복은 `airline`, `return_airline`을 모두 채운다
- 국내선 가격 기준선:
  - `FlightResult`는 `benefit_price`, `benefit_label`을 포함한다
  - canonical `price`는 계속 기본가이며, 혜택가는 툴팁/CSV/Excel에 노출한다
- 내부 구조 기준선:
  - `scraping.search_sources`가 내부 source boundary를 제공한다
  - 기본 런타임 source는 `InterparkAirSource`
  - `InterparkTicketSource`는 skeleton adapter만 제공한다
- 로컬 품질 기준선:
  - `pyright --warnings` -> `0 errors, 0 warnings`
  - `pytest -q --basetemp=.pytest_tmp` -> `72 passed`
  - `python scripts/check_tracked_text.py --check-lf` -> `Checked 101 tracked text files: OK`
- GitHub Actions `Quality` 워크플로 기준선:
  - tracked text integrity check는 `--check-lf`와 BOM 검사를 포함한다
  - `pyright --warnings` 실행
  - `pytest`는 실행하지 않음
- 저장소 운영 기준선:
  - `.pre-commit-config.yaml`로 로컬 훅에서 `check_tracked_text.py --check-lf`와 `pyright --warnings`를 실행할 수 있다
  - `.gitignore`는 `.pytest_tmp/`, `.pre-commit-cache/`를 포함해 현재 운영 산출물을 커버한다

## 2026-03-19 기준선

- 공개 실행 및 import 진입점은 유지된다.
  - `python gui_v2.py`
  - `from database import FlightDatabase`
  - `from scraper_v2 import FlightSearcher, PlaywrightScraper`
  - `from ui.components import ...`
  - `from ui.dialogs import ...`
  - `from ui.workers import ...`
- 로컬 품질 기준선:
  - `pyright` -> `0 errors`
  - `pytest -q` -> `65 passed`
  - `python scripts/check_tracked_text.py` -> tracked text check passed
- 검색 파라미터 기준선:
  - 저장/복원 공용 스키마는 `origin`, `dest`, `dep`, `ret`, `adults`, `cabin_class`, `is_domestic`
  - `user_preferences.json`과 세션 JSON 루트는 `schema_version = 2`
  - 구버전 payload에서 `is_domestic`가 없으면 국내선 코드 기준으로 추론해 정규화한다
- 가격 알림 기준선:
  - `price_alerts`는 `adults`, `last_error`를 포함한다
  - 자동 알림 실패는 모달 없이 DB 상태 + 로그에 기록한다
- GitHub Actions `Quality` 워크플로 기준선:
  - tracked text integrity check 실행
  - `pyright` 실행
  - `pytest`는 실행하지 않음

## CI 판단 근거

- GitHub hosted Ubuntu runner에서 PyQt bootstrap 시 `libEGL.so.1`가 없어 `tests/conftest.py` import 단계가 실패했다.
- 그래서 현재 저장소 기준은 다음과 같이 분리한다.
  - GitHub Actions: 텍스트 무결성 + 정적 타입 검사
  - 로컬 개발 환경: `pytest -q` 포함 전체 확인
- `tests/conftest.py`는 PyQt import 실패 시 GUI 의존 테스트만 수집 단계에서 건너뛰도록 완화되었다.

## PyInstaller 점검 결과

- 점검 대상:
  - `flight_bot.spec`
  - `FlightBot_v2.5.spec`
  - `FlightBot_Simple.spec`
- 세 파일 모두 다음 기준으로 동기화했다.
  - facade 경로 유지:
    - `database`
    - `scraper_v2`
    - `ui.components`
    - `ui.dialogs`
    - `ui.styles`
    - `ui.workers`
  - 패키지 루트 명시:
    - `app`
    - `app.mainwindow`
    - `scraping`
    - `storage`
  - 분리 모듈 포함:
    - `app.mainwindow.ui_bootstrap_sections`
    - `scraping.playwright_*`
    - `scraping.playwright_api`
    - `scraping.search_sources`
  - `ui.search_panel_*`
  - `ui.search_panel_params`
  - `ui.airport_options`
  - `ui.export_helpers`
  - `ui.dialogs_search_*`
  - `ui.dialogs_tools_*`
  - `ui.styles_dark`
    - `ui.styles_light`

## 문서 정합성 요약

- `README.md`, `claude.md`, `gemini.md`는 모두 다음 최신 기준으로 맞춘다.
  - GitHub Actions에서는 `pytest`를 돌리지 않는다.
  - `pytest -q`는 로컬 검증 기준이다.
  - `.spec` 파일은 facade + split modules + package roots + `ui.search_panel_params` 기준으로 유지된다.
  - 2026-04-09부터는 `scraping.playwright_api`, `scraping.search_sources` hiddenimport도 포함한다.
  - 2026-04-29부터는 `ui.airport_options`, `ui.export_helpers` hiddenimport도 포함한다.
  - 검색 파라미터 저장/복원은 `schema_version = 2`와 공용 정규화 규약을 기준으로 설명한다.
  - 가격 알림 문서는 성인 수/좌석 등급 매칭, `점검 실패`, `결과 없음` 상태를 반영한다.
  - 고급 검색 문서는 요약 히스토리 저장과 raw 결과 복원 제외 범위를 반영한다.
  - `.gitignore`는 `.pytest_tmp/`, `.pre-commit-cache/`, `build/`, `dist/`, `playwright_profile/`, `logs/`를 포함해 현재 산출물을 커버한다.

## 남아 있는 운영 메모

- GitHub에서 GUI 테스트가 빠지므로, PyQt/Playwright 환경이 준비된 로컬 머신에서 `pytest -q`를 실행하는 습관이 중요하다.
- 향후 GitHub에서 테스트를 다시 활성화하려면 두 가지 중 하나가 필요하다.
  - Ubuntu runner에 Qt/OpenGL 시스템 라이브러리 설치
  - GUI 의존 테스트와 비의존 테스트를 워크플로 단계에서 분리
