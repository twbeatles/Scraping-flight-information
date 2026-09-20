import logging
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

from tests.support_gui import _DummyGuardContext, _DummyLogViewer


def test_manual_browser_guard_blocks_when_user_declines(monkeypatch):
    ctx = _DummyGuardContext()

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )

    can_proceed = MainWindow._guard_manual_browser_for_new_search(ctx, "새 검색")

    assert can_proceed is False
    assert ctx.closed is False
    assert any("취소" in log for log in ctx.log_viewer.logs)

def test_manual_browser_guard_closes_when_user_accepts(monkeypatch):
    ctx = _DummyGuardContext()

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    can_proceed = MainWindow._guard_manual_browser_for_new_search(ctx, "새 검색")

    assert can_proceed is True
    assert ctx.closed is True

def test_resolve_log_level_defaults_and_overrides(monkeypatch):
    monkeypatch.delenv("FLIGHTBOT_LOG_LEVEL", raising=False)
    assert resolve_log_level() == logging.INFO

    monkeypatch.setenv("FLIGHTBOT_LOG_LEVEL", "DEBUG")
    assert resolve_log_level() == logging.DEBUG

    monkeypatch.setenv("FLIGHTBOT_LOG_LEVEL", "NOT_A_LEVEL")
    assert resolve_log_level() == logging.INFO

def test_double_click_url_includes_cabin_and_adults(monkeypatch):
    opened_urls = []
    monkeypatch.setattr("app.mainwindow.ui_bootstrap.webbrowser.open", lambda url: opened_urls.append(url))

    class _DummyTable:
        def get_flight_at_row(self, row):
            return FlightResult(airline="A", price=120000, departure_time="10:00", arrival_time="12:00")

    class _DummyContext:
        def __init__(self):
            self.table = _DummyTable()
            self.current_search_params = {
                "origin": "ICN",
                "dest": "NRT",
                "dep": "2026-03-01",
                "ret": "2026-03-05",
                "cabin_class": "BUSINESS",
                "adults": 2,
            }
            self.log_viewer = _DummyLogViewer()

    ctx = _DummyContext()
    MainWindow._on_table_double_click(ctx, 0, 0)

    assert len(opened_urls) == 1
    assert "/c:SEL-c:TYO-20260301/c:TYO-c:SEL-20260305" in opened_urls[0]
    assert "?cabin=BUSINESS&infant=0&child=0&adult=2" in opened_urls[0]
    assert any("현재 조건 검색 열기" in log for log in ctx.log_viewer.logs)

def test_start_search_passes_child_and_infant_to_worker(monkeypatch):
    captured: dict[str, object] = {}

    class _Signal:
        def connect(self, _):
            return None

    class _DummyWorker:
        def __init__(self, *args, **kwargs):
            captured.update(kwargs)

        def start(self):
            return None

        progress = _Signal()
        finished = _Signal()
        error = _Signal()
        manual_mode_signal = _Signal()

    monkeypatch.setattr("app.mainwindow.search_single.SearchWorker", _DummyWorker)

    class _DummyPrefs:
        def add_history(self, *_):
            return None

        def save_last_search(self, *_):
            return None

        def get_max_results(self):
            return 1000

    class _DummySearchPanel:
        rb_domestic = type("R", (), {"isChecked": lambda *_: False})()
        spin_child = type("S", (), {"value": lambda *_: 2})()
        spin_infant = type("S", (), {"value": lambda *_: 1})()

        def set_searching(self, *_):
            return None

        def consume_force_refresh(self):
            return False

    class _DummyTable:
        def setRowCount(self, *_):
            return None

    class _DummyManual:
        def setVisible(self, *_):
            return None

    class _DummyTabs:
        def setCurrentIndex(self, *_):
            return None

    class _DummyProgress:
        def setRange(self, *_):
            return None

        def setFormat(self, *_):
            return None

    class _DummyStatus:
        def showMessage(self, *_):
            return None

    class _DummyContext:
        def __init__(self):
            self.prefs = _DummyPrefs()
            self.search_panel = _DummySearchPanel()
            self.table = _DummyTable()
            self.manual_frame = _DummyManual()
            self.log_viewer = _DummyLogViewer()
            self.tabs = _DummyTabs()
            self.progress_bar = _DummyProgress()
            self.active_searcher = None
            self.worker = None
            self.current_search_params = {}

        def _stop_alert_worker_if_running(self):
            return None

        def _ensure_no_running_search(self):
            return True

        def _guard_manual_browser_for_new_search(self, _):
            return True

        def _update_progress(self, *_):
            return None

        def _search_finished(self, *_):
            return None

        def _search_error(self, *_):
            return None

        def _activate_manual_mode(self, *_):
            return None

        def _emit_telemetry_event(self, *_):
            return None

        def statusBar(self):
            return _DummyStatus()

    ctx = _DummyContext()
    MainWindow._start_search(ctx, "ICN", "NRT", "20260301", None, 1, "ECONOMY")

    assert captured["child"] == 2
    assert captured["infant"] == 1
    assert ctx.current_search_params["child"] == 2
    assert ctx.current_search_params["infant"] == 1

def test_start_search_consumes_force_refresh_into_worker(monkeypatch):
    captured = {"force_refresh": None}

    class _Signal:
        def connect(self, _):
            return None

    class _DummyWorker:
        def __init__(self, *args, **kwargs):
            captured["force_refresh"] = kwargs.get("force_refresh")
            self.progress = _Signal()
            self.finished = _Signal()
            self.error = _Signal()
            self.manual_mode_signal = _Signal()

        def start(self):
            return None

    monkeypatch.setattr("app.mainwindow.search_single.SearchWorker", _DummyWorker)

    class _DummyPrefs:
        def add_history(self, *_):
            return None

        def save_last_search(self, *_):
            return None

        def get_max_results(self):
            return 1000

    class _DummySearchPanel:
        rb_domestic = type("R", (), {"isChecked": lambda *_: False})()

        def set_searching(self, *_):
            return None

        def consume_force_refresh(self):
            return True

    class _DummyTable:
        def setRowCount(self, *_):
            return None

    class _DummyManual:
        def setVisible(self, *_):
            return None

    class _DummyTabs:
        def setCurrentIndex(self, *_):
            return None

    class _DummyProgress:
        def setRange(self, *_):
            return None

        def setFormat(self, *_):
            return None

    class _DummyStatus:
        def showMessage(self, *_):
            return None

    class _DummyContext:
        def __init__(self):
            self.prefs = _DummyPrefs()
            self.search_panel = _DummySearchPanel()
            self.table = _DummyTable()
            self.manual_frame = _DummyManual()
            self.log_viewer = _DummyLogViewer()
            self.tabs = _DummyTabs()
            self.progress_bar = _DummyProgress()
            self.active_searcher = None
            self.worker = None
            self.current_search_params = {}

        def _stop_alert_worker_if_running(self):
            return None

        def _ensure_no_running_search(self):
            return True

        def _guard_manual_browser_for_new_search(self, _):
            return True

        def _update_progress(self, *_):
            return None

        def _search_finished(self, *_):
            return None

        def _search_error(self, *_):
            return None

        def _activate_manual_mode(self, *_):
            return None

        def _emit_telemetry_event(self, *_):
            return None

        def statusBar(self):
            return _DummyStatus()

    ctx = _DummyContext()
    MainWindow._start_search(ctx, "ICN", "NRT", "20260301", None, 1, "ECONOMY")

    assert captured["force_refresh"] is True

