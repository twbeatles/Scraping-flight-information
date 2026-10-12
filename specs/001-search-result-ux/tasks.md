# Tasks: 검색 입력·가격 결과 조회 UX 정리

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Phase 1: US1 - 가격 기준 통일 (P1)

- [x] T001 [US1] `ui/components_result_table/formatting.py`에 `SortableItem`과 정렬 키 role 추가, 가격·경유·잔여석 셀에 적용
- [x] T002 [US1] `build_price_item`을 비교가 주 표시 + 기본가/구간가 보조 표기로 변경 (툴팁 유지)
- [x] T003 [US1] `app/mainwindow/filtering.py` 가격 필터와 표시 순서를 `effective_flight_price` 기준으로 변경
- [x] T004 [US1] `search_single.py`, `session.py`의 최저가 문구를 비교가 최솟값으로 계산
- [x] T005 [US1] 테스트: 숫자 정렬, 혜택가 필터, 최저가 행 일치

## Phase 2: US2 - 결과 요약과 표 구성 (P2)

- [x] T006 [US2] `table_config.py` 컬럼 재구성 (가는편/오는편 경유 헤더, 소요시간 추가, 출처 폭 축소)
- [x] T007 [US2] `ResultTable.set_empty_message()`와 필터/검색 빈 표 문구 구분
- [x] T008 [US2] `build_result_summary()`와 `result_summary_label`, 누락 경고 표시
- [x] T009 [US2] 빈 검색 결과 시 `all_results` 초기화
- [x] T010 [US2] 행 복사·결과 복사에 비교가와 오는편 포함
- [x] T011 [US2] 테스트: 요약 문구, 빈 표 문구, 컬럼 인덱스, 복사 내용

## Phase 3: US3 - 필터 단순화 (P3)

- [x] T012 [US3] `FilterPanel` 경유 컨트롤을 `cb_stops` 콤보로 통합 (dict 키 유지)
- [x] T013 [US3] `FilterPanel.set_departure_time_range()`와 설정 선호시간 초기화
- [x] T014 [US3] 검색 패널 선호시간 컨트롤 제거
- [x] T015 [US3] 필터 상태 문구 한글화
- [x] T016 [US3] 테스트: 경유 콤보 매핑, 선호시간 초기화

## Phase 4: US4 - 입력 편의 (P4)

- [x] T017 [US4] 출발지↔도착지 교환 버튼
- [x] T018 [US4] 날짜 최소값과 오는 날 자동 보정, 테마 안전한 비활성 처리
- [x] T019 [US4] 승객 검증 (유아 ≤ 성인, 합계 ≤ 9)
- [x] T020 [US4] 검색 버튼 문구 통일, 캐시 무시 버튼 문구, `\n` 리터럴 수정, 헤더 아이콘 정정
- [x] T021 [US4] 테스트: 교환, 날짜 보정, 승객 검증, 버튼 문구

## Phase 5: Polish

- [x] T022 README/CLAUDE.md 문구와 테스트 기준 수치 갱신
- [x] T023 `pytest`, `pyright --warnings`, LF check, `git diff --check`
