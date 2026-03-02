from datetime import datetime, timedelta

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QMessageBox

from ui.dialogs import MultiDestDialog, DateRangeDialog, PriceAlertDialog


class _FakePrefs:
    def get_all_presets(self):
        return {
            "ICN": "인천",
            "NRT": "도쿄 나리타",
            "HND": "도쿄 하네다",
            "GMP": "김포",
        }


class _FakeDB:
    def __init__(self):
        self.add_calls = []

    def add_price_alert(self, origin, dest, dep, ret, target, cabin_class="ECONOMY"):
        self.add_calls.append((origin, dest, dep, ret, target, cabin_class))
        return 1

    def get_all_alerts(self):
        return []

    def delete_alert(self, alert_id):
        return True


def test_multi_dest_rejects_origin_in_destinations(qapp, monkeypatch):
    dlg = MultiDestDialog(prefs=_FakePrefs())
    emitted = []
    warnings = []
    dlg.search_requested.connect(lambda *args: emitted.append(args))

    idx = dlg.cb_origin.findData("ICN")
    dlg.cb_origin.setCurrentIndex(idx)
    dlg.dest_checkboxes["ICN"].setChecked(True)
    dlg.dest_checkboxes["NRT"].setChecked(True)

    dep = QDate.currentDate().addDays(7)
    ret = QDate.currentDate().addDays(10)
    dlg.date_dep.setDate(dep)
    dlg.date_ret.setDate(ret)

    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args) or QMessageBox.StandardButton.Ok)

    dlg._on_search()

    assert emitted == []
    assert warnings


def test_multi_dest_enforces_max_five_destinations(qapp, monkeypatch):
    dlg = MultiDestDialog()
    emitted = []
    warnings = []
    dlg.search_requested.connect(lambda *args: emitted.append(args))

    dep = QDate.currentDate().addDays(7)
    ret = QDate.currentDate().addDays(10)
    dlg.date_dep.setDate(dep)
    dlg.date_ret.setDate(ret)

    selectable_codes = [code for code, cb in dlg.dest_checkboxes.items() if cb.isEnabled()]
    assert len(selectable_codes) >= 6
    for code in selectable_codes[:6]:
        dlg.dest_checkboxes[code].setChecked(True)

    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args) or QMessageBox.StandardButton.Ok)
    dlg._on_search()

    assert warnings
    assert emitted == []

    warnings.clear()
    dlg.dest_checkboxes[selectable_codes[5]].setChecked(False)
    dlg._on_search()

    assert warnings == []
    assert len(emitted) == 1
    assert len(emitted[0][1]) == 5


def test_multi_dest_origin_checkbox_auto_excluded(qapp):
    dlg = MultiDestDialog(prefs=_FakePrefs())

    dlg.cb_origin.setCurrentIndex(dlg.cb_origin.findData("ICN"))
    icn_cb = dlg.dest_checkboxes["ICN"]
    assert icn_cb.isEnabled() is False
    assert icn_cb.isChecked() is False

    dlg.cb_origin.setCurrentIndex(dlg.cb_origin.findData("NRT"))
    nrt_cb = dlg.dest_checkboxes["NRT"]
    assert nrt_cb.isEnabled() is False
    assert nrt_cb.isChecked() is False
    assert icn_cb.isEnabled() is True


def test_date_range_allows_single_day_search(qapp, monkeypatch):
    dlg = DateRangeDialog(prefs=_FakePrefs())
    emitted = []
    warnings = []
    dlg.search_requested.connect(lambda *args: emitted.append(args))

    dlg.cb_origin.setCurrentIndex(dlg.cb_origin.findData("ICN"))
    dlg.cb_dest.setCurrentIndex(dlg.cb_dest.findData("NRT"))
    day = QDate.currentDate().addDays(3)
    dlg.date_start.setDate(day)
    dlg.date_end.setDate(day)

    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args) or QMessageBox.StandardButton.Ok)

    dlg._on_search()

    assert warnings == []
    assert len(emitted) == 1
    assert emitted[0][2] == [day.toString("yyyyMMdd")]


def test_date_range_blocks_over_30_days(qapp, monkeypatch):
    dlg = DateRangeDialog(prefs=_FakePrefs())
    emitted = []
    warnings = []
    dlg.search_requested.connect(lambda *args: emitted.append(args))

    dlg.cb_origin.setCurrentIndex(dlg.cb_origin.findData("ICN"))
    dlg.cb_dest.setCurrentIndex(dlg.cb_dest.findData("NRT"))
    start = QDate.currentDate().addDays(3)
    end = start.addDays(30)  # inclusive -> 31 days
    dlg.date_start.setDate(start)
    dlg.date_end.setDate(end)

    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args) or QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    dlg._on_search()

    assert warnings
    assert emitted == []


def test_date_range_allows_30_days_with_confirmation(qapp, monkeypatch):
    dlg = DateRangeDialog(prefs=_FakePrefs())
    emitted = []
    questions = []
    dlg.search_requested.connect(lambda *args: emitted.append(args))

    dlg.cb_origin.setCurrentIndex(dlg.cb_origin.findData("ICN"))
    dlg.cb_dest.setCurrentIndex(dlg.cb_dest.findData("NRT"))
    start = QDate.currentDate().addDays(3)
    end = start.addDays(29)  # inclusive -> 30 days
    dlg.date_start.setDate(start)
    dlg.date_end.setDate(end)

    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: questions.append(args) or QMessageBox.StandardButton.Yes)
    dlg._on_search()

    assert len(questions) == 1
    assert len(emitted) == 1
    assert len(emitted[0][2]) == 30


def test_price_alert_oneway_saves_none_return_date(qapp, monkeypatch):
    db = _FakeDB()
    dlg = PriceAlertDialog(db=db, prefs=_FakePrefs())

    dlg.cb_origin.setCurrentIndex(dlg.cb_origin.findData("ICN"))
    dlg.cb_dest.setCurrentIndex(dlg.cb_dest.findData("NRT"))
    dlg.date_dep.setDate(QDate.currentDate().addDays(7))
    dlg.chk_oneway.setChecked(True)

    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    dlg._add_alert()

    assert db.add_calls
    assert db.add_calls[0][3] is None
    assert db.add_calls[0][5] == "ECONOMY"


def test_price_alert_rejects_return_before_departure(qapp, monkeypatch):
    db = _FakeDB()
    dlg = PriceAlertDialog(db=db, prefs=_FakePrefs())

    dep = QDate.currentDate().addDays(10)
    ret = QDate.currentDate().addDays(7)
    dlg.date_dep.setDate(dep)
    dlg.date_ret.setDate(ret)
    dlg.chk_oneway.setChecked(False)

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args) or QMessageBox.StandardButton.Ok)

    dlg._add_alert()

    assert warnings
    assert db.add_calls == []

