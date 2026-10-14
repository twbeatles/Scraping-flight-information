"""ExportsMixin methods extracted from MainWindow."""

from app.mainwindow.shared import (
    QApplication,
    QFileDialog,
    QMessageBox,
    datetime,
)
from typing import TYPE_CHECKING, Any
from scraping.models import effective_flight_price
from ui.export_helpers import export_flights_to_csv

if TYPE_CHECKING:
    from app.main_window import MainWindow


class ExportsMixin:
    def _export_to_csv(self: Any):
        """검색 결과를 CSV 파일로 저장"""
        if not self.all_results:
            QMessageBox.warning(self, "내보내기 오류", "내보낼 검색 결과가 없습니다.")
            return
        
        fname, _ = QFileDialog.getSaveFileName(
            self, "CSV로 저장", 
            f"flight_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not fname:
            return
        
        try:
            export_flights_to_csv(fname, self.all_results)
            self.log_viewer.append_log(f"📥 CSV 저장 완료: {fname}")
            QMessageBox.information(self, "저장 완료", f"{len(self.all_results)}개 결과가 저장되었습니다.\n{fname}")
            
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", f"파일 저장 중 오류 발생:\n{e}")
    def _copy_results_to_clipboard(self: Any):
        """검색 결과를 클립보드에 복사"""
        if not self.all_results:
            QMessageBox.warning(self, "복사 오류", "복사할 검색 결과가 없습니다.")
            return
        
        from PySide6.QtWidgets import QApplication
        
        lines = ["항공사\t비교가(혜택 반영)\t기본가\t가는편 출발\t가는편 도착\t가는편 경유\t오는편 출발\t오는편 도착"]
        for flight in self.all_results[:50]:  # 최대 50개
            lines.append(
                "\t".join(
                    [
                        flight.airline,
                        f"{effective_flight_price(flight):,}원",
                        f"{flight.price:,}원",
                        flight.departure_time,
                        flight.arrival_time,
                        f"{flight.stops}회",
                        getattr(flight, "return_departure_time", "") or "-",
                        getattr(flight, "return_arrival_time", "") or "-",
                    ]
                )
            )
        
        text = "\n".join(lines)
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text)
        
        self.log_viewer.append_log(f"📋 {min(len(self.all_results), 50)}개 결과 클립보드에 복사됨")
        QMessageBox.information(self, "복사 완료", f"{min(len(self.all_results), 50)}개 결과가 클립보드에 복사되었습니다.")

    # --- Multi-Destination Search ---

