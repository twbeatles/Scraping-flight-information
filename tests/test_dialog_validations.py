from datetime import datetime, timedelta

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QMessageBox

from database import PriceAlert
from ui.dialogs import MultiDestDialog, DateRangeDialog, PriceAlertDialog


class _FakePrefs:
    def get_all_presets(self):
        return {
            "ICN": "인천",
            "NRT": "도쿄 나리타",
            "HND": "도쿄 하네다",
            "GMP": "김포",
            "CJU": "제주",
            "ZZZ": "커스텀",
        }


class _FakeDB:
    def __init__(self):
        self.add_calls = []

    def add_price_alert(self, origin, dest, dep, ret, target, cabin_class="ECONOMY", adults=1):
        self.add_calls.append((origin, dest, dep, ret, target, cabin_class, adults))
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


def test_advanced_dialogs_include_custom_origin_in_international_mode(qapp):
    multi = MultiDestDialog(prefs=_FakePrefs())
    date_range = DateRangeDialog(prefs=_FakePrefs())
    alert = PriceAlertDialog(db=_FakeDB(), prefs=_FakePrefs())

    assert multi.cb_origin.findData("ZZZ") >= 0
    assert date_range.cb_origin.findData("ZZZ") >= 0
    assert alert.cb_origin.findData("ZZZ") >= 0


def test_advanced_dialogs_domestic_mode_limits_airport_options(qapp):
    multi = MultiDestDialog(prefs=_FakePrefs())
    multi.rb_domestic.setChecked(True)
    multi._refresh_airports()
    assert multi.cb_origin.findData("NRT") == -1
    assert set(multi.dest_checkboxes.keys()) <= {"ICN", "GMP", "CJU", "PUS", "TAE", "SEL"}

    date_range = DateRangeDialog(prefs=_FakePrefs())
    date_range.rb_domestic.setChecked(True)
    date_range._refresh_airport_combos()
    assert date_range.cb_origin.findData("NRT") == -1
    assert date_range.cb_dest.findData("CJU") >= 0

    alert = PriceAlertDialog(db=_FakeDB(), prefs=_FakePrefs())
    alert.rb_domestic.setChecked(True)
    alert._refresh_airport_combos()
    assert alert.cb_origin.findData("NRT") == -1
    assert alert.cb_dest.findData("CJU") >= 0


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
    assert db.add_calls[0][6] == 1


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


def test_price_alert_dialog_displays_no_result_status(qapp):
    class _NoResultDB(_FakeDB):
        def get_all_alerts(self):
            return [
                PriceAlert(
                    1,
                    "ICN",
                    "NRT",
                    "20260301",
                    None,
                    300000,
                    1,
                    "2026-03-01 10:00:00",
                    None,
                    0,
                    "now",
                    last_error="NO_RESULT: 검색 결과 없음",
                )
            ]

    dlg = PriceAlertDialog(db=_NoResultDB(), prefs=_FakePrefs())
    status_item = dlg.table.item(0, 8)

    assert status_item is not None
    assert status_item.text() == "결과 없음"
    assert status_item.toolTip() == "검색 결과 없음"
