"""DOM wait selectors and regex patterns for Interpark pages."""

DOMESTIC_WAIT_SELECTORS = [
    'button:has-text("원")',
    r"text=/\d{1,3}(,\d{3})+\s*원/",
    'button:has-text("직항")',
]
INTERNATIONAL_WAIT_SELECTORS = [
    "li[data-index]",
    "div[data-index]",
    'li[class*="result"]',
    r"text=/\d{1,3}(,\d{3})+\s*원/",
]

REGEX_TIME = r"(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})"
REGEX_PRICE = r"(?:^|[^\d,])(\d{1,3}(?:,\d{3}){1,2})\s*원"
REGEX_STOPS = r"(\d)회\s*경유"
