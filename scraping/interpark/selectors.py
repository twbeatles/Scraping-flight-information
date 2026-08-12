"""DOM wait selectors and regex patterns for Interpark pages."""

# Ordered by live-site hit reliability (2026-08 audit).
DOMESTIC_WAIT_SELECTORS = [
    'button:has-text("원")',
    r"text=/\d{1,3}(,\d{3})+\s*원/",
]
INTERNATIONAL_WAIT_SELECTORS = [
    "li[data-index]",
    r"text=/\d{1,3}(,\d{3})+\s*원/",
    "div[data-index]",
]

# Primary scopes for DOM extraction (narrow first, then page-wide fallback).
DOMESTIC_RESULT_ROOT_SELECTORS = (
    "main",
    '[class*="result"]',
    '[class*="Result"]',
    '[class*="list"]',
    "section",
)
DOMESTIC_RESULT_ITEM_SELECTORS = ("button",)
INTERNATIONAL_RESULT_CARD_SELECTORS = (
    "li[data-index]",
    "div[data-index]",
)

REGEX_TIME = r"(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})"
REGEX_PRICE = r"(?:^|[^\d,])(\d{1,3}(?:,\d{3}){1,2})\s*원"
REGEX_STOPS = r"(\d)회\s*경유"
