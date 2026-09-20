"""Result table file export dialogs (SRP: export dialogs only).

Row/column mapping lives in `ui.export_helpers`; this module only owns
the file-dialog and message-box interaction.
"""

from datetime import datetime
from typing import Any

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from ui.export_helpers import export_flights_to_csv, export_flights_to_excel


try:
    import openpyxl  # noqa: F401

    HAS_OPENPYXL = True
except ImportError:
    openpyxl = None
    HAS_OPENPYXL = False


def export_to_excel(table: Any) -> None:
    """검색 결과를 Excel 파일로 내보내기"""
    if not table.results_data:
        QMessageBox.warning(table, "경고", "내보낼 데이터가 없습니다.")
        return

    if not HAS_OPENPYXL:
        QMessageBox.warning(table, "경고", "openpyxl이 설치되지 않았습니다.\npip install openpyxl")
        return

    filename, _ = QFileDialog.getSaveFileName(
        table, "Excel로 저장",
        f"flight_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        "Excel Files (*.xlsx)"
    )

    if not filename:
        return

    try:
        export_flights_to_excel(filename, table.results_data)
        QMessageBox.information(table, "완료", f"Excel 파일이 저장되었습니다:\n{filename}")
    except Exception as e:
        QMessageBox.critical(table, "오류", f"저장 실패: {e}")


def export_to_csv(table: Any) -> None:
    """검색 결과를 CSV 파일로 내보내기"""
    if not table.results_data:
        QMessageBox.warning(table, "경고", "내보낼 데이터가 없습니다.")
        return

    filename, _ = QFileDialog.getSaveFileName(
        table, "CSV로 저장",
        f"flight_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        "CSV Files (*.csv)"
    )

    if not filename:
        return

    try:
        export_flights_to_csv(filename, table.results_data)
        QMessageBox.information(table, "완료", f"CSV 파일이 저장되었습니다:\n{filename}")
    except Exception as e:
        QMessageBox.critical(table, "오류", f"저장 실패: {e}")
