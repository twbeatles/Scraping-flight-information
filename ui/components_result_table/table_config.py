"""Result table layout constants (SRP: layout/style constants only)."""

COLUMN_LABELS = [
    "항공사", "가격", "가는편 출발", "가는편 도착", "경유",
    "오는편 출발", "오는편 도착", "경유", "공항", "수하물", "잔여석", "출처",
]

INITIAL_WIDTHS = [200, 160, 100, 100, 85, 100, 100, 85, 90, 80, 70, 120]

STRETCH_COLUMN = 11

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
