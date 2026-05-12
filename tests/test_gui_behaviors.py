from datetime import datetime, timedelta
import logging
import time
from typing import cast

import config
from PyQt6.QtCore import QDate, QSettings, QTimer, Qt
from PyQt6.QtTest import QTest
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
from ui.components import ResultTable, SearchPanel
from ui.export_helpers import flight_export_headers, flight_to_export_row
from ui.search_panel_params import get_panel_search_params


class _DummyLogViewer:
    def __init__(self):
        self.logs = []

    def append_log(self, message):
        self.logs.append(message)

    def clear(self):
        self.logs.clear()


class _DummyGuardContext:
    def __init__(self):
        self.active_searcher = object()
        self.log_viewer = _DummyLogViewer()
        self.closed = False

    def _close_active_browser(self, confirm=False):
        self.closed = True
        self.active_searcher = None


def _build_search_panel():
    class _Panel:
        def __init__(self):
            self.cb_origin = QComboBox()
            self.cb_origin.addItem("ICN", "ICN")
            self.cb_origin.addItem("GMP", "GMP")

            self.cb_dest = QComboBox()
            self.cb_dest.addItem("NRT", "NRT")
            self.cb_dest.addItem("HND", "HND")

            self.date_dep = QDateEdit()
            self.date_ret = QDateEdit()
            self.rb_round = QRadioButton()
            self.rb_oneway = QRadioButton()
            self.rb_group = QButtonGroup()
            self.rb_group.addButton(self.rb_round)
            self.rb_group.addButton(self.rb_oneway)
            self.rb_round.setChecked(True)
            self.date_ret.setEnabled(True)

            self.spin_adults = QSpinBox()
            self.spin_adults.setRange(1, 9)

            self.cb_cabin_class = QComboBox()
            self.cb_cabin_class.addItem("ECONOMY", "ECONOMY")
            self.cb_cabin_class.addItem("BUSINESS", "BUSINESS")
            self.cb_cabin_class.addItem("FIRST", "FIRST")

        def _toggle_return_date(self):
            self.date_ret.setEnabled(self.rb_round.isChecked())

    return _Panel()


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


def test_restore_search_panel_round_trip_and_cabin(qapp):
    panel = _build_search_panel()

    class _DummyContext:
        search_panel: object

    ctx = _DummyContext()
    ctx.search_panel = panel

    dep = (datetime.now() + timedelta(days=7)).strftime("%Y%m%d")
    ret = (datetime.now() + timedelta(days=10)).strftime("%Y%m%d")
    params = {
        "origin": "ICN",
        "dest": "NRT",
        "dep": dep,
        "ret": ret,
        "adults": 2,
        "cabin_class": "BUSINESS",
    }

    MainWindow._restore_search_panel_from_params(ctx, params)

    assert panel.cb_origin.currentData() == "ICN"
    assert panel.cb_dest.currentData() == "NRT"
    assert panel.rb_round.isChecked()
    assert panel.date_ret.isEnabled()
    assert panel.spin_adults.value() == 2
    assert panel.cb_cabin_class.currentData() == "BUSINESS"
    assert panel.date_dep.date() == QDate.fromString(dep, "yyyyMMdd")
    assert panel.date_ret.date() == QDate.fromString(ret, "yyyyMMdd")


def test_restore_search_panel_oneway_disables_return_date(qapp):
    panel = _build_search_panel()

    class _DummyContext:
        search_panel: object

    ctx = _DummyContext()
    ctx.search_panel = panel

    dep = (datetime.now() + timedelta(days=7)).strftime("%Y%m%d")
    params = {
        "origin": "ICN",
        "dest": "NRT",
        "dep": dep,
        "ret": None,
        "adults": 1,
        "cabin_class": "ECONOMY",
    }

    MainWindow._restore_search_panel_from_params(ctx, params)

    assert panel.rb_oneway.isChecked()
    assert panel.date_ret.isEnabled() is False


def test_search_params_prefer_editable_airport_text_over_stale_data(qapp):
    panel = _build_search_panel()
    panel.cb_origin.setEditable(True)
    panel.cb_dest.setEditable(True)
    panel.cb_origin.setCurrentIndex(0)
    panel.cb_dest.setCurrentIndex(0)
    assert panel.cb_origin.currentData() == "ICN"
    assert panel.cb_dest.currentData() == "NRT"

    panel.cb_origin.setEditText("HND")
    panel.cb_dest.setEditText("KIX")

    params = get_panel_search_params(panel)

    assert params["origin"] == "HND"
    assert params["dest"] == "KIX"


def test_restore_search_panel_restores_sel_domestic_route(qapp):
    class _Prefs:
        def __init__(self):
            self._profiles = {}
            self._presets = {}
            self._preferred_time = {"departure_start": 0, "departure_end": 24}

        def get_all_profiles(self):
            return self._profiles

        def get_all_presets(self):
            return self._presets

        def get_preferred_time(self):
            return self._preferred_time

        def set_preferred_time(self, start, end):
            self._preferred_time = {"departure_start": start, "departure_end": end}

        def add_preset(self, code, name):
            self._presets[code] = name

        def remove_preset(self, code):
            self._presets.pop(code, None)

        def save_profile(self, name, params):
            self._profiles[name] = params

        def get_profile(self, name):
            return self._profiles.get(name, {})

    panel = SearchPanel(_Prefs())

    class _DummyContext:
        search_panel: object

    ctx = _DummyContext()
    ctx.search_panel = panel

    params = {
        "origin": "SEL",
        "dest": "CJU",
        "dep": (datetime.now() + timedelta(days=7)).strftime("%Y%m%d"),
        "ret": (datetime.now() + timedelta(days=10)).strftime("%Y%m%d"),
        "adults": 2,
        "cabin_class": "BUSINESS",
        "is_domestic": True,
    }

    MainWindow._restore_search_panel_from_params(ctx, params)

    assert panel.rb_domestic.isChecked() is True
    assert panel.cb_origin.currentData() == "SEL"
    assert panel.cb_dest.currentData() == "CJU"
    assert panel.cb_cabin_class.currentData() == "BUSINESS"


def test_search_panel_save_restore_settings_round_trips_sel(qapp):
    class _Prefs:
        def __init__(self):
            self._profiles = {}
            self._presets = {}
            self._preferred_time = {"departure_start": 0, "departure_end": 24}

        def get_all_profiles(self):
            return self._profiles

        def get_all_presets(self):
            return self._presets

        def get_preferred_time(self):
            return self._preferred_time

        def set_preferred_time(self, start, end):
            self._preferred_time = {"departure_start": start, "departure_end": end}

        def add_preset(self, code, name):
            self._presets[code] = name

        def remove_preset(self, code):
            self._presets.pop(code, None)

        def save_profile(self, name, params):
            self._profiles[name] = params

        def get_profile(self, name):
            return self._profiles.get(name, {})

    QSettings("FlightBot", "FlightComparisonBot").clear()

    panel = SearchPanel(_Prefs())
    panel.rb_domestic.setChecked(True)
    panel._on_flight_type_changed()
    panel.cb_origin.setCurrentIndex(panel.cb_origin.findData("SEL"))
    panel.cb_dest.setCurrentIndex(panel.cb_dest.findData("CJU"))
    panel.save_settings()

    restored = SearchPanel(_Prefs())
    restored.restore_settings()

    assert restored.rb_domestic.isChecked() is True
    assert restored.cb_origin.currentData() == "SEL"
    assert restored.cb_dest.currentData() == "CJU"


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


def test_flight_type_change_preserves_custom_origin_preset(qapp):
    class _RadioStub:
        def __init__(self):
            self._checked: bool = False

        def isChecked(self):
            return self._checked

    class _FakePrefs:
        def get_all_presets(self):
            return {"ZZZ": "Custom Origin", "YYY": "Custom Dest"}

    class _DummyPanel:
        def __init__(self):
            self.prefs = _FakePrefs()
            self.rb_domestic = _RadioStub()
            self.cb_origin = QComboBox()
            self.cb_dest = QComboBox()

            for code, name in {"ICN": "Incheon", "NRT": "Narita"}.items():
                self.cb_origin.addItem(f"{code} ({name})", code)
                self.cb_dest.addItem(f"{code} ({name})", code)
            self.cb_origin.addItem("ZZZ (Custom Origin)", "ZZZ")
            self.cb_dest.addItem("YYY (Custom Dest)", "YYY")
            self.cb_origin.setCurrentIndex(self.cb_origin.findData("ZZZ"))
            self.cb_dest.setCurrentIndex(self.cb_dest.findData("YYY"))

    ctx = _DummyPanel()

    ctx.rb_domestic._checked = True
    SearchPanel._on_flight_type_changed(cast(SearchPanel, ctx))
    assert ctx.cb_origin.findData("ZZZ") == -1

    ctx.rb_domestic._checked = False
    SearchPanel._on_flight_type_changed(cast(SearchPanel, ctx))
    assert ctx.cb_origin.findData("ZZZ") >= 0
    assert ctx.cb_dest.findData("YYY") >= 0


def test_refresh_combos_respects_domestic_mode(qapp):
    class _Prefs:
        def __init__(self):
            self._preferred_time = {"departure_start": 0, "departure_end": 24}

        def get_all_presets(self):
            return {"ZZZ": "Custom International"}

        def add_preset(self, code, name):
            return None

        def remove_preset(self, code):
            return None

        def get_preferred_time(self):
            return self._preferred_time

        def set_preferred_time(self, start, end):
            self._preferred_time = {"departure_start": start, "departure_end": end}

        def get_all_profiles(self):
            return {}

        def save_profile(self, name, params):
            return None

        def get_profile(self, name):
            return {}

    panel = SearchPanel(_Prefs())
    panel.rb_domestic.setChecked(True)
    panel._on_flight_type_changed()
    panel._refresh_combos()

    codes = {
        panel.cb_origin.itemData(index)
        for index in range(panel.cb_origin.count())
    }
    assert codes
    assert codes <= config.DOMESTIC_AIRPORT_CODES
    assert panel.cb_origin.findData("ZZZ") == -1


def test_restore_last_search_avoids_direct_table_render():
    class _DummyStatusBar:
        def __init__(self):
            self.messages = []

        def showMessage(self, msg):
            self.messages.append(msg)

    class _DummyProgress:
        def __init__(self):
            self.formats = []

        def setFormat(self, text):
            self.formats.append(text)

    class _DummyTabs:
        def __init__(self):
            self.index = None

        def setCurrentIndex(self, index):
            self.index = index

    class _DummyDB:
        def get_last_search_results(self):
            return (
                {"origin": "ICN", "dest": "NRT", "dep": "20260301", "ret": "20260305"},
                [FlightResult(airline="A", price=120000, departure_time="10:00", arrival_time="12:00")],
                "2026-01-01 12:00:00",
                48.0,
            )

    class _DummyTable:
        def update_data(self, _):
            raise AssertionError("table.update_data should not be called directly in _restore_last_search")

    class _DummyContext:
        def __init__(self):
            self.db = _DummyDB()
            self.table = _DummyTable()
            self.progress_bar = _DummyProgress()
            self.log_viewer = _DummyLogViewer()
            self.tabs = _DummyTabs()
            self._status_bar = _DummyStatusBar()
            self.apply_calls = 0

        def statusBar(self):
            return self._status_bar

        def _restore_search_panel_from_params(self, _):
            return None

        def _apply_filter(self, filters=None):
            self.apply_calls += 1

    ctx = _DummyContext()
    MainWindow._restore_last_search(ctx)

    assert ctx.apply_calls == 1
    assert ctx.tabs.index == 0
    assert any("오래된 검색 데이터" in msg for msg in ctx._status_bar.messages)


def test_filter_debounce_applies_last_event_once(qapp):
    class _DebounceContext:
        def __init__(self):
            self._pending_filter = None
            self._filter_apply_timer = QTimer()
            self._filter_apply_timer.setSingleShot(True)
            self.applied = []
            self._filter_apply_timer.timeout.connect(
                lambda: MainWindow._run_scheduled_filter_apply(cast(MainWindow, self))
            )

        def _apply_filter(self, filters=None):
            self.applied.append(filters)

    ctx = _DebounceContext()

    for h in range(5):
        MainWindow._schedule_filter_apply(cast(MainWindow, ctx), {"start_time": h, "end_time": 24})

    deadline = time.time() + 0.5
    while time.time() < deadline and not ctx.applied:
        qapp.processEvents()
        time.sleep(0.01)
    assert len(ctx.applied) == 1
    assert ctx.applied[0]["start_time"] == 4


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


def test_resolve_log_level_defaults_and_overrides(monkeypatch):
    monkeypatch.delenv("FLIGHTBOT_LOG_LEVEL", raising=False)
    assert resolve_log_level() == logging.INFO

    monkeypatch.setenv("FLIGHTBOT_LOG_LEVEL", "DEBUG")
    assert resolve_log_level() == logging.DEBUG

    monkeypatch.setenv("FLIGHTBOT_LOG_LEVEL", "NOT_A_LEVEL")
    assert resolve_log_level() == logging.INFO


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


def test_restore_search_from_history_restores_cabin_class(monkeypatch):
    class _HistoryItem:
        def __init__(self, payload):
            self.payload = payload

        def data(self, role):
            if role == Qt.ItemDataRole.UserRole:
                return self.payload
            return None

    panel = _build_search_panel()

    class _DummyContext:
        def __init__(self):
            self.search_panel = panel

        def _restore_search_panel_from_params(self, params):
            MainWindow._restore_search_panel_from_params(self, params)

    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    payload = {
        "origin": "ICN",
        "dest": "NRT",
        "dep": (datetime.now() + timedelta(days=7)).strftime("%Y%m%d"),
        "ret": None,
        "adults": 1,
        "cabin_class": "BUSINESS",
    }
    ctx = _DummyContext()
    MainWindow.restore_search_from_history(ctx, _HistoryItem(payload))

    assert panel.cb_cabin_class.currentData() == "BUSINESS"


def test_domestic_mode_blocks_non_domestic_manual_input(qapp, monkeypatch):
    class _Prefs:
        def __init__(self):
            self._profiles = {}
            self._presets = {}
            self._preferred_time = {"departure_start": 0, "departure_end": 24}

        def get_all_profiles(self):
            return self._profiles

        def get_all_presets(self):
            return self._presets

        def get_preferred_time(self):
            return self._preferred_time

        def set_preferred_time(self, start, end):
            self._preferred_time = {"departure_start": start, "departure_end": end}

        def add_preset(self, code, name):
            self._presets[code] = name

        def remove_preset(self, code):
            self._presets.pop(code, None)

        def save_profile(self, name, params):
            self._profiles[name] = params

        def get_profile(self, name):
            return self._profiles.get(name, {})

    panel = SearchPanel(_Prefs())
    emitted = []
    warnings = []
    panel.search_requested.connect(lambda *args: emitted.append(args))

    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args) or QMessageBox.StandardButton.Ok)

    panel.rb_domestic.setChecked(True)
    panel._on_flight_type_changed()

    idx_origin = panel.cb_origin.findData("GMP")
    if idx_origin >= 0:
        panel.cb_origin.setCurrentIndex(idx_origin)
    panel.cb_dest.setCurrentIndex(-1)
    panel.cb_dest.setEditText("NRT")

    panel._on_search()

    assert warnings
    assert emitted == []
