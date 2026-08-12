"""Canonical domestic carrier maps for Interpark extraction."""

from __future__ import annotations

# IATA marketing code → display name (API normalization).
DOMESTIC_CARRIER_CODE_TO_NAME: dict[str, str] = {
    "KE": "대한항공",
    "OZ": "아시아나항공",
    "7C": "제주항공",
    "LJ": "진에어",
    "TW": "티웨이항공",
    "BX": "에어부산",
    "RS": "에어서울",
    "ZE": "이스타항공",
    "YP": "에어프레미아",
}

# Display-name list used by DOM scripts (substring matching on card text).
# Order is matching priority; keep stable for regression fixtures.
DOMESTIC_AIRLINE_NAMES: list[str] = [
    "대한항공",
    "아시아나",
    "제주항공",
    "진에어",
    "티웨이",
    "에어부산",
    "에어서울",
    "이스타항공",
    "하이에어",
    "에어프레미아",
    "플라이강원",
]
