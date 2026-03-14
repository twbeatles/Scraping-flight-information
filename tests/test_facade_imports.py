from scraper_v2 import PlaywrightScraper
from ui.components import SearchPanel
from ui.components_search_panel import SearchPanel as SearchPanelDirect
from ui.dialogs import (
    DateRangeDialog,
    DateRangeResultDialog,
    MultiDestDialog,
    MultiDestResultDialog,
    PriceAlertDialog,
    SettingsDialog,
    ShortcutsDialog,
)
from ui.styles import DARK_THEME, LIGHT_THEME, MODERN_THEME


def test_scraper_facade_still_exports_playwright_scraper():
    assert PlaywrightScraper.__name__ == "PlaywrightScraper"


def test_ui_components_facade_still_exports_search_panel():
    assert SearchPanel is SearchPanelDirect


def test_ui_dialogs_facade_still_exports_split_dialogs():
    assert MultiDestDialog.__name__ == "MultiDestDialog"
    assert DateRangeDialog.__name__ == "DateRangeDialog"
    assert MultiDestResultDialog.__name__ == "MultiDestResultDialog"
    assert DateRangeResultDialog.__name__ == "DateRangeResultDialog"
    assert ShortcutsDialog.__name__ == "ShortcutsDialog"
    assert PriceAlertDialog.__name__ == "PriceAlertDialog"
    assert SettingsDialog.__name__ == "SettingsDialog"


def test_styles_facade_keeps_theme_aliases():
    assert isinstance(DARK_THEME, str) and DARK_THEME
    assert isinstance(LIGHT_THEME, str) and LIGHT_THEME
    assert MODERN_THEME == DARK_THEME
