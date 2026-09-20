from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QMessageBox,
    QRadioButton,
    QSpinBox,
)
from database import PriceAlert
from gui_v2 import MainWindow, resolve_log_level
from scraper_v2 import FlightResult
from ui.export_helpers import (
    export_flights_to_csv,
    export_flights_to_excel,
    flight_export_headers,
    flight_export_rows,
    flight_to_export_row,
)

from tests.support_gui import _DummyLogViewer


def test_price_alert_matching_respects_return_date(monkeypatch):
    class _DummyDB:
        def __init__(self):
            self.updated = []
            self.triggered = []
            self.alerts = [
                PriceAlert(1, "ICN", "NRT", "20260301", "20260305", 300000, 1, None, None, 0, "now"),
                PriceAlert(2, "ICN", "NRT", "20260301", "20260306", 300000, 1, None, None, 0, "now"),
                PriceAlert(3, "ICN", "NRT", "20260301", None, 300000, 1, None, None, 0, "now"),
            ]

        def get_active_alerts(self):
            return self.alerts

        def update_alert_check(self, alert_id, current_price):
            self.updated.append((alert_id, current_price))
            return True

        def mark_alert_triggered(self, alert_id):
            self.triggered.append(alert_id)
            return True

    class _DummyContext:
        def __init__(self):
            self.db = _DummyDB()
            self.log_viewer = _DummyLogViewer()
            self.current_search_params = {
                "origin": "ICN",
                "dest": "NRT",
                "dep": "20260301",
                "ret": "20260305",
            }

    ctx = _DummyContext()
    results = [FlightResult(airline="Test", price=250000, departure_time="10:00", arrival_time="12:00")]

    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    MainWindow._check_price_alerts(ctx, results)

    assert 1 in ctx.db.triggered
    assert 3 in ctx.db.triggered
    assert 2 not in ctx.db.triggered
    assert all(alert_id != 2 for alert_id, _ in ctx.db.updated)

def test_price_alert_matching_requires_adults(monkeypatch):
    class _DummyDB:
        def __init__(self):
            self.updated = []
            self.triggered = []
            self.alerts = [
                PriceAlert(1, "ICN", "NRT", "20260301", "20260305", 300000, 1, None, None, 0, "now", adults=1),
                PriceAlert(2, "ICN", "NRT", "20260301", "20260305", 300000, 1, None, None, 0, "now", adults=2),
            ]

        def get_active_alerts(self):
            return self.alerts

        def update_alert_check(self, alert_id, current_price):
            self.updated.append((alert_id, current_price))
            return True

        def mark_alert_triggered(self, alert_id):
            self.triggered.append(alert_id)
            return True

    class _DummyContext:
        def __init__(self):
            self.db = _DummyDB()
            self.log_viewer = _DummyLogViewer()
            self.current_search_params = {
                "origin": "ICN",
                "dest": "NRT",
                "dep": "20260301",
                "ret": "20260305",
                "adults": 2,
                "cabin_class": "ECONOMY",
            }

    ctx = _DummyContext()
    results = [FlightResult(airline="Test", price=250000, departure_time="10:00", arrival_time="12:00")]

    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    MainWindow._check_price_alerts(ctx, results)

    assert ctx.db.triggered == [2]
    assert ctx.db.updated == [(2, 250000)]

def test_auto_alert_db_read_failure_is_logged_without_worker():
    class _FailingDb:
        def get_active_alerts(self):
            raise RuntimeError("db locked")

    class _DummyContext:
        def __init__(self):
            self.alert_worker = None
            self.db = _FailingDb()
            self.log_viewer = _DummyLogViewer()
            self.events = []
            self._last_alert_auto_error = ""

        def _get_running_workers(self):
            return []

        def _emit_telemetry_event(self, payload):
            self.events.append(payload)

    ctx = _DummyContext()
    MainWindow._run_auto_alert_check(ctx, force=True)

    assert ctx.alert_worker is None
    assert "DB 조회 실패" in ctx._last_alert_auto_error
    assert any("DB 조회 실패" in log for log in ctx.log_viewer.logs)
    assert ctx.events[0]["error_code"] == "AUTO_ALERT_DB_READ_FAILED"

def test_auto_alert_failure_logs_and_stores_error():
    class _DummyDB:
        def __init__(self):
            self.update_calls = []

        def update_alert_check(self, alert_id, current_price, last_error=""):
            self.update_calls.append((alert_id, current_price, last_error))
            return True

    class _DummyContext:
        def __init__(self):
            self.db = _DummyDB()
            self.log_viewer = _DummyLogViewer()

    ctx = _DummyContext()
    MainWindow._on_auto_alert_check_failed(ctx, 7, "ICN", "NRT", "boom\ntrace")

    assert ctx.db.update_calls == [(7, None, "boom")]
    assert any("자동 알림 점검 실패" in log for log in ctx.log_viewer.logs)

def test_auto_alert_no_result_stores_no_result_status():
    class _DummyDB:
        def __init__(self):
            self.update_calls = []

        def update_alert_check(self, alert_id, current_price, last_error=""):
            self.update_calls.append((alert_id, current_price, last_error))
            return True

    class _DummyContext:
        def __init__(self):
            self.db = _DummyDB()
            self.log_viewer = _DummyLogViewer()

    ctx = _DummyContext()
    MainWindow._on_auto_alert_no_result(ctx, 8, "ICN", "NRT")

    assert ctx.db.update_calls == [(8, None, "NO_RESULT: 검색 결과 없음")]
    assert any("결과 없음" in log for log in ctx.log_viewer.logs)

def test_main_csv_export_uses_shared_benefit_columns(tmp_path, monkeypatch):
    class _DummyContext:
        def __init__(self):
            self.all_results = [
                FlightResult(
                    airline="제주항공",
                    price=39900,
                    benefit_price=38930,
                    benefit_label="삼성카드 2.5% 캐시백 적용 시",
                    departure_time="06:15",
                    arrival_time="07:30",
                )
            ]
            self.log_viewer = _DummyLogViewer()

    output_path = tmp_path / "main_export.csv"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(output_path), "CSV Files (*.csv)"),
    )
    monkeypatch.setattr(
        QMessageBox,
        "information",
        lambda *args, **kwargs: QMessageBox.StandardButton.Ok,
    )

    ctx = _DummyContext()
    MainWindow._export_to_csv(ctx)
    content = output_path.read_text(encoding="utf-8-sig")

    assert "혜택가" in content
    assert "혜택 정보" in content
    assert "38930" in content

def test_export_helper_contains_benefit_and_split_price_fields():
    flight = FlightResult(
        airline="제주항공",
        return_airline="대한항공",
        price=100000,
        benefit_price=95000,
        benefit_label="카드 혜택",
        departure_time="06:15",
        arrival_time="07:30",
        outbound_price=40000,
        return_price=60000,
    )

    headers = flight_export_headers()
    row = flight_to_export_row(flight)
    data = dict(zip(headers, row))

    assert data["오는편 항공사"] == "대한항공"
    assert data["혜택가"] == 95000
    assert data["혜택 정보"] == "카드 혜택"
    assert data["가는편 가격"] == 40000
    assert data["오는편 가격"] == 60000

def test_export_rows_neutralize_formula_like_text():
    flight = FlightResult(
        airline="=HYPERLINK(\"http://example.test\")",
        return_airline="+SUM(1,1)",
        price=100000,
        benefit_label="@cmd",
        source="-danger",
        departure_time="06:15",
        arrival_time="07:30",
    )

    row = flight_export_rows([flight])[0]

    assert row[0].startswith("'=")
    assert row[1].startswith("'+")
    assert row[4].startswith("'@")
    assert row[11].startswith("'-")
    assert row[2] == 100000

def test_csv_and_xlsx_exports_neutralize_formula_like_text(tmp_path):
    import openpyxl

    flight = FlightResult(
        airline="=cmd",
        price=100000,
        benefit_label="+promo",
        source="@source",
        departure_time="06:15",
        arrival_time="07:30",
    )
    csv_path = tmp_path / "safe.csv"
    xlsx_path = tmp_path / "safe.xlsx"

    export_flights_to_csv(str(csv_path), [flight])
    export_flights_to_excel(str(xlsx_path), [flight])

    csv_content = csv_path.read_text(encoding="utf-8-sig")
    assert "'=cmd" in csv_content
    assert "'+promo" in csv_content
    assert "'@source" in csv_content

    workbook = openpyxl.load_workbook(xlsx_path, data_only=False)
    worksheet = workbook.active
    assert worksheet is not None
    assert worksheet["A2"].value == "'=cmd"
    assert worksheet["E2"].value == "'+promo"
    assert worksheet["L2"].value == "'@source"

