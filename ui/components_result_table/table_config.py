"""Result table layout constants (SRP: layout/style constants only)."""

COLUMN_LABELS = [
    "항공사", "가격 (혜택 반영)", "가는편 출발", "가는편 도착", "가는편 경유",
    "오는편 출발", "오는편 도착", "오는편 경유", "소요시간", "공항", "수하물", "잔여석", "출처",
]

COL_AIRLINE = 0
COL_PRICE = 1
COL_DEP = 2
COL_ARR = 3
COL_STOPS = 4
COL_RET_DEP = 5
COL_RET_ARR = 6
COL_RET_STOPS = 7
COL_DURATION = 8
COL_AIRPORT = 9
COL_BAGGAGE = 10
COL_SEATS = 11
COL_SOURCE = 12

INITIAL_WIDTHS = [180, 250, 95, 95, 95, 95, 95, 95, 180, 110, 90, 70, 80]

# 마지막 열이 남는 폭을 가져간다. 앞쪽 열을 늘리면 좁은 창에서 그 열이 최소 폭으로 눌린다.
STRETCH_COLUMN = COL_SOURCE

MIN_SECTION_SIZE = 60

DEFAULT_ROW_HEIGHT = 48

PLACEHOLDER_ROW_HEIGHT = 80

RESULT_TABLE_STYLESHEET = """
    QTableWidget {
        font-size: 13px;
    }
    QHeaderView::section {
        font-size: 13px;
        font-weight: 600;
        padding: 8px 4px;
    }
"""

PLACEHOLDER_TEXT = "🔍 검색 결과가 없습니다. 검색 조건을 확인해주세요."

FILTERED_EMPTY_TEXT = "🎯 필터 조건에 맞는 결과가 없습니다 (전체 {total}건). 필터의 '↺ 초기화'를 눌러보세요."
