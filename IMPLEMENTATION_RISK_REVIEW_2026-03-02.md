# Flight Bot 기능 구현 리스크 점검 리포트 (2026-03-02)

## 1) 점검 기준
- 참조 문서: `README.md`, `claude.md`
- 참조 코드: `gui_v2.py`, `ui/workers.py`, `ui/components.py`, `ui/dialogs.py`, `scraper_v2.py`, `database.py`, `tests/*`
- 현재 테스트 상태: `pytest -q` 기준 `31 passed`

## 2) 핵심 발견사항 (기능 구현 관점)

### [P1] 다중 목적지 개수 제한 미구현 (문서-구현 불일치)
- 근거:
  - 문서에는 다중 목적지 최대 5개로 안내됨 (`README.md:37`)
  - 실제 검증은 최소 2개만 확인하고 상한 제한이 없음 (`ui/dialogs.py:405-410`)
- 영향:
  - 사용자가 과도한 목적지를 선택하면 검색 시간이 급증하고 취소 지연 가능성이 커짐
  - 사용자 기대(최대 5개)와 실제 동작 불일치
- 권장 조치:
  - `MultiDestDialog._on_search()`에 `len(selected) <= 5` 검증 추가
  - 초과 시 즉시 경고 후 실행 차단

### [P1] 다중/날짜 범위 검색 취소 지연 가능성 (ThreadPool 작업 전량 제출)
- 근거:
  - 작업을 한 번에 전부 `submit` (`ui/workers.py:205-210`, `ui/workers.py:358-363`)
  - 취소 시 이미 제출된 작업을 `cancel_futures`로 취소하지 않음
  - `as_completed` 루프 및 컨텍스트 종료까지 대기 구조 (`ui/workers.py:211-238`, `ui/workers.py:365-401`)
- 영향:
  - 사용자가 Esc 취소를 눌러도 백그라운드 작업이 길게 남아 UX 저하
  - 앱 종료 지연/재검색 불가 상태가 길어질 수 있음
- 권장 조치:
  - 취소 시점에 `executor.shutdown(cancel_futures=True)` 경로 도입
  - 작업을 배치 제출(또는 세마포어 기반)로 변경해 미실행 작업 취소 가능하게 개선
  - “취소 후 N초 내 종료”를 검증하는 테스트 추가

### [P1] 정렬 후 우클릭 “정보 복사”가 다른 행 데이터를 복사할 수 있음
- 근거:
  - 우클릭 복사는 시각 행 인덱스를 그대로 `results_data[row]`에 사용 (`ui/components.py:547-551`)
  - 반면 정렬 대응용 매핑 로직은 별도 구현돼 있음 (`ui/components.py:650-658`)
- 영향:
  - 사용자에게 잘못된 항공편 정보 복사/공유 가능
  - 정렬 사용 빈도가 높아 실제 체감 오류로 이어질 확률이 높음
- 권장 조치:
  - `_copy_row_info()`에서 `get_flight_at_row(row)` 사용하도록 통일
  - 정렬 상태에서 복사 정확성을 검증하는 UI 테스트 추가

### [P1] 즐겨찾기 중복 판단 키가 불충분해 왕복 조합이 누락될 수 있음
- 근거:
  - 중복 판정 필드가 `airline, price, departure_time, origin, destination`으로 제한됨 (`database.py:378-386`)
  - 즐겨찾기 추가 시 돌아오는 편 정보는 중복 판정에 포함되지 않음 (`gui_v2.py:779-783`)
- 영향:
  - 서로 다른 왕복 조합(특히 귀국편이 다름)이 “이미 추가됨”으로 차단될 수 있음
- 권장 조치:
  - 중복 판정 키에 `return_departure_time`, `return_airline`, `departure_date`, `return_date` 포함
  - 스키마/쿼리 확장 또는 해시 기반 unique key 도입

### [P2] 날짜 범위 검색: UI 경고(14일)와 실제 처리 상한(30일) 불일치
- 근거:
  - UI는 14일 초과 시 경고 후 계속 진행 가능 (`ui/dialogs.py:564-571`)
  - 워커는 30개 초과 날짜를 내부에서 자동 잘라냄 (`ui/workers.py:305-309`)
- 영향:
  - 사용자는 입력 범위 전체가 검색된다고 인지하지만 실제로 일부 날짜가 누락될 수 있음
- 권장 조치:
  - 다이얼로그에서 30일 초과 입력 자체를 차단하거나
  - “30일까지만 실행”을 사전 명시하고 사용자 재확인 받도록 개선

### [P2] 수동 추출 성공 시 텔레메트리 `manual_mode`가 왜곡될 수 있음
- 근거:
  - 수동 추출 성공 시 `_manual_extract()`가 `_search_finished(results)` 호출 (`gui_v2.py:1268-1273`)
  - `_search_finished()`의 성공 이벤트 payload는 `manual_mode: False` 고정 (`gui_v2.py:1091-1101`)
- 영향:
  - 진단 화면(수동모드 전환률/성공률) 지표 정확도 저하
  - 운영 중 문제 원인 분석이 왜곡될 수 있음
- 권장 조치:
  - `_search_finished()`에서 `manual_mode`를 `self.active_searcher` 상태와 연동
  - 수동 추출 경로 전용 이벤트 타입(`ui_manual_extract_finished`) 분리 권장

### [P2] 노선 전환(국내↔국제) 후 출발지 커스텀 프리셋이 사라질 수 있음
- 근거:
  - 초기 콤보 생성은 출발/도착 모두 커스텀 프리셋 포함 (`ui/components.py:755`, `ui/components.py:779`)
  - 국제선 모드 재구성 시 커스텀 프리셋을 도착지에만 다시 추가 (`ui/components.py:1066-1077`)
- 영향:
  - 사용자가 추가한 출발지 프리셋이 전환 이후 선택 불가 상태가 될 수 있음
- 권장 조치:
  - 국제선 전환 시 출발지/도착지 모두 동일한 프리셋 재주입 로직으로 통일

### [P3] 관측성 로그 보존정책 부재 (DB/JSONL 무기한 증가)
- 근거:
  - 텔레메트리 JSONL은 append-only (`database.py:527-531`)
  - 정리 함수는 `price_history`, `search_logs`만 삭제 (`database.py:664-672`)
- 영향:
  - 장기 사용 시 로그 파일/DB 용량 증가, 진단 조회 성능 저하 가능
- 권장 조치:
  - `telemetry_events` 및 JSONL 보존일/최대크기 정책 추가
  - 앱 시작 시 주기적 로테이션/압축 전략 도입

## 3) 추가하면 좋은 기능 (우선순위 제안)

### 우선순위 A (즉시)
- 다중 목적지 상한 5개 강제 + 선택 UX 개선(“모두 선택” 시 출발지 자동 제외)
- 정렬 상태 정보 복사 정확성 수정
- 다중/날짜 워커 취소 체감 속도 개선

### 우선순위 B (단기)
- 즐겨찾기 중복 키 개선(왕복 상세 포함)
- 날짜 범위 30일 상한을 UI에서 명시적으로 통일
- 수동 추출 경로 텔레메트리 분리

### 우선순위 C (중기)
- 텔레메트리 데이터 보존 정책(보존일, 파일 로테이션, 집계 테이블 분리)
- 취소/타임아웃 시 사용자 피드백 메시지 고도화(“남은 작업 N개 취소 중”)

## 4) 테스트 보강 제안
- 정렬된 테이블에서 우클릭 “정보 복사” 정확성 테스트
- 다중/날짜 검색 취소 시 종료 시간 상한 테스트
- 즐겨찾기 중복 판정(왕복 조합 차이) 회귀 테스트
- 날짜 범위 30일 초과 입력 처리(차단 또는 명시 경고) 테스트

## 5) 반영 완료 상태 (2026-03-02)
- [x] 다중 목적지 선택 `2~5개` 강제 및 출발지 자동 제외 처리
- [x] 다중/날짜 범위 워커 취소 경로 개선 (`cancel_futures=True`, pending future cancel, 활성 searcher 선정리)
- [x] 정렬 상태 우클릭 복사 로직을 `get_flight_at_row()` 기반으로 수정
- [x] 즐겨찾기 중복 판정 강화 (`dedup_key`, `is_favorite_by_entry`, 왕복 상세 필드 반영)
- [x] 날짜 범위 검색 `30일 하드캡` UI 차단 + `15~30일` 확인 다이얼로그 유지
- [x] 수동 추출 텔레메트리 분리 (`ui_manual_extract_finished` 성공/실패 이벤트 추가)
- [x] 국제/국내 전환 후 출발지 커스텀 프리셋 유지
- [x] 텔레메트리 보존 정책 반영 (DB 30일 정리 + JSONL 10MB x 최대 5개 롤링)
- [x] 관련 회귀 테스트 추가 및 업데이트


## 6) ?? ?? ?? ???? ??? ?? ?? (2026-03-02)
- facade ?? ?? ??:
  - `gui_v2.py`, `database.py`, `scraper_v2.py`, `ui/components.py`, `ui/dialogs.py`, `ui/workers.py`
- ?? ?? ?? ??:
  - `app/`, `storage/`, `scraping/`, `ui/*_*.py`
- PyInstaller spec ???:
  - `flight_bot.spec`, `FlightBot_v2.5.spec`, `FlightBot_Simple.spec`
  - ??? `gui_v2.py` ?? + ?? ?? `hiddenimports` ?? ??
- ???/?? ??:
  - `pytest -q` -> `44 passed`
  - import compatibility smoke ??

## 7) ??? ?? ?? (2026-03-02)
- ?? ???(`backups/`)? ?? ?? ??? ??
- `.gitignore`? `backups/`? ??? ?? ??? ?? ??
