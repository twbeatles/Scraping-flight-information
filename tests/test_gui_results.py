from PyQt6.QtCore import QDate, QSettings, QTimer, Qt
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
from gui_v2 import MainWindow, resolve_log_level
from scraper_v2 import FlightResult
from ui.components import ResultTable, SearchPanel

from tests.support_gui import _DummyLogViewer


def test_search_finished_uses_single_render_path():
    class _DummySearchPanel:
        def set_searching(self, _):
            return None

    class _DummyProgress:
        def setRange(self, *_):
            return None

        def setValue(self, *_):
            return None

        def setFormat(self, *_):
            return None

    class _DummyTabs:
        def __init__(self):
            self.index = None

        def setCurrentIndex(self, index):
            self.index = index

    class _DummyTable:
        def update_data(self, _):
            raise AssertionError("table.update_data should not be called directly in _search_finished")

    class _DummyContext:
        def __init__(self):
            self.search_panel = _DummySearchPanel()
            self.progress_bar = _DummyProgress()
            self.table = _DummyTable()
            self.log_viewer = _DummyLogViewer()
            self.tabs = _DummyTabs()
            self.current_search_params = {}
            self.db = object()
            self.all_results = []
            self.results = []
            self.apply_calls = 0

        def _apply_filter(self, filters=None):
            self.apply_calls += 1

    ctx = _DummyContext()
    results = [FlightResult(airline="A", price=100000, departure_time="10:00", arrival_time="12:00")]
    MainWindow._search_finished(ctx, results)

    assert ctx.all_results == results
    assert ctx.results == results
    assert ctx.apply_calls == 1
    assert ctx.tabs.index == 0

def test_search_finished_renders_results_when_db_persistence_fails():
    class _DummySearchPanel:
        def set_searching(self, _):
            return None

    class _DummyProgress:
        def setRange(self, *_):
            return None

        def setValue(self, *_):
            return None

        def setFormat(self, *_):
            return None

    class _DummyTabs:
        def __init__(self):
            self.index = None

        def setCurrentIndex(self, index):
            self.index = index

    class _FailingDb:
        def add_price_history_batch(self, *_):
            raise RuntimeError("history locked")

        def log_search(self, *_):
            raise RuntimeError("log locked")

        def save_last_search_results(self, *_):
            raise RuntimeError("snapshot locked")

    class _DummyContext:
        def __init__(self):
            self.search_panel = _DummySearchPanel()
            self.progress_bar = _DummyProgress()
            self.log_viewer = _DummyLogViewer()
            self.tabs = _DummyTabs()
            self.current_search_params = {
                "origin": "ICN",
                "dest": "NRT",
                "dep": "20260301",
                "adults": 1,
            }
            self.db = _FailingDb()
            self.all_results = []
            self.results = []
            self.apply_calls = 0
            self.alert_calls = 0

        def _apply_filter(self, filters=None):
            self.apply_calls += 1

        def _check_price_alerts(self, _results):
            self.alert_calls += 1

        def _record_persistence_warning(self, action_name, error):
            return MainWindow._record_persistence_warning(self, action_name, error)

        def _persist_successful_search(self, results):
            return MainWindow._persist_successful_search(self, results)

    ctx = _DummyContext()
    results = [FlightResult(airline="A", price=100000, departure_time="10:00", arrival_time="12:00")]
    MainWindow._search_finished(ctx, results)

    assert ctx.all_results == results
    assert ctx.apply_calls == 1
    assert ctx.alert_calls == 1
    assert ctx.tabs.index == 0
    assert any("실패" in log for log in ctx.log_viewer.logs)

def test_result_table_copy_row_info_uses_sorted_visual_row(qapp):
    table = ResultTable()
    results = [
        FlightResult(airline="Expensive", price=300000, departure_time="10:00", arrival_time="12:00"),
        FlightResult(airline="Cheap", price=100000, departure_time="08:00", arrival_time="10:00"),
    ]
    table.update_data(results)
    table.sortItems(1, Qt.SortOrder.AscendingOrder)

    target_row = None
    for row in range(table.rowCount()):
        item = table.item(row, 0)
        if item and "Cheap" in item.text():
            target_row = row
            break

    assert target_row is not None
    table._copy_row_info(target_row)
    clipboard = QApplication.clipboard()
    copied = clipboard.text() if clipboard is not None else ""

    assert "Cheap" in copied
    assert "100,000" in copied

def test_manual_extract_logs_success_event_and_uses_search_finished(monkeypatch):
    class _DummySearcher:
        def get_manual_reason(self):
            return "international_api_failed"

        def extract_manual(self):
            return [FlightResult(airline="Manual", price=111000, departure_time="09:00", arrival_time="11:00")]

    class _DummyContext:
        def __init__(self):
            self.active_searcher = _DummySearcher()
            self.current_search_params = {"origin": "ICN", "dest": "NRT"}
            self.log_viewer = _DummyLogViewer()
            self.events = []
            self.search_finished_payload = None

        def _emit_telemetry_event(self, payload):
            self.events.append(payload)

        def _search_finished(self, results):
            self.search_finished_payload = results

    ctx = _DummyContext()
    MainWindow._manual_extract(ctx)

    assert ctx.search_finished_payload is not None
    assert ctx.events
    assert ctx.events[0]["event_type"] == "ui_manual_extract_finished"
    assert ctx.events[0]["success"] is True
    assert ctx.events[0]["manual_mode"] is True
    assert ctx.events[0]["result_count"] == 1
    assert ctx.events[0]["details"]["manual_reason"] == "international_api_failed"

def test_manual_extract_logs_failure_event_when_no_result(monkeypatch):
    class _DummySearcher:
        def get_manual_reason(self):
            return "domestic_return_key_missing"

        def extract_manual(self):
            return []

    class _DummyContext:
        def __init__(self):
            self.active_searcher = _DummySearcher()
            self.current_search_params = {"origin": "ICN", "dest": "NRT"}
            self.log_viewer = _DummyLogViewer()
            self.events = []
            self.search_finished_called = False

        def _emit_telemetry_event(self, payload):
            self.events.append(payload)

        def _search_finished(self, results):
            self.search_finished_called = True

    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    ctx = _DummyContext()
    MainWindow._manual_extract(ctx)

    assert ctx.search_finished_called is False
    assert ctx.events
    assert ctx.events[0]["event_type"] == "ui_manual_extract_finished"
    assert ctx.events[0]["success"] is False
    assert ctx.events[0]["error_code"] == "MANUAL_NO_RESULT"
    assert ctx.events[0]["details"]["manual_reason"] == "domestic_return_key_missing"

def test_activate_manual_mode_logs_manual_reason(monkeypatch):
    class _DummySearcher:
        def get_manual_reason(self):
            return "international_api_failed"

    class _DummySearchPanel:
        def __init__(self):
            self.searching = None

        def set_searching(self, value):
            self.searching = value

    class _DummyFrame:
        def __init__(self):
            self.visible = None

        def setVisible(self, value):
            self.visible = value

    class _DummyLabel:
        def __init__(self):
            self.text = ""

        def setText(self, value):
            self.text = value

    class _DummyProgressBar:
        def __init__(self):
            self.value = None
            self.format = ""

        def setRange(self, *_args):
            return None

        def setValue(self, value):
            self.value = value

        def setFormat(self, value):
            self.format = value

    class _DummyContext:
        def __init__(self):
            self.current_search_params = {"origin": "ICN", "dest": "NRT"}
            self.search_panel = _DummySearchPanel()
            self.manual_frame = _DummyFrame()
            self.manual_status_label = _DummyLabel()
            self.progress_bar = _DummyProgressBar()
            self.log_viewer = _DummyLogViewer()
            self.events = []
            self.active_searcher = None

        def _emit_telemetry_event(self, payload):
            self.events.append(payload)

    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    ctx = _DummyContext()
    MainWindow._activate_manual_mode(ctx, _DummySearcher())

    assert ctx.active_searcher is not None
    assert ctx.search_panel.searching is False
    assert ctx.manual_frame.visible is True
    assert ctx.events[0]["event_type"] == "manual_mode_activated"
    assert ctx.events[0]["details"]["manual_reason"] == "international_api_failed"
    assert any("international_api_failed" in log for log in ctx.log_viewer.logs)

def test_update_progress_dedup_suppresses_duplicate_logs():
    class _DummyStatusBar:
        def __init__(self):
            self.messages = []

        def showMessage(self, msg):
            self.messages.append(msg)

    class _DummyProgress:
        def __init__(self):
            self.formats = []

        def setFormat(self, msg):
            self.formats.append(msg)

    class _DummyContext:
        def __init__(self):
            self._status_bar = _DummyStatusBar()
            self.progress_bar = _DummyProgress()
            self.log_viewer = _DummyLogViewer()
            self._last_progress_msg = ""
            self._last_progress_ts = 0.0

        def statusBar(self):
            return self._status_bar

    ctx = _DummyContext()

    MainWindow._update_progress(ctx, "same message")
    MainWindow._update_progress(ctx, "same message")
    MainWindow._update_progress(ctx, "new message")

    assert ctx.log_viewer.logs == ["same message", "new message"]
    assert ctx._status_bar.messages[-1] == "new message"

def test_search_finished_logs_api_page_truncation_warning():
    class _DummySearchPanel:
        def set_searching(self, _):
            return None

    class _DummyProgress:
        def setRange(self, *_):
            return None

        def setValue(self, *_):
            return None

        def setFormat(self, *_):
            return None

    class _DummyTabs:
        def __init__(self):
            self.index = None

        def setCurrentIndex(self, index):
            self.index = index

    class _DummySearcher:
        def get_search_metrics(self):
            return {"api_pages_truncated": True}

    class _DummyWorker:
        def __init__(self):
            self.searcher = _DummySearcher()

    class _DummyDb:
        def add_price_history_batch(self, *_):
            return None

        def log_search(self, *_):
            return None

        def save_last_search_results(self, *_):
            return None

    class _DummyContext:
        def __init__(self):
            self.search_panel = _DummySearchPanel()
            self.progress_bar = _DummyProgress()
            self.log_viewer = _DummyLogViewer()
            self.tabs = _DummyTabs()
            self.current_search_params = {
                "origin": "ICN",
                "dest": "NRT",
                "dep": "20260301",
                "adults": 1,
            }
            self.db = _DummyDb()
            self.all_results = []
            self.results = []
            self.apply_calls = 0
            self.worker = _DummyWorker()
            self.alert_calls = 0

        def _apply_filter(self, filters=None):
            self.apply_calls += 1

        def _check_price_alerts(self, _results):
            self.alert_calls += 1

        def _record_persistence_warning(self, action_name, error):
            return MainWindow._record_persistence_warning(self, action_name, error)

        def _persist_successful_search(self, results):
            return MainWindow._persist_successful_search(self, results)

        def _emit_telemetry_event(self, _payload):
            return None

    ctx = _DummyContext()
    results = [FlightResult(airline="A", price=100000, departure_time="10:00", arrival_time="12:00")]
    MainWindow._search_finished(ctx, results)

    assert ctx.apply_calls == 1
    assert any("페이지 상한" in log for log in ctx.log_viewer.logs)

def test_search_finished_empty_updates_table_and_shows_result_tab(monkeypatch):
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    class _DummySearchPanel:
        def set_searching(self, _):
            return None

    class _DummyProgress:
        def setRange(self, *_):
            return None

        def setValue(self, *_):
            return None

        def setFormat(self, *_):
            return None

    class _DummyTabs:
        def __init__(self):
            self.index = None

        def setCurrentIndex(self, index):
            self.index = index

    class _DummyTable:
        def __init__(self):
            self.last = None

        def update_data(self, rows):
            self.last = rows

    class _DummyContext:
        def __init__(self):
            self.search_panel = _DummySearchPanel()
            self.progress_bar = _DummyProgress()
            self.table = _DummyTable()
            self.log_viewer = _DummyLogViewer()
            self.tabs = _DummyTabs()
            self.current_search_params = {}

    ctx = _DummyContext()
    MainWindow._search_finished(ctx, [])

    assert ctx.table.last == []
    assert ctx.tabs.index == 0

def test_result_table_price_tooltip_and_csv_include_benefit(tmp_path, qapp, monkeypatch):
    table = ResultTable()
    results = [
        FlightResult(
            airline="제주항공",
            price=39900,
            benefit_price=38930,
            benefit_label="삼성카드 2.5% 캐시백 적용 시",
            departure_time="06:15",
            arrival_time="07:30",
        )
    ]
    table.update_data(results)

    price_item = table.item(0, 1)
    assert price_item is not None
    assert "기본가: 39,900원" in price_item.toolTip()
    assert "혜택가: 38,930원" in price_item.toolTip()
    assert "혜택 정보: 삼성카드 2.5% 캐시백 적용 시" in price_item.toolTip()

    output_path = tmp_path / "benefit.csv"
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

    table.export_to_csv()
    content = output_path.read_text(encoding="utf-8-sig")

    assert "혜택가" in content
    assert "혜택 정보" in content
    assert "38930" in content
    assert "삼성카드 2.5% 캐시백 적용 시" in content

