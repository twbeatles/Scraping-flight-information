"""Shared GUI test doubles (extracted from test_gui_behaviors.py)."""

from PyQt6.QtWidgets import QButtonGroup, QComboBox, QDateEdit, QRadioButton, QSpinBox


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
