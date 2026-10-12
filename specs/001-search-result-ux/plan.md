# Implementation Plan: 검색 입력·가격 결과 조회 UX 정리

**Branch**: `001-search-result-ux` | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

## Summary

결과 표·필터·검색 패널의 표시 계층만 수정한다. 스크래핑 추출, `FlightResult` 형태, DB/환경설정 스키마, export 컬럼은 건드리지 않는다. 새 모듈을 만들지 않으므로 PyInstaller hiddenimports 변경은 없다.

## Technical Context

- **Language/Version**: Python 3.10+
- **Primary Dependencies**: PyQt6
- **Testing**: pytest (`tests/test_gui_*.py`, `tests/test_audit_improvements.py`), pyright
- **Constraints**: facade import 경로와 CLAUDE.md의 Compatibility Contracts 유지. 테스트가 `MainWindow` 메서드를 더미 컨텍스트로 호출하므로 새 위젯 접근은 `hasattr` 가드로 감싼다.

## Design Decisions

| 항목 | 결정 | 이유 |
| --- | --- | --- |
| 숫자 정렬 | `formatting.py`에 정렬 키 role을 비교하는 `SortableItem` 추가 | `QTableWidgetItem`은 표시 문자열로 정렬한다 |
| 비교가 기준 | `_apply_filter`에서 가격 필터와 표시 순서를 `effective_flight_price`로 처리 | 스크래퍼 계층의 기본가 정렬은 그대로 둔다 |
| 가격 0 | 정렬 키를 무한대로 두어 오름차순에서 맨 뒤 | 가격 미확인 항공편이 최저가로 보이지 않게 |
| 빈 표 문구 | `ResultTable.set_empty_message()` | 더미 테이블의 `update_data(rows)` 시그니처를 깨지 않는다 |
| 결과 요약 | `filtering.py`의 순수 함수 `build_result_summary()` + `result_summary_label` | 위젯 없이 단위 테스트 가능 |
| 경유 필터 | 콤보 `cb_stops`가 `direct_only`/`include_layover`/`max_stops` 키를 파생 | 필터 dict 계약 유지 |
| 전체 경유 | `max_stops = UNLIMITED_STOPS(99)` | 기존 기본값 3은 4회 이상 경유를 말없이 숨겼다 |
| 선호시간 | 검색 패널 컨트롤 제거, `FilterPanel.set_departure_time_range()`로 초기화 | 설정 대화상자가 유일한 저장 지점이 된다 |
| 결과 없음 | `_search_finished` 빈 결과 시 `all_results` 비움 | 필터 조작으로 이전 검색 결과가 되살아나는 것을 방지 |

## Affected Files

- `ui/components_result_table/{formatting,table,table_config,context_menu}.py`
- `ui/components_filter_panel/{panel,state}.py`
- `ui/search_panel_{build,actions,params,shared}.py`
- `app/mainwindow/{filtering,search_single,exports,session,ui_bootstrap_sections}.py`
- `tests/test_gui_results.py`, `tests/test_gui_search_panel.py`, `tests/test_audit_improvements.py`, 신규 `tests/test_result_ux.py`
- `README.md`, `CLAUDE.md` (문구·테스트 기준 수치)

## Verification

```powershell
python -m pytest -q
pyright --warnings
python scripts\check_tracked_text.py --check-lf
git diff --check
```
