"""검색 입력·가격 결과 조회 UX (specs/001-search-result-ux) 회귀 테스트."""

from typing import Any

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from app.mainwindow.filtering import build_result_summary, lowest_effective_price
from gui_v2 import MainWindow
from scraper_v2 import FlightResult
from ui.components import FilterPanel, ResultTable, SearchPanel
from ui.components_filter_panel import DEFAULT_FILTERS, UNLIMITED_STOPS
from ui.components_result_table.context_menu import format_row_info
from ui.components_result_table.formatting import duration_to_minutes
from ui.components_result_table.table_config import (
    COL_DURATION,
    COL_PRICE,
    COL_RET_STOPS,
    COL_SEATS,
    COL_STOPS,
    COLUMN_LABELS,
)
from ui.search_panel_shared import SEARCH_BUTTON_TEXT


class _Prefs:
    def __init__(self):
        self._profiles = {}
        self._presets = {}

    def get_all_profiles(self):
        return self._profiles

    def get_all_presets(self):
        return self._presets

    def add_preset(self, code, name):
        self._presets[code] = name

    def remove_preset(self, code):
        self._presets.pop(code, None)

    def save_profile(self, name, params):
        self._profiles[name] = params

    def get_profile(self, name):
        return self._profiles.get(name, {})

    def get_preferred_time(self):
        return {"departure_start": 0, "departure_end": 24}


class _Recorder:
    def __init__(self):
        self.messages = []

    def showMessage(self, msg):
        self.messages.append(msg)

    def append_log(self, msg):
        self.messages.append(msg)

    def setText(self, msg):
        self.messages.append(msg)


class _FilterContext:
    """`MainWindow._apply_filter`를 실제 ResultTable과 함께 돌리는 최소 컨텍스트."""

    def __init__(self, results, params=None):
        self.all_results = results
        self.table = ResultTable()
        self.current_search_params = params or {}
        self.result_summary_label = _Recorder()
        self.log_viewer = _Recorder()
        self._status = _Recorder()
        self._last_filter_log_msg = ""
        self._last_filter_log_ts = 0.0
        self.results: Any = list(results)
        self.search_panel: Any = None
        self.progress_bar: Any = None
        self.tabs: Any = None

    def statusBar(self):
        return self._status

    def _append_filter_log(self, message):
        MainWindow._append_filter_log(self, message)

    def _update_result_summary(self, shown):
        MainWindow._update_result_summary(self, shown)


def _flight(airline, price, **kwargs):
    kwargs.setdefault("departure_time", "10:00")
    kwargs.setdefault("arrival_time", "12:00")
    return FlightResult(airline=airline, price=price, **kwargs)


def _cell(table, row, col):
    item = table.item(row, col)
    assert item is not None
    return item.text()


# --- US1: 가격 기준 통일 ---


def test_price_column_sorts_numerically_not_lexically(qapp):
    del qapp
    table = ResultTable()
    table.update_data([_flight("Big", 1_200_000), _flight("Small", 200_000), _flight("Mid", 990_000)])

    table.sortItems(COL_PRICE, Qt.SortOrder.AscendingOrder)
    assert [_cell(table, row, 0) for row in range(3)] == ["Small", "Mid", "Big"]

    table.sortItems(COL_PRICE, Qt.SortOrder.DescendingOrder)
    assert [_cell(table, row, 0) for row in range(3)] == ["Big", "Mid", "Small"]


def test_default_order_puts_lowest_effective_price_first_with_badge(qapp):
    del qapp
    table = ResultTable()
    table.update_data(
        [
            _flight("Base", 120_000),
            _flight("Benefit", 150_000, benefit_price=110_000),
        ]
    )

    assert _cell(table, 0, 0) == "Benefit"
    price_text = _cell(table, 0, COL_PRICE)
    assert price_text.startswith("🏆 110,000원")
    assert "기본 150,000" in price_text
    assert "🏆" not in _cell(table, 1, COL_PRICE)


def test_unknown_price_sorts_last_and_is_not_marked_cheapest(qapp):
    del qapp
    table = ResultTable()
    table.update_data([_flight("Unknown", 0), _flight("Known", 90_000)])

    assert _cell(table, 0, 0) == "Known"
    assert "🏆" in _cell(table, 0, COL_PRICE)
    assert "🏆" not in _cell(table, 1, COL_PRICE)


def test_stops_seats_and_duration_columns_sort_numerically(qapp):
    del qapp
    table = ResultTable()
    table.update_data(
        [
            _flight("A", 100_000, stops=10, seat_availability=9, duration="10시간 05분"),
            _flight("B", 100_000, stops=2, seat_availability=12, duration="02시간 30분"),
            _flight("C", 100_000, stops=0, seat_availability=0, duration=""),
        ]
    )

    table.sortItems(COL_STOPS, Qt.SortOrder.AscendingOrder)
    assert [_cell(table, row, 0) for row in range(3)] == ["C", "B", "A"]

    # 잔여석 미확인(0)과 소요시간 미확인은 오름차순에서 맨 뒤
    table.sortItems(COL_SEATS, Qt.SortOrder.AscendingOrder)
    assert [_cell(table, row, 0) for row in range(3)] == ["A", "B", "C"]

    table.sortItems(COL_DURATION, Qt.SortOrder.AscendingOrder)
    assert [_cell(table, row, 0) for row in range(3)] == ["B", "A", "C"]


def test_duration_to_minutes_handles_known_formats():
    assert duration_to_minutes("02시간 30분") == 150
    assert duration_to_minutes("45분") == 45
    assert duration_to_minutes("1h 5m") == 65
    assert duration_to_minutes("02:10") == 130
    assert duration_to_minutes("70") == 70
    assert duration_to_minutes("") == 0
    assert duration_to_minutes("알 수 없음") == 0


def test_price_filter_uses_effective_price(qapp):
    del qapp
    ctx = _FilterContext(
        [
            _flight("Base", 120_000),
            _flight("Benefit", 150_000, benefit_price=110_000),
        ]
    )

    MainWindow._apply_filter(ctx, {**DEFAULT_FILTERS, "max_price": 110_000})

    assert [f.airline for f in ctx.table.results_data] == ["Benefit"]


def test_apply_filter_orders_rows_by_effective_price(qapp):
    del qapp
    ctx = _FilterContext(
        [
            _flight("Base", 120_000),
            _flight("NoPrice", 0),
            _flight("Benefit", 150_000, benefit_price=110_000),
        ]
    )

    MainWindow._apply_filter(ctx, dict(DEFAULT_FILTERS))

    assert [f.airline for f in ctx.table.results_data] == ["Benefit", "Base", "NoPrice"]
    assert lowest_effective_price(ctx.all_results) == 110_000


# --- US2: 결과 요약과 표 구성 ---


def test_result_summary_describes_query_counts_and_lowest_price():
    params = {
        "origin": "ICN",
        "dest": "NRT",
        "dep": "20261019",
        "ret": "20261022",
        "adults": 2,
        "child": 1,
        "infant": 0,
        "cabin_class": "ECONOMY",
    }
    shown = [_flight("A", 213_000), _flight("B", 250_000, benefit_price=199_000)]

    text = build_result_summary(params, shown, 124)

    assert "ICN → NRT" in text
    assert "10/19 ~ 10/22 왕복" in text
    assert "성인 2 · 소아 1" in text
    assert "유아" not in text
    assert "2건 표시 / 전체 124건" in text
    assert "최저 199,000원" in text
    assert "⚠️" not in text


def test_result_summary_flags_truncation_and_one_way():
    text = build_result_summary(
        {"origin": "GMP", "dest": "CJU", "dep": "20261101", "ret": None, "adults": 1},
        [_flight("A", 50_000)],
        1,
        truncated=True,
    )

    assert "11/1 편도" in text
    assert "1건" in text and "전체" not in text
    assert "일부 결과가 빠졌을 수 있습니다" in text


def test_result_summary_tolerates_missing_params():
    assert "결과 없음" in build_result_summary(None, [], 0)


def test_filtered_empty_table_explains_filter_not_search(qapp):
    del qapp
    ctx = _FilterContext([_flight("A", 300_000), _flight("B", 400_000)])

    MainWindow._apply_filter(ctx, {**DEFAULT_FILTERS, "max_price": 100_000})

    placeholder = _cell(ctx.table, 0, 0)
    assert "필터 조건에 맞는 결과가 없습니다" in placeholder
    assert "전체 2건" in placeholder
    assert "0건 표시 / 전체 2건" in ctx.result_summary_label.messages[-1]

    # 필터를 풀면 기본 문구로 되돌아가야 한다
    MainWindow._apply_filter(ctx, dict(DEFAULT_FILTERS))
    ctx.table.update_data([])
    assert "검색 조건을 확인해주세요" in _cell(ctx.table, 0, 0)


def test_filter_status_message_uses_user_facing_labels(qapp):
    del qapp
    ctx = _FilterContext([_flight("A", 300_000)])

    MainWindow._apply_filter(ctx, dict(DEFAULT_FILTERS))

    message = ctx._status.messages[-1]
    assert "항공사: 전체" in message
    assert "경유: 전체" in message
    assert "ALL" not in message


def test_empty_search_clears_previous_results(qapp, monkeypatch):
    del qapp
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.StandardButton.Ok)

    class _Panel:
        def set_searching(self, _):
            return None

    class _Progress:
        def setRange(self, *_):
            return None

        def setValue(self, _):
            return None

        def setFormat(self, _):
            return None

    class _Tabs:
        def setCurrentIndex(self, _):
            return None

    ctx = _FilterContext([_flight("Old", 100_000)], {"origin": "ICN", "dest": "NRT"})
    ctx.search_panel = _Panel()
    ctx.progress_bar = _Progress()
    ctx.tabs = _Tabs()

    MainWindow._search_finished(ctx, [])

    assert ctx.all_results == []
    assert "결과 없음" in ctx.result_summary_label.messages[-1]
    # 이전 결과가 없으므로 필터를 다시 적용해도 표가 채워지지 않는다
    MainWindow._apply_filter(ctx, dict(DEFAULT_FILTERS))
    assert ctx.table.results_data == []


def test_column_headers_distinguish_outbound_and_return_stops():
    assert COLUMN_LABELS[COL_STOPS] == "가는편 경유"
    assert COLUMN_LABELS[COL_RET_STOPS] == "오는편 경유"
    assert COLUMN_LABELS[COL_DURATION] == "소요시간"
    assert len(set(COLUMN_LABELS)) == len(COLUMN_LABELS)


def test_row_copy_includes_return_leg_and_effective_price(qapp):
    del qapp
    flight = _flight(
        "제주항공",
        150_000,
        benefit_price=110_000,
        is_round_trip=True,
        return_airline="진에어",
        return_departure_time="18:00",
        return_arrival_time="19:10",
    )

    info = format_row_info(flight)

    assert "제주항공 + 진에어" in info
    assert "110,000원 (기본 150,000원)" in info
    assert "가는편 10:00→12:00" in info
    assert "오는편 18:00→19:10" in info

    table = ResultTable()
    table.update_data([flight])
    table._copy_row_info(0)
    clipboard = QApplication.clipboard()
    assert clipboard is not None and clipboard.text() == info


# --- US3: 필터 단순화 ---


def test_stops_combo_derives_legacy_filter_keys(qapp):
    del qapp
    panel = FilterPanel()

    default = panel.get_current_filters()
    assert default == DEFAULT_FILTERS
    assert default["max_stops"] == UNLIMITED_STOPS

    panel.cb_stops.setCurrentIndex(panel.cb_stops.findData(0))
    direct = panel.get_current_filters()
    assert (direct["direct_only"], direct["include_layover"], direct["max_stops"]) == (True, False, 0)

    panel.cb_stops.setCurrentIndex(panel.cb_stops.findData(1))
    one_stop = panel.get_current_filters()
    assert (one_stop["direct_only"], one_stop["include_layover"], one_stop["max_stops"]) == (False, True, 1)

    panel._reset_filters()
    assert panel.get_current_filters() == DEFAULT_FILTERS


def test_stops_filter_limits_rows(qapp):
    del qapp
    ctx = _FilterContext(
        [
            _flight("Direct", 300_000, stops=0),
            _flight("One", 200_000, stops=1),
            _flight("Four", 100_000, stops=4),
        ]
    )

    MainWindow._apply_filter(ctx, dict(DEFAULT_FILTERS))
    assert {f.airline for f in ctx.table.results_data} == {"Direct", "One", "Four"}

    panel = FilterPanel()
    panel.cb_stops.setCurrentIndex(panel.cb_stops.findData(1))
    MainWindow._apply_filter(ctx, panel.get_current_filters())
    assert [f.airline for f in ctx.table.results_data] == ["One", "Direct"]

    panel.cb_stops.setCurrentIndex(panel.cb_stops.findData(0))
    MainWindow._apply_filter(ctx, panel.get_current_filters())
    assert [f.airline for f in ctx.table.results_data] == ["Direct"]


def test_legacy_filter_dict_without_new_keys_still_works(qapp):
    del qapp
    ctx = _FilterContext([_flight("Direct", 300_000, stops=0), _flight("One", 200_000, stops=1)])

    MainWindow._apply_filter(ctx, {"direct_only": True, "start_time": 0, "end_time": 24})

    assert [f.airline for f in ctx.table.results_data] == ["Direct"]


def test_filter_departure_time_initialises_without_emitting(qapp):
    del qapp
    panel = FilterPanel()
    emitted = []
    panel.filter_changed.connect(emitted.append)

    panel.set_departure_time_range(9, 18)

    filters = panel.get_current_filters()
    assert (filters["start_time"], filters["end_time"]) == (9, 18)
    assert emitted == []

    panel.set_departure_time_range(30, 5)
    filters = panel.get_current_filters()
    assert 0 <= filters["start_time"] < filters["end_time"] <= 24


def test_search_panel_no_longer_has_inert_time_controls(qapp):
    del qapp
    panel = SearchPanel(_Prefs())

    assert not hasattr(panel, "spin_time_start")
    assert not hasattr(panel, "spin_time_end")


# --- US4: 입력 편의 ---


def test_swap_button_exchanges_origin_and_destination(qapp):
    del qapp
    panel = SearchPanel(_Prefs())
    panel.cb_origin.setCurrentIndex(panel.cb_origin.findData("ICN"))
    panel.cb_dest.setCurrentIndex(panel.cb_dest.findData("NRT"))

    panel.btn_swap.click()

    params = panel.get_search_params()
    assert (params["origin"], params["dest"]) == ("NRT", "ICN")


def test_swap_keeps_manually_typed_code(qapp):
    del qapp
    panel = SearchPanel(_Prefs())
    panel.cb_origin.setCurrentIndex(panel.cb_origin.findData("ICN"))
    panel.cb_dest.setCurrentIndex(-1)
    panel.cb_dest.setEditText("ZZZ")

    panel._swap_airports()

    params = panel.get_search_params()
    assert (params["origin"], params["dest"]) == ("ZZZ", "ICN")


def test_return_date_follows_departure_date(qapp):
    del qapp
    panel = SearchPanel(_Prefs())
    today = QDate.currentDate()
    panel.date_dep.setDate(today.addDays(5))
    panel.date_ret.setDate(today.addDays(7))

    panel.date_dep.setDate(today.addDays(12))
    assert panel.date_ret.date() == today.addDays(12)

    # 가는 날을 앞당길 때는 오는 날을 건드리지 않는다
    panel.date_dep.setDate(today.addDays(3))
    assert panel.date_ret.date() == today.addDays(12)


def test_past_dates_cannot_be_selected(qapp):
    del qapp
    panel = SearchPanel(_Prefs())
    today = QDate.currentDate()

    panel.date_dep.setDate(today.addDays(-3))
    panel.date_ret.setDate(today.addDays(-1))

    assert panel.date_dep.date() == today
    assert panel.date_ret.date() >= today


def _capture_search(panel, monkeypatch):
    emitted = []
    warnings = []
    panel.search_requested.connect(lambda *args: emitted.append(args))
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda *args, **kwargs: warnings.append(args[2]) or QMessageBox.StandardButton.Ok,
    )
    return emitted, warnings


def test_search_blocks_more_infants_than_adults(qapp, monkeypatch):
    del qapp
    panel = SearchPanel(_Prefs())
    emitted, warnings = _capture_search(panel, monkeypatch)
    panel.spin_adults.setValue(1)
    panel.spin_infant.setValue(2)

    panel._on_search()

    assert emitted == []
    assert any("유아" in text for text in warnings)


def test_search_blocks_more_than_nine_passengers(qapp, monkeypatch):
    del qapp
    panel = SearchPanel(_Prefs())
    emitted, warnings = _capture_search(panel, monkeypatch)
    panel.spin_adults.setValue(5)
    panel.spin_child.setValue(5)

    panel._on_search()

    assert emitted == []
    assert any("최대 9명" in text for text in warnings)


def test_search_allows_valid_passenger_mix(qapp, monkeypatch):
    del qapp
    panel = SearchPanel(_Prefs())
    emitted, warnings = _capture_search(panel, monkeypatch)
    panel.spin_adults.setValue(2)
    panel.spin_child.setValue(1)
    panel.spin_infant.setValue(2)

    panel._on_search()

    assert warnings == []
    assert len(emitted) == 1


def test_search_button_text_is_stable_across_search(qapp):
    del qapp
    panel = SearchPanel(_Prefs())
    assert panel.btn_search.text() == SEARCH_BUTTON_TEXT

    panel.set_searching(True)
    assert panel.btn_search.text() != SEARCH_BUTTON_TEXT
    assert panel.btn_swap.isEnabled() is False

    panel.set_searching(False)
    assert panel.btn_search.text() == SEARCH_BUTTON_TEXT
    assert panel.btn_swap.isEnabled() is True


def test_one_way_dims_return_date_without_hardcoded_colors(qapp):
    del qapp
    panel = SearchPanel(_Prefs())

    panel.rb_oneway.setChecked(True)
    panel._toggle_return_date()
    assert panel.date_ret.isEnabled() is False
    assert panel.date_ret.styleSheet() == ""
    assert panel.date_ret.graphicsEffect() is not None

    panel.rb_round.setChecked(True)
    panel._toggle_return_date()
    assert panel.date_ret.isEnabled() is True
    assert panel.date_ret.graphicsEffect() is None
