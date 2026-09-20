"""Lock the module -> package split contracts (facades + re-exported names).

Each split keeps its original import path working; this file guards that
no previously importable name goes missing after refactoring.
"""

import importlib

from core.preferences import (
    HistoryMixin,
    PreferenceManager,
    PresetsMixin,
    ProfilesMixin,
    SettingsMixin,
)


def test_preferences_manager_composes_concern_mixins():
    assert issubclass(PreferenceManager, PresetsMixin)
    assert issubclass(PreferenceManager, HistoryMixin)
    assert issubclass(PreferenceManager, ProfilesMixin)
    assert issubclass(PreferenceManager, SettingsMixin)


def test_playwright_api_facade_exports_all_helpers():
    module = importlib.import_module("scraping.playwright_api")
    expected = {
        "page_fetch_json",
        "_maybe_cache_search_key_from_fetch",
        "get_api_meta",
        "_record_api_meta",
        "_sanitize_resource_url",
        "_ensure_search_key_cache",
        "cache_search_key",
        "drop_cached_search_key",
        "get_cached_search_keys",
        "extract_search_key_from_url",
        "extract_search_key_from_payload",
        "find_search_keys",
        "find_search_keys_from_performance",
        "recent_api_resource_urls",
        "resolve_search_key",
        "wait_for_search_key",
        "find_latest_search_key",
        "_normalize_exclude_keys",
        "_record_key_wait",
    }
    assert expected <= set(module.__all__)
    for name in expected:
        assert callable(getattr(module, name)), name


def test_domestic_api_facade_keeps_private_helpers():
    module = importlib.import_module("scraping.domestic.api")
    for name in (
        "extract_domestic_api_flights_data",
        "clear_domestic_api_failure_after_success",
        "_fetch_domestic_search_page",
        "_record_domestic_api_failure",
        "_normalize_domestic_api_item",
        "_extract_domestic_benefit",
        "_is_invalid_cache_search_key",
        "_refresh_domestic_search_key",
        "DOMESTIC_API_FAILURE_REASONS",
        "INVALID_CACHE_SEARCH_KEY",
        "DOMESTIC_CARRIER_NAMES",
    ):
        assert hasattr(module, name), name


def test_orchestration_submodules_importable():
    for name in ("browser", "context", "extraction", "failures", "telemetry"):
        module = importlib.import_module(f"scraping.search_flow.orchestration.{name}")
        assert module is not None
    from scraping.search_flow.orchestration import run_search

    assert callable(run_search)


def test_ui_split_packages_expose_widgets():
    from ui.components_filter_panel import FilterPanel
    from ui.components_result_table import ResultTable
    from ui.dialogs_tools_settings import SettingsDialog
    from ui.workers_parallel import (
        DateRangeWorker,
        MAX_DATE_RANGE_SEARCHES,
        MAX_PARALLEL_WORKERS,
        MultiSearchWorker,
    )

    assert FilterPanel.__name__ == "FilterPanel"
    assert ResultTable.__name__ == "ResultTable"
    assert SettingsDialog.__name__ == "SettingsDialog"
    assert MultiSearchWorker.__name__ == "MultiSearchWorker"
    assert DateRangeWorker.__name__ == "DateRangeWorker"
    assert MAX_PARALLEL_WORKERS == 2
    assert MAX_DATE_RANGE_SEARCHES == 30


def test_style_section_modules_compose_themes():
    from ui import styles_dark, styles_light
    from ui.styles import DARK_THEME, LIGHT_THEME

    assert styles_dark.DARK_THEME == DARK_THEME
    assert styles_light.LIGHT_THEME == LIGHT_THEME
    for package, theme in ((styles_dark, DARK_THEME), (styles_light, LIGHT_THEME)):
        assert isinstance(theme, str) and len(theme) > 1000
        for name in package.__all__:
            if name in {"DARK_THEME", "LIGHT_THEME"}:
                continue
            section = getattr(package, name)
            assert isinstance(section, str) and section
            assert section in theme, name
