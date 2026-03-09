"""ExportsMixin methods extracted from MainWindow."""

from app.mainwindow.shared import *
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.main_window import MainWindow


class ExportsMixin:
    def _export_to_csv(self: Any):
        """검색 결과를 CSV 파일로 저장"""
        if not self.all_results:
            QMessageBox.warning(self, "내보내기 오류", "내보낼 검색 결과가 없습니다.")
            return
        
        import csv
        
        fname, _ = QFileDialog.getSaveFileName(
            self, "CSV로 저장", 
            f"flight_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not fname:
            return
        
        try:
            with open(fname, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # Header
                writer.writerow([
                    "항공사", "가격", "가는편 출발", "가는편 도착", "경유",
                    "오는편 출발", "오는편 도착", "오는편 경유", "출처"
                ])
                
                # Data
                for flight in self.all_results:
                    writer.writerow([
                        flight.airline,
                        flight.price,
                        flight.departure_time,
                        flight.arrival_time,
                        flight.stops,
                        getattr(flight, 'return_departure_time', '-'),
                        getattr(flight, 'return_arrival_time', '-'),
                        getattr(flight, 'return_stops', '-'),
                        flight.source
                    ])
            
            self.log_viewer.append_log(f"📥 CSV 저장 완료: {fname}")
            QMessageBox.information(self, "저장 완료", f"{len(self.all_results)}개 결과가 저장되었습니다.\n{fname}")
            
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", f"파일 저장 중 오류 발생:\n{e}")
    def _copy_results_to_clipboard(self: Any):
        """검색 결과를 클립보드에 복사"""
        if not self.all_results:
            QMessageBox.warning(self, "복사 오류", "복사할 검색 결과가 없습니다.")
            return
        
        from PyQt6.QtWidgets import QApplication
        
        lines = ["항공사\t가격\t출발\t도착\t경유"]
        for flight in self.all_results[:50]:  # 최대 50개
            lines.append(f"{flight.airline}\t{flight.price:,}원\t{flight.departure_time}\t{flight.arrival_time}\t{flight.stops}회")
        
        text = "\n".join(lines)
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text)
        
        self.log_viewer.append_log(f"📋 {min(len(self.all_results), 50)}개 결과 클립보드에 복사됨")
        QMessageBox.information(self, "복사 완료", f"{min(len(self.all_results), 50)}개 결과가 클립보드에 복사되었습니다.")

    # --- Multi-Destination Search ---



