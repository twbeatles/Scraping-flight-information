# Flight Bot 기능 구현 감사 리포트 (2026-03-05)

- 작성일: 2026-03-05
- 대상 저장소: `Scraping-flight-information`
- 참조 문서: `README.md`, `claude.md`
- 초기 실행 확인(조치 전):
  - `pytest -q` -> `44 passed`
  - `scraping.parallel.ParallelSearcher` 최소 실행 스모크에서 `NameError` 재현

---

## 0) 후속 조치 완료 업데이트 (2026-03-05)

- 적용 결과:
  - [x] `scraping/parallel.py`: 로거 정의 추가, `ParallelSearcher` 공개 API 유지
  - [x] `app/mainwindow/ui_bootstrap.py`: 더블클릭 URL에 `cabin/adult` 반영
  - [x] `app/mainwindow/history.py`: 기록 복원 경로를 `_restore_search_panel_from_params()`로 통합
  - [x] `ui/components_search_panel.py`: 국내선 모드 비국내 코드 하드 차단
  - [x] `config.py`: 설정 import 후 `search_history` 리스트 정규화 + 20개 상한 강제
  - [x] `storage/db_last_search.py`: 깨진 `__main__` 블록 제거
  - [x] 회귀 테스트 추가/수정 완료
- 재검증:
  - `pytest -q` -> `49 passed`
  - `ParallelSearcher` 경로에서 `NameError` 재현되지 않음

---

## 1) 핵심 발견사항 (심각도 순)

### [P1] `ParallelSearcher` 실행 시 `logger` 미정의로 즉시 예외 발생
- 근거:
  - `scraping/parallel.py:61`, `scraping/parallel.py:73`, `scraping/parallel.py:117`, `scraping/parallel.py:197`, `scraping/parallel.py:249`에서 `logger` 사용
  - 동일 파일에 `import logging` 및 `logger = logging.getLogger(...)` 정의 없음
- 영향:
  - `from scraper_v2 import ParallelSearcher` 경로의 병렬 검색 API가 런타임에서 즉시 실패
  - 기능 확장/재사용 시 장애 전이 위험 큼
- 권장 조치:
  - `scraping/parallel.py`에 로거 정의 추가
  - `tests/`에 `ParallelSearcher` 스모크 테스트 추가
  - 미사용 경로라면 모듈을 비공개 처리하거나 제거 검토

### [P1] 결과 더블클릭 예약 URL에 `cabin/adult`가 누락되어 검색 조건 불일치
- 근거:
  - 더블클릭 URL 생성: `app/mainwindow/ui_bootstrap.py:303-306`
  - 좌석/인원 파라미터 없는 URL로 오픈
  - URL 계약 문서: `claude.md:1132-1134` (`?cabin={cabin}&adult={adults}` 명시)
  - 사용자 기능 문서: `README.md:133`(좌석 등급 선택), `README.md:140`(더블클릭 예약 페이지 열기)
- 영향:
  - 사용자가 검색한 조건(좌석/인원)과 예약 페이지 조건이 달라져 가격/결과 일치성이 깨질 수 있음
- 권장 조치:
  - `current_search_params`의 `cabin_class`, `adults`를 URL 쿼리에 반영
  - 더블클릭 동작 회귀 테스트 추가 (`?cabin=...&adult=...` 검증)

### [P2] 검색 기록 복원 경로에서 `cabin_class`가 누락됨
- 근거:
  - 기록 저장 시 `cabin_class` 포함: `app/mainwindow/search_single.py:19-25`
  - 기록 복원(`restore_search_from_history`)은 성인만 복원하고 좌석등급 복원 누락: `app/mainwindow/history.py:107`
  - 반면 공통 복원 함수 `_restore_search_panel_from_params`는 `cabin_class` 복원 구현: `app/mainwindow/history.py:71-75`
- 영향:
  - “검색 기록 복원” 후 실제 재검색 조건이 기록 당시와 달라질 수 있음
- 권장 조치:
  - `restore_search_from_history()`에서 `_restore_search_panel_from_params()`를 재사용하도록 통합
  - 기록 복원 시 좌석등급까지 동일 복원되는 테스트 추가

### [P2] 국내선 모드에서 비국내 코드를 수동 입력해도 검색이 통과됨
- 근거:
  - 콤보박스가 editable: `ui/components_search_panel.py:237-238`
  - 검색 검증은 “3자리 영문”만 검사: `ui/components_search_panel.py:366-372`
  - 국내선 모드 전용 제한 검증 부재 (`rb_domestic` 상태에서 코드 집합 검증 없음)
  - 문서 기대: `README.md:128-130` (국내선은 국내 공항 간 이동)
- 영향:
  - UI 모드(국내선)와 실제 검색 동작(국제선 가능)이 어긋나 사용자 혼란/오입력 유발
- 권장 조치:
  - `rb_domestic` 선택 시 `origin/dest`를 `config.DOMESTIC_AIRPORT_CODES`로 강제 검증
  - 또는 국내선 모드에서는 editable 비활성화

### [P3] 설정 Import 시 `search_history` 상한(20개) 보장이 깨짐
- 근거:
  - 일반 추가 경로는 20개 제한: `config.py:155-160`
  - Import 경로는 리스트 병합만 수행하고 길이 제한 없음: `config.py:275-280`
- 영향:
  - 대용량 history 유입 시 설정 파일/히스토리 탭 비대화 가능
- 권장 조치:
  - Import 후 `search_history`를 최신순 20개로 trim
  - Import 정합성 테스트 추가

### [P3] `db_last_search.py` 단독 실행 블록이 깨져 있음
- 근거:
  - `if __name__ == "__main__":`에서 `FlightDatabase` 직접 사용: `storage/db_last_search.py:166-167`
  - 해당 파일 내 `FlightDatabase` import 부재
- 영향:
  - 유지보수/수동 디버깅 시 스크립트 실행 실패
- 권장 조치:
  - 테스트 블록 제거 또는 올바른 import 추가

---

## 2) 추가 구현 권장 항목

1. URL 일치성 강화
- 더블클릭 예약 URL에 검색 조건(`cabin`, `adult`)을 강제 포함
- 필요 시 `child`, `infant`까지 일관성 확장

2. 복원 로직 단일화
- 프로필/히스토리/세션/마지막검색 복원 모두 `_restore_search_panel_from_params`로 통합
- 복원 경로별 중복 코드를 제거해 drift 방지

3. 입력 검증 체계화
- 모드별(국내/국제) 코드 검증 정책 분리
- 검증 실패 사유를 사용자 메시지로 명확화

4. 미사용/호환 API 정리
- `scraping/parallel.py`를 실제 경로로 유지할지, deprecated 처리할지 결정
- 유지 시 테스트/로깅/예외 정책을 `ui/workers_*`와 동일 수준으로 정합화

---

## 3) 테스트 보강 제안 (우선순위)

1. `test_parallel_searcher_smoke_no_nameerror`
2. `test_double_click_url_preserves_cabin_and_adults`
3. `test_restore_search_from_history_restores_cabin_class`
4. `test_domestic_mode_rejects_non_domestic_manual_code`
5. `test_import_settings_trims_search_history_to_20`

---

## 4) 이번 점검에서 확인한 긍정 신호

- 문서 기준 핵심 안정화 항목(워커 취소 정책, 30일 하드캡, 2~5 목적지 제한, telemetry 보존 정책)은 코드와 대체로 정합
- 회귀 테스트 스위트가 `44 passed`로 유지되어 기존 개선사항이 안정적으로 보호되고 있음
