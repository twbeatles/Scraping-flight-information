from datetime import datetime, timedelta

from PyQt6.QtCore import QDate, QTimer, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QButtonGroup, QComboBox, QDateEdit, QRadioButton, QSpinBox, QMessageBox

from database import PriceAlert
from gui_v2 import MainWindow
from scraper_v2 import FlightResult
from ui.components import ResultTable, SearchPanel


class _DummyLogViewer:
    def __init__(self):
        self.logs = []

    def append_log(self, message):
        self.logs.append(message)


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


def test_restore_search_panel_round_trip_and_cabin(qapp):
    panel = _build_search_panel()

    class _DummyContext:
        pass

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
        pass

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
    copied = QApplication.clipboard().text()

    assert "Cheap" in copied
    assert "100,000" in copied


def test_manual_extract_logs_success_event_and_uses_search_finished(monkeypatch):
    class _DummySearcher:
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


def test_manual_extract_logs_failure_event_when_no_result(monkeypatch):
    class _DummySearcher:
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


def test_flight_type_change_preserves_custom_origin_preset(qapp):
    class _FakePrefs:
        def get_all_presets(self):
            return {"ZZZ": "Custom Origin", "YYY": "Custom Dest"}

    class _DummyPanel:
        def __init__(self):
            self.prefs = _FakePrefs()
            self.rb_domestic = type(
                "_RadioStub",
                (),
                {
                    "__init__": lambda self: setattr(self, "_checked", False),
                    "isChecked": lambda self: self._checked,
                },
            )()
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
    SearchPanel._on_flight_type_changed(ctx)
    assert ctx.cb_origin.findData("ZZZ") == -1

    ctx.rb_domestic._checked = False
    SearchPanel._on_flight_type_changed(ctx)
    assert ctx.cb_origin.findData("ZZZ") >= 0
    assert ctx.cb_dest.findData("YYY") >= 0


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
            self._filter_apply_timer.timeout.connect(lambda: MainWindow._run_scheduled_filter_apply(self))

        def _apply_filter(self, filters=None):
            self.applied.append(filters)

    ctx = _DebounceContext()

    for h in range(5):
        MainWindow._schedule_filter_apply(ctx, {"start_time": h, "end_time": 24})

    QTest.qWait(250)
    assert len(ctx.applied) == 1
    assert ctx.applied[0]["start_time"] == 4
