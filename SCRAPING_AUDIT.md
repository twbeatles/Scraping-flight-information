# Flight Bot v2.5 항공권 스크래핑 기능 감사 보고서

- 작성일: 2026-02-25
- 최종 갱신: 2026-03-15
- 대상 저장소: `Scraping-flight-information`
- 점검 범위: 스크래퍼, 워커, GUI, DB, 설정/세션/알림, 테스트
- 근거 문서: `README.md`, `claude.md`, `gemini.md`
- 근거 코드: `scraper_v2.py`, `scraper_config.py`, `app/mainwindow/*`, `scraping/playwright_*.py`, `ui/components_search_panel.py`, `ui/search_panel_*.py`, `ui/dialogs_search.py`, `ui/dialogs_tools.py`, `ui/styles.py`, `tests/*`
- 실행 확인: `pytest -q` 통과 (56 passed)

---

## Refresh (2026-03-15)

- 현재 감사 기준선은 2026-03-15 품질/패키징 점검까지 반영한 구조다.
- 정적 품질 기준:
  - `pyrightconfig.json`: Python `3.10`, `typeCheckingMode=standard`
  - `pyright`: `0 errors`
  - `pytest -q`: `56 passed`
  - `python scripts/check_tracked_text.py`: `Checked 97 tracked text files: OK`
- 타입 계약 보강 대상:
  - `scraping/playwright_scraper.py`, `scraping/playwright_browser.py`, `scraping/playwright_search.py`
  - `ui/search_panel_shared.py`, `ui/search_panel_build.py`, `ui/search_panel_actions.py`, `ui/search_panel_state.py`, `ui/search_panel_widget.py`
  - `app/main_window.py`
- 패키징 기준 재확인:
  - `flight_bot.spec`
  - `FlightBot_v2.5.spec`
  - `FlightBot_Simple.spec`
  - 위 세 파일은 facade + split-module hiddenimports에 더해 `ui.styles` facade도 명시적으로 포함한다.
- 텍스트/인코딩 가드레일:
  - `.gitattributes`
  - `scripts/check_tracked_text.py`
  - `.github/workflows/quality.yml`
- `.gitignore`는 새 품질 도구 기준으로 재확인했고 추가 ignore 규칙은 필요하지 않았다.

## Refresh (2026-03-14)

- 현재 감사 기준선은 2026-03-14 리팩토링 이후 구조다.
- 외부 공개 경로는 유지한다:
  - `gui_v2.py`
  - `scraper_v2.py`
  - `database.py`
  - `ui.components`
  - `ui.dialogs`
  - `ui.workers`
- 내부 구현은 다음 모듈 묶음으로 분리되었다:
  - `scraping/playwright_browser.py`, `scraping/playwright_search.py`, `scraping/playwright_domestic.py`, `scraping/playwright_results.py`
  - `app/mainwindow/ui_bootstrap_sections.py`
  - `ui/search_panel_*.py`
  - `ui/dialogs_search_*.py`
  - `ui/dialogs_tools_*.py`
  - `ui/styles_dark.py`, `ui/styles_light.py`
- 패키징 기준도 함께 갱신되었다:
  - `flight_bot.spec`
  - `FlightBot_v2.5.spec`
  - `FlightBot_Simple.spec`
  - 위 세 파일은 facade + second-stage split hiddenimports를 모두 포함한다.
- 리팩토링 시작 백업:
  - `backups/code_snapshot_20260314_231358.zip`

> 아래 0장 이후의 리스크/라인 근거는 원래 감사 로그를 보존한 것이다. 최신 구조를 읽을 때는 이 Refresh 섹션과 2026-03-14 문서 업데이트를 우선 기준으로 본다.

---

## 0. 구현 반영 현황 (2026-02-26)

본 문서는 원래 리스크 감사 문서이며, 아래 B01~B11 개선안은 현재 코드에 반영 완료된 상태다.

| 항목 | 구현 상태 | 핵심 반영 파일 |
|---|---|---|
| B01 재시도/백오프 | 완료 | `scraper_v2.py`, `scraper_config.py` |
| B02 terminate 제거 | 완료 | `gui_v2.py` |
| B03 DB 연결 수명 관리 | 완료 | `database.py`, `gui_v2.py` |
| B04 국내선 판별 중앙화 | 완료 | `config.py`, `scraper_v2.py`, `ui/components.py` |
| B05 좌석등급 전파 통일 | 완료 | `ui/dialogs.py`, `ui/workers.py`, `gui_v2.py` |
| B06 selector 강건화/health | 완료 | `scraper_config.py`, `scraper_v2.py`, `database.py` |
| B07 자동 가격 알림 점검 | 완료 | `config.py`, `gui_v2.py`, `ui/workers.py`, `ui/dialogs.py` |
| B08 관측성(JSONL+DB 요약) | 완료 | `database.py`, `gui_v2.py`, `ui/dialogs.py` |
| B09 문서 정합성 | 완료 | `README.md`, `claude.md`, `gemini.md` |
| B10 FlightResult 메타 확장 | 완료 | `scraper_v2.py`, `database.py`, `gui_v2.py` |
| B11 진단 UI/selector health | 완료 | `ui/dialogs.py`, `database.py` |
| B12 백그라운드 실행 분리/재시도 루프 안정화 | 완료 | `scraper_v2.py`, `ui/workers.py`, `tests/test_workers_and_scraper.py` |

> 참고: 아래 3장 리스크 목록은 감사 기준선(개선 전 위험 정의)으로 유지하며, 현재 코드는 0장 상태표를 기준으로 해석한다.

---

## 1. 문서 목적, 범위, 평가 기준

### 1.1 목적
이 문서는 항공권 가격 스크래핑 프로그램의 기능 구현 관점에서 잠재 리스크와 보완/추가가 필요한 항목을 식별하고, 즉시 실행 가능한 우선순위 백로그와 로드맵을 제공한다.

### 1.2 범위
- 포함:
  - 인터파크 스크래핑 자동/수동 모드
  - 단일/다중/날짜범위 검색 워커
  - GUI 취소/오류/알림/세션 흐름
  - DB 연결/캐시/저장 복원
  - 테스트 커버리지와 운영 관측성
- 제외:
  - 법률/약관 적합성의 법률 자문
  - 실제 인터파크 운영 환경 부하 테스트(온라인 실측)

### 1.3 심각도 정의
- `P0`: 서비스 핵심 기능 마비 또는 대규모 오동작을 즉시 유발
- `P1`: 기능 정확도/안정성에 중대한 영향, 단기간 내 해결 필요
- `P2`: 운영 효율/신뢰도 저하, 중기적으로 해결 필요
- `P3`: 문서/사용성/유지보수성 개선 권고

### 1.4 실행 우선순위 정의
- `즉시(1주)`: P0/P1 중심 차단 이슈
- `단기(1~4주)`: 정확도/자동화/운영 편의 개선
- `중기(4주+)`: 확장성/관측성/지속 개선 체계화

---

## 2. 현재 구현 스냅샷 (README/claude 대비 실제 구현 매핑)

| 영역 | 문서상 의도 | 현재 구현 확인 | 상태 |
|---|---|---|---|
| 브라우저 폴백 | Chrome → Edge → Chromium | `scraper_v2.py` `_init_browser()`에서 순차 시도 구현 | 일치 |
| 수동 모드 | 자동 추출 실패 시 브라우저 유지 | `manual_mode=True` 전환 및 GUI 수동 추출/닫기 제공 | 일치 |
| 멀티/날짜 검색 | 병렬 검색 제공 | `ui/workers.py`에서 `ThreadPoolExecutor(max_workers=2)` | 일치 |
| 좌석등급 필터 | 이코노미/비즈니스/일등석 지원 | 단일/다중/날짜 검색 전체에서 `cabin_class` 전달 반영 | 일치 |
| 가격 알림 | 목표가 도달 알림 | 수동 검색 체크 + 앱 실행 중 QTimer 주기 점검(옵션) 반영 | 일치 |
| 설정 파일 경로 | README 표기와 구현 일치 | `user_preferences.json` 기준으로 정합화 | 일치 |

---

## 3. 잠재 문제 목록 (P0~P3)

> 주의: 아래 리스크의 코드 라인 근거는 감사 시점 기준 스냅샷이며, 최신 코드에서는 일부 라인 번호가 달라질 수 있다.

### 3.1 리스크 #1: 재시도 로직 미구현
- 심각도/우선순위: `P1 / 즉시`
- 증상:
  - 일시적 네트워크/DOM 로딩 실패 시 단발성 실패로 수동 모드 전환 확률 증가
- 재현 조건:
  - 간헐적 타임아웃 또는 일시적 페이지 지연 환경
- 코드 근거:
  - `scraper_config.py:9-10` (`MAX_RETRY_COUNT`, `RETRY_DELAY_SECONDS` 선언)
  - `scraper_v2.py` 검색 경로에서 해당 상수 사용처 부재
- 영향:
  - 자동 추출 성공률 하락, 사용자 체감 안정성 저하
- 권고 조치:
  - `FlightSearcher` 또는 `PlaywrightScraper.search()`에 재시도/백오프 루프 명시 구현
  - 예외 타입별 재시도 가능/불가 정책 분리 (`NetworkError` 재시도, `DataExtractionError` 제한적 재시도)

### 3.2 리스크 #2: 국내선 판별 하드코딩 협소
- 심각도/우선순위: `P1 / 즉시`
- 증상:
  - 국내 노선인데 국제선 로직으로 진입하거나 그 반대가 될 가능성
- 재현 조건:
  - 국내 공항 코드가 하드코딩 집합에 누락된 경우
- 코드 근거:
  - `scraper_v2.py:378-380` (`domestic_airports` 하드코딩)
- 영향:
  - 국내선 왕복 조합 로직 미적용, 결과 정확도/수집량 저하
- 권고 조치:
  - 국내선 코드 소스를 `config.py`로 중앙화하고 단일 기준으로 참조
  - 회귀 테스트에서 국내선 판별 케이스 추가

### 3.3 리스크 #3: 고정 셀렉터/정규식 의존
- 심각도/우선순위: `P0 / 즉시`
- 증상:
  - 사이트 DOM 변경 시 추출 전면 실패 또는 결과 누락
- 재현 조건:
  - 클래스/태그 구조 변경, 텍스트 포맷 변경
- 코드 근거:
  - `scraper_config.py:28-29` (`REGEX_TIME`, `REGEX_PRICE`)
  - `scraper_config.py:161`, `scraper_config.py:320` (고정 추출/스크롤 스크립트)
  - `scraper_v2.py:213-236` (`_wait_for_results`의 고정 selector)
- 영향:
  - 핵심 기능(가격 추출) 중단
- 권고 조치:
  - 다중 selector 전략(우선순위 체인) + DOM 버전 감지
  - 추출 실패 시 selector 진단 로그 및 헬스체크 결과 기록

### 3.4 리스크 #4: 다중/날짜 검색 좌석등급 미반영
- 심각도/우선순위: `P1 / 즉시`
- 증상:
  - 단일 검색과 달리 멀티/날짜검색 결과가 기본 좌석등급으로 검색되어 일관성 붕괴
- 재현 조건:
  - 사용자가 비즈니스/일등석 기대 상태로 멀티/날짜검색 수행
- 코드 근거:
  - `ui/workers.py:160`, `ui/workers.py:289` (`searcher.search(...)` 호출 시 `cabin_class` 미전달)
  - 반면 단일 검색은 `ui/workers.py:60`에서 전달됨
- 영향:
  - 기능 신뢰도 하락, 비교 결과 왜곡
- 권고 조치:
  - 멀티/날짜검색 시그니처에 `cabin_class` 추가 후 UI~Worker~Searcher 경로 통일

### 3.5 리스크 #5: 워커 강제 종료(`terminate`) fallback
- 심각도/우선순위: `P1 / 즉시`
- 증상:
  - 강제 종료 시 리소스 정리 불완전, 간헐적 크래시/잠금 가능성
- 재현 조건:
  - 취소 시 워커가 지정 시간 내 정상 종료하지 못할 때
- 코드 근거:
  - `gui_v2.py:550`, `gui_v2.py:1491` (`worker.terminate()`)
- 영향:
  - Playwright/스레드/DB 상태 불안정 위험
- 권고 조치:
  - cooperative cancel 강화 + terminate 사용 최소화
  - 종료 단계별 타임아웃/로그 표준화

### 3.6 리스크 #6: DB 연결 수명 관리 API 부재
- 심각도/우선순위: `P1 / 단기`
- 증상:
  - 장기 실행/종료 시 파일 잠금 유지 가능성(특히 Windows)
- 재현 조건:
  - thread-local connection 누적 후 명시적 close 없이 종료/파일 작업
- 코드 근거:
  - `database.py:67` (`FlightDatabase` 시작)
  - `database.py` 내 `def close...` 계열 API 부재
- 영향:
  - 유지보수/백업/테스트 시 파일 핸들 충돌 리스크
- 권고 조치:
  - `close_all_connections()` 또는 `close()` 제공
  - 앱 종료 훅에서 명시 호출

### 3.7 리스크 #7: 문서-구현 설정 파일명 불일치
- 심각도/우선순위: `P3 / 단기`
- 증상:
  - 사용자/운영자가 잘못된 파일명으로 설정 백업/문제 해결 시도
- 재현 조건:
  - README 기준으로 수동 설정 파일 확인 시
- 코드 근거:
  - `README.md:290`, `README.md:292` (`preferences.json`)
  - `config.py:83`, `config.py:86` (`user_preferences.json`)
- 영향:
  - 운영 혼란, 지원 비용 증가
- 권고 조치:
  - README 경로/파일명 즉시 정정

### 3.8 리스크 #8: 가격 알림 주기 감시 미구현
- 심각도/우선순위: `P2 / 단기`
- 증상:
  - 검색을 직접 실행하지 않으면 알림이 업데이트/발동되지 않음
- 재현 조건:
  - 사용자가 자동 감시를 기대하지만 수동 검색 미실행
- 코드 근거:
  - `gui_v2.py:972` (검색 완료 시 `_check_price_alerts()` 호출)
  - `gui_v2.py:984` (`_check_price_alerts` 정의)
  - `gui_v2.py`에 알림 전용 주기 스케줄러 부재
- 영향:
  - 알림 기능의 실효성 제한
- 권고 조치:
  - 백그라운드 스케줄러(간격/대상 노선 제한) 설계 및 사용자 on/off 제공

### 3.9 리스크 #9: DOM 회귀 감지 테스트 부재
- 심각도/우선순위: `P1 / 단기`
- 증상:
  - 사이트 구조 변경을 사전 감지하지 못하고 런타임에서만 장애 인지
- 재현 조건:
  - 인터파크 DOM 변경
- 코드 근거:
  - `tests/test_workers_and_scraper.py:47` (`_FakePage` 기반 단위 테스트)
  - `tests/test_workers_and_scraper.py:150` (`FlightSearcher` monkeypatch)
  - 실제 Playwright DOM 통합 회귀 테스트 없음
- 영향:
  - 변경 탐지 지연, 장애 대응 시간 증가
- 권고 조치:
  - 샘플 HTML fixture 기반 selector 회귀 테스트 + smoke E2E 추가

### 3.10 리스크 #10: 운영 관측성(Observability) 부족
- 심각도/우선순위: `P1 / 단기`
- 증상:
  - 실패율/원인/성공률 추적이 어렵고 장애 분석 시간이 길어짐
- 재현 조건:
  - 실제 운영에서 간헐 실패, 추출 누락 발생 시
- 코드 근거:
  - `gui_v2.py:1514-1517` (`logging.basicConfig` + stdout handler 중심)
  - 구조화 로그/메트릭 저장/헬스체크 리포트 부재
- 영향:
  - 운영 대응 지연, 개선 우선순위 판단 어려움
- 권고 조치:
  - JSON 로그, 실패 코드 분류, selector 헬스 점수, 성공률 지표 도입

---

## 4. 추가해야 할 기능 백로그 (안정성/정확도/운영성/확장성)

### 4.1 안정성
- `B01` 재시도/백오프 정책 구현 (`P1`, 즉시)
- `B02` cooperative cancel 강화 및 `terminate` 의존 축소 (`P1`, 즉시)
- `B03` DB 연결 종료 API 추가 (`P1`, 단기)

### 4.2 정확도
- `B04` 국내선 판별 기준 중앙화 (`P1`, 즉시)
- `B05` 다중/날짜검색 `cabin_class` 전달 경로 통일 (`P1`, 즉시)
- `B06` selector 다중화 + fallback 계층 강화 (`P0`, 즉시)

### 4.3 운영성
- `B07` 가격 알림 주기 감시 스케줄러 (`P2`, 단기)
- `B08` 구조화 파일 로그 + 지표 수집 (`P1`, 단기)
- `B09` README/운영 문서 정합화 (`P3`, 단기)

### 4.4 확장성
- `B10` 스크래핑 결과 메타 확장 (`confidence`, `extraction_source`) (`P2`, 중기)
- `B11` 소스별 추출기 상태 진단 인터페이스 (`P2`, 중기)

### 4.5 중요한 API/인터페이스 변경 제안
1. `FlightSearcher.search(...)`:
   - 멀티/날짜검색 경로에서도 `cabin_class`를 반드시 전달하도록 인터페이스 통일
2. `FlightDatabase`:
   - `close_all_connections()` 또는 `close()` API 추가
3. `FlightResult`:
   - `confidence: float`, `extraction_source: str` 필드 확장 제안
4. 가격 알림:
   - 자동 점검 잡 진입점(예: `run_price_alert_check_once()`) 인터페이스 추가

---

## 5. 실행 로드맵 (즉시 1주 / 단기 1~4주 / 중기 4주+)

### 5.1 즉시(1주)
- `P0/P1` 차단 이슈 우선:
  - selector/정규식 회귀 방어 강화
  - 멀티/날짜검색 `cabin_class` 전달 누락 수정
  - 재시도/백오프 도입
  - `terminate` fallback 축소 설계 반영
- 산출물:
  - 코드 수정 + 단위 테스트 + 회귀 테스트 추가

### 5.2 단기(1~4주)
- 운영 안정화:
  - DB close API + 종료 훅 반영
  - 가격 알림 자동 점검(옵션형) 도입
  - 구조화 로그 및 실패 코드 분류
  - README 설정 파일명/운영 가이드 정정
- 산출물:
  - 운영 가이드 업데이트 + 관측 대시보드 초안(간단 지표)

### 5.3 중기(4주+)
- 확장/지속 개선:
  - 스크래핑 결과 신뢰도 메타 확장
  - selector 헬스체크 자동화 및 정기 리포트
  - 소스 확장 시 공통 추상화 레이어 정리
- 산출물:
  - 확장 설계 문서 + 점진적 마이그레이션

---

## 6. 테스트 강화 계획 (단위/통합/E2E)

### 6.1 필수 테스트 케이스
1. 국제선/국내선 DOM 변경 회귀 테스트
2. 타임아웃 + 재시도/백오프 동작 테스트
3. 다중/날짜검색 좌석등급 반영 테스트
4. 취소 시나리오(`Esc`, 종료 타임아웃, 리소스 정리) 테스트
5. DB 연결 종료 후 파일 잠금 해소 테스트(Windows)
6. 가격 알림 매칭(왕복/편도/날짜 불일치) 테스트
7. 세션 저장/복원 경계값(1000건) + 스키마 호환 테스트
8. 1000+ 결과 렌더링 성능 회귀 테스트

### 6.2 권장 테스트 계층
- 단위:
  - 파라미터 전달/분기/예외 처리
- 통합:
  - 스크래퍼 + 워커 + DB 연동(모의 페이지/fixture 기반)
- E2E 스모크:
  - 제한된 시나리오로 실제 Playwright 흐름 검증

### 6.3 합격 기준 예시
- 재시도 적용 후 일시적 실패 시 자동 회복률 개선
- 멀티/날짜검색에서 선택 좌석등급이 URL/결과에 반영
- 앱 종료 시 DB 파일 잠금 미발생
- selector 변경 시 테스트 단계에서 실패 감지

---

## 7. 완료 기준 (Definition of Done)

다음 조건을 모두 만족하면 본 감사 항목의 1차 조치를 완료한 것으로 본다.

1. `P0/P1` 항목 대응 PR 머지 완료
2. 멀티/날짜검색 `cabin_class` 일관성 보장 및 테스트 통과
3. 재시도/백오프 정책이 코드/로그에 명시되고 테스트로 검증됨
4. DB 연결 종료 API 도입 및 종료 경로에서 호출됨
5. 가격 알림 자동점검 모드(최소 opt-in) 제공
6. 구조화 로그/핵심 지표(추출 성공률, 실패 코드, 수동모드 전환률) 수집 가능
7. README와 실제 동작(설정 파일명/경로) 정합성 일치
8. 테스트 스위트에 DOM 회귀 감지 케이스가 포함됨

---

## 부록 A. 확인된 주요 근거 위치

- 재시도 상수 선언: `scraper_config.py:9-10`
- 국내선 판별 하드코딩: `scraper_v2.py:378-380`
- 결과 대기 selector: `scraper_v2.py:213-236`
- 고정 JS/정규식: `scraper_config.py:28-29`, `scraper_config.py:161`, `scraper_config.py:320`
- 멀티/날짜검색 `cabin_class` 누락 경로: `ui/workers.py:160`, `ui/workers.py:289`
- 단일 검색 `cabin_class` 전달 경로: `ui/workers.py:60`
- 강제 종료 fallback: `gui_v2.py:550`, `gui_v2.py:1491`
- 가격 알림 체크 트리거: `gui_v2.py:972`, `gui_v2.py:984`
- 설정 파일명 불일치: `README.md:290`, `README.md:292`, `config.py:83`, `config.py:86`
- 테스트가 fake/monkeypatch 중심: `tests/test_workers_and_scraper.py:47`, `tests/test_workers_and_scraper.py:150`

## 부록 B. 전제(Assumptions)

1. 산출물은 단일 문서 `SCRAPING_AUDIT.md`로 관리한다.
2. 형식은 리스크 + 개선안 통합형을 유지한다.
3. 점검 범위는 엔드투엔드 전체를 기본값으로 한다.
