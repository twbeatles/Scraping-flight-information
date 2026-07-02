"""Search parameter normalization and route inference helpers."""

from datetime import datetime
from typing import Any, Dict

from core.airports import DOMESTIC_AIRPORT_CODES, _extract_airport_code


SEARCH_PARAMS_SCHEMA_VERSION = 2
VALID_CABIN_CLASSES = {"ECONOMY", "BUSINESS", "FIRST"}


def normalize_search_date(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None

    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y%m%d")
        except ValueError:
            continue
    return None


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    return default


def infer_is_domestic_route(origin: Any, dest: Any) -> bool:
    origin_code = _extract_airport_code(origin)
    dest_code = _extract_airport_code(dest)
    return origin_code in DOMESTIC_AIRPORT_CODES and dest_code in DOMESTIC_AIRPORT_CODES


def normalize_search_params(params: Dict[str, Any] | None) -> Dict[str, Any]:
    raw = params if isinstance(params, dict) else {}

    origin = _extract_airport_code(raw.get("origin", ""))
    dest = _extract_airport_code(raw.get("dest", raw.get("destination", "")))
    dep = normalize_search_date(raw.get("dep", raw.get("departure_date", raw.get("dep_date"))))
    ret = normalize_search_date(raw.get("ret", raw.get("return_date", raw.get("ret_date"))))

    try:
        adults = int(raw.get("adults", 1) or 1)
    except Exception:
        adults = 1
    adults = max(1, min(adults, 9))

    try:
        child = max(0, min(int(raw.get("child", 0) or 0), 9))
    except Exception:
        child = 0
    try:
        infant = max(0, min(int(raw.get("infant", 0) or 0), 9))
    except Exception:
        infant = 0

    cabin_class = str(raw.get("cabin_class", raw.get("cabin", "ECONOMY")) or "ECONOMY").upper()
    if cabin_class not in VALID_CABIN_CLASSES:
        cabin_class = "ECONOMY"

    inferred_domestic = infer_is_domestic_route(origin, dest)
    if "is_domestic" in raw and raw.get("is_domestic") is not None:
        is_domestic = _coerce_bool(raw.get("is_domestic"), inferred_domestic)
    else:
        is_domestic = inferred_domestic

    normalized = {
        "origin": origin,
        "dest": dest,
        "dep": dep or "",
        "ret": ret,
        "adults": adults,
        "child": child,
        "infant": infant,
        "cabin_class": cabin_class,
        "is_domestic": is_domestic,
    }
    timestamp = raw.get("timestamp")
    if timestamp:
        normalized["timestamp"] = str(timestamp)
    return normalized
