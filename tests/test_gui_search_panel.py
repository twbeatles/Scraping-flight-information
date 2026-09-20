from datetime import datetime, timedelta
import time
from typing import cast
import config
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
from ui.search_panel_params import get_panel_search_params

from tests.support_gui import _DummyLogViewer, _build_search_panel


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

