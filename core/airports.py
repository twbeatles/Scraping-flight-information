"""Airport, route, and airline classification constants."""

from typing import Any


AIRPORTS = {
    "ICN": "인천",
    "GMP": "김포",
    "CJU": "제주",
    "PUS": "부산 김해",
    "TAE": "대구",
    "NRT": "도쿄 나리타",
    "HND": "도쿄 하네다",
    "KIX": "오사카 간사이",
    "FUK": "후쿠오카",
    "BKK": "방콕",
    "SIN": "싱가포르",
    "HKG": "홍콩",
    "SGN": "호치민",
    "DAD": "다낭",
    "DPS": "발리 (덴파사르)",
}

DOMESTIC_AIRPORTS = {
    "ICN": "인천",
    "GMP": "김포",
    "CJU": "제주",
    "PUS": "부산 김해",
    "TAE": "대구",
    "SEL": "서울(도시)",
}
DOMESTIC_AIRPORT_CODES = set(DOMESTIC_AIRPORTS.keys())

CITY_CODES_MAP = {
    "ICN": "SEL",
    "GMP": "SEL",
    "SEL": "SEL",
    "NRT": "TYO",
    "HND": "TYO",
    "KIX": "OSA",
    "FUK": "FUK",
    "CJU": "CJU",
    "PUS": "PUS",
    "BKK": "BKK",
    "SIN": "SIN",
    "HKG": "HKG",
    "SGN": "SGN",
    "DAD": "DAD",
    "DPS": "DPS",
}

AIRLINE_CATEGORIES = {
    "LCC": [
        "진에어",
        "제주항공",
        "티웨이항공",
        "에어부산",
        "에어서울",
        "이스타항공",
        "피치항공",
        "젯스타",
        "스쿠트",
        "에어아시아",
        "세부퍼시픽",
        "비엣젯",
        "스프링항공",
        "ZipAir",
        "Air Busan",
        "Jin Air",
        "T'way",
        "Jeju Air",
    ],
    "FSC": [
        "대한항공",
        "아시아나항공",
        "일본항공",
        "전일본공수",
        "JAL",
        "ANA",
        "캐세이퍼시픽",
        "싱가포르항공",
        "타이항공",
        "베트남항공",
        "Korean Air",
        "Asiana",
        "Cathay Pacific",
        "Singapore Airlines",
    ],
}

ALL_AIRLINES = AIRLINE_CATEGORIES["LCC"] + AIRLINE_CATEGORIES["FSC"] + ["기타"]


def validate_airport_code(code: str) -> bool:
    """Return whether a value is a three-letter ASCII airport or city code."""
    if not code:
        return False
    normalized = code.strip().upper()
    return len(normalized) == 3 and normalized.isalpha() and normalized.isascii()


def _extract_airport_code(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return ""
    if validate_airport_code(text):
        return text

    code_chars: list[str] = []
    for ch in text:
        if ch.isascii() and ch.isalpha():
            code_chars.append(ch)
            if len(code_chars) == 3:
                break
        elif code_chars:
            break
    candidate = "".join(code_chars)
    return candidate if validate_airport_code(candidate) else candidate


def get_airline_category(airline_name: str) -> str:
    """Return the configured airline category for a display name."""
    airline_name = airline_name.strip()
    for category, airlines in AIRLINE_CATEGORIES.items():
        if any(
            a.lower() in airline_name.lower() or airline_name.lower() in a.lower()
            for a in airlines
        ):
            return category
    return "OTHER"
