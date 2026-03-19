# Flight Bot v2.5 Scraping Audit

- 작성일: 2026-02-25
- 최종 갱신: 2026-03-19
- 대상 저장소: `Scraping-flight-information`
- 점검 범위: 스크래퍼, 워커, GUI, DB, 패키징, CI, 문서

---

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
    - `ui.search_panel_*`
    - `ui.search_panel_params`
    - `ui.dialogs_search_*`
    - `ui.dialogs_tools_*`
    - `ui.styles_dark`
    - `ui.styles_light`

## 문서 정합성 요약

- `README.md`, `claude.md`, `gemini.md`는 모두 다음 최신 기준으로 맞춘다.
  - GitHub Actions에서는 `pytest`를 돌리지 않는다.
  - `pytest -q`는 로컬 검증 기준이다.
  - `.spec` 파일은 facade + split modules + package roots + `ui.search_panel_params` 기준으로 유지된다.
  - 검색 파라미터 저장/복원은 `schema_version = 2`와 공용 정규화 규약을 기준으로 설명한다.
  - 가격 알림 문서는 성인 수/좌석 등급 매칭과 `점검 실패` 상태를 반영한다.
  - `.gitignore`는 현 상태에서 추가 규칙 없이도 주요 산출물을 커버한다.

## 남아 있는 운영 메모

- GitHub에서 GUI 테스트가 빠지므로, PyQt/Playwright 환경이 준비된 로컬 머신에서 `pytest -q`를 실행하는 습관이 중요하다.
- 향후 GitHub에서 테스트를 다시 활성화하려면 두 가지 중 하나가 필요하다.
  - Ubuntu runner에 Qt/OpenGL 시스템 라이브러리 설치
  - GUI 의존 테스트와 비의존 테스트를 워크플로 단계에서 분리
