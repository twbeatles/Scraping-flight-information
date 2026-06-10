from scraper_v2 import PlaywrightScraper
import config
import scraper_config
from core.airports import AIRPORTS as CORE_AIRPORTS
from core.preferences import PreferenceManager as CorePreferenceManager
from core.search_params import normalize_search_params as core_normalize_search_params
from scraping.domestic import combine_domestic_round_trip as domestic_combine_round_trip
from scraping.interpark.scripts import ScraperScripts as InterparkScraperScripts
from scraping.interpark.selectors import REGEX_TIME as INTERPARK_REGEX_TIME
from scraping.interpark.urls import build_interpark_search_url as interpark_build_search_url
from scraping.international.normalizer import (
    _normalize_international_api_item as direct_normalize_international_api_item,
)
from scraping.playwright_domestic import combine_domestic_round_trip
from scraping.playwright_results import (
    _normalize_international_api_item as facade_normalize_international_api_item,
)
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


def test_config_facade_still_exports_core_contracts():
    params = {"origin": "ICN", "dest": "NRT", "dep": "2026-03-01"}

    assert config.PreferenceManager is CorePreferenceManager
    assert config.AIRPORTS is CORE_AIRPORTS
    assert config.normalize_search_params(params) == core_normalize_search_params(params)
    assert config._extract_airport_code("ICN 인천") == "ICN"


def test_scraper_config_facade_still_exports_interpark_contracts():
    args = ("ICN", "NRT", "2026-03-01", "2026-03-05")

    assert scraper_config.ScraperScripts is InterparkScraperScripts
    assert scraper_config.REGEX_TIME == INTERPARK_REGEX_TIME
    assert scraper_config.build_interpark_search_url(*args) == interpark_build_search_url(*args)


def test_split_scraping_modules_keep_private_helper_compatibility():
    assert facade_normalize_international_api_item is direct_normalize_international_api_item
    assert combine_domestic_round_trip is domestic_combine_round_trip
