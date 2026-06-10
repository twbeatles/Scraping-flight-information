"""Backward-compatible script builder class for Interpark DOM automation."""

from scraping.interpark.scripts.actions import (
    get_click_flight_by_details_script,
    get_click_flight_script,
)
from scraping.interpark.scripts.domestic import (
    get_domestic_list_script,
    get_domestic_prices_script,
)
from scraping.interpark.scripts.international import (
    get_international_prices_fallback_script,
    get_international_prices_script,
)
from scraping.interpark.scripts.scroll import get_scroll_check_script


class ScraperScripts:
    get_click_flight_script = staticmethod(get_click_flight_script)
    get_domestic_list_script = staticmethod(get_domestic_list_script)
    get_domestic_prices_script = staticmethod(get_domestic_prices_script)
    get_international_prices_script = staticmethod(get_international_prices_script)
    get_click_flight_by_details_script = staticmethod(get_click_flight_by_details_script)
    get_international_prices_fallback_script = staticmethod(get_international_prices_fallback_script)
    get_scroll_check_script = staticmethod(get_scroll_check_script)


__all__ = [
    "ScraperScripts",
    "get_click_flight_by_details_script",
    "get_click_flight_script",
    "get_domestic_list_script",
    "get_domestic_prices_script",
    "get_international_prices_fallback_script",
    "get_international_prices_script",
    "get_scroll_check_script",
]
