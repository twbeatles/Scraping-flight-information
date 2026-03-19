"""
Flight Bot Configuration
Shared constants and settings for scraping and GUI.
"""

import json
import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# 공항/도시 코드 매핑 (GUI 표시용)
AIRPORTS = {
    "ICN": "인천", "GMP": "김포", "CJU": "제주", "PUS": "부산 김해",
    "TAE": "대구", "NRT": "도쿄 나리타", "HND": "도쿄 하네다",
    "KIX": "오사카 간사이", "FUK": "후쿠오카", "BKK": "방콕",
    "SIN": "싱가포르", "HKG": "홍콩", "SGN": "호치민", "DAD": "다낭",
    "DPS": "발리 (덴파사르)"
}

# 국내선 공항/도시 코드 (단일 소스)
# - 공항 코드: ICN, GMP, CJU, PUS, TAE
# - 도시 코드: SEL (서울)
DOMESTIC_AIRPORTS = {
    "ICN": "인천",
    "GMP": "김포",
    "CJU": "제주",
    "PUS": "부산 김해",
    "TAE": "대구",
    "SEL": "서울(도시)",
}
DOMESTIC_AIRPORT_CODES = set(DOMESTIC_AIRPORTS.keys())
SEARCH_PARAMS_SCHEMA_VERSION = 2
VALID_CABIN_CLASSES = {"ECONOMY", "BUSINESS", "FIRST"}

# 인터파크 검색용 도시 코드 매핑
# 입력된 공항 코드를 인터파크 시스템이 이해하는 도시 코드로 변환
CITY_CODES_MAP = {
    "ICN": "SEL", "GMP": "SEL",  # 서울 (인천/김포 -> SEL)
    "NRT": "TYO", "HND": "TYO",  # 도쿄 (나리타/하네다 -> TYO)
    "KIX": "OSA",                # 오사카
    "FUK": "FUK",                # 후쿠오카
    "CJU": "CJU",                # 제주
    "PUS": "PUS",                # 부산
    "BKK": "BKK",                # 방콕
    "SIN": "SIN",                # 싱가포르
    "HKG": "HKG",                # 홍콩
    "SGN": "SGN",                # 호치민
    "DAD": "DAD",                # 다낭
    "DPS": "DPS",                # 발리
}

# 항공사 분류 (LCC: 저비용항공 / FSC: 일반항공)
AIRLINE_CATEGORIES = {
    "LCC": [  # Low Cost Carrier
        "진에어", "제주항공", "티웨이항공", "에어부산", "에어서울", "이스타항공",
        "피치항공", "젯스타", "스쿠트", "에어아시아", "세부퍼시픽", "비엣젯",
        "스프링항공", "ZipAir", "Air Busan", "Jin Air", "T'way", "Jeju Air"
    ],
    "FSC": [  # Full Service Carrier
        "대한항공", "아시아나항공", "일본항공", "전일본공수", "JAL", "ANA",
        "캐세이퍼시픽", "싱가포르항공", "타이항공", "베트남항공",
        "Korean Air", "Asiana", "Cathay Pacific", "Singapore Airlines"
    ]
}

# 모든 알려진 항공사 목록 (필터용)
ALL_AIRLINES = AIRLINE_CATEGORIES["LCC"] + AIRLINE_CATEGORIES["FSC"] + ["기타"]


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


def normalize_search_date(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None

    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y%m%d")
        except ValueError:
            continue
    return text


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
        "cabin_class": cabin_class,
        "is_domestic": is_domestic,
    }
    timestamp = raw.get("timestamp")
    if timestamp:
        normalized["timestamp"] = str(timestamp)
    return normalized

def validate_airport_code(code: str) -> bool:
    """공항/도시 코드 유효성 검사 (3자리 영문)"""
    if not code:
        return False
    normalized = code.strip().upper()
    return len(normalized) == 3 and normalized.isalpha() and normalized.isascii()

def get_airline_category(airline_name: str) -> str:
    """항공사 이름으로 카테고리 반환"""
    airline_name = airline_name.strip()
    for category, airlines in AIRLINE_CATEGORIES.items():
        if any(a.lower() in airline_name.lower() or airline_name.lower() in a.lower() 
               for a in airlines):
            return category
    return "OTHER"


class PreferenceManager:
    """사용자 환경설정, 프리셋, 히스토리 관리자"""
    
    def __init__(self, filepath: str | None = None):
        if filepath is None:
            if getattr(sys, 'frozen', False):
                # Frozen/EXE: Use AppData
                app_data = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'FlightBot')
                os.makedirs(app_data, exist_ok=True)
                self.filepath = os.path.join(app_data, "user_preferences.json")
            else:
                # Dev: Use default local file
                self.filepath = "user_preferences.json"
        else:
            self.filepath = filepath
            
        self.preferences = self._load()

    def _default_preferences(self) -> Dict[str, Any]:
        return {
            "schema_version": SEARCH_PARAMS_SCHEMA_VERSION,
            "custom_presets": {},  # { "Code": "City Name" }
            "search_history": [],  # [ { "origin":..., "dest":..., "date":... } ]
            "last_search": {},     # 마지막 검색 조건
            "preferred_times": {   # 선호 시간대
                "departure_start": 0,    # 0시
                "departure_end": 24      # 24시
            },
            "saved_profiles": {},   # { "ProfileName": { search_params... } }
            "theme": "dark",        # 테마 설정 (dark/light)
            # 가격 알림 자동 점검 설정
            "alert_auto_check_enabled": False,
            "alert_auto_check_interval_min": 30,
            "max_results": 1000,
        }

    @staticmethod
    def _has_required_search_fields(params: Dict[str, Any]) -> bool:
        return bool(params.get("origin") and params.get("dest") and params.get("dep"))

    @staticmethod
    def _history_key(params: Dict[str, Any]) -> tuple[Any, ...]:
        return (
            params.get("origin", ""),
            params.get("dest", ""),
            params.get("dep", ""),
            params.get("ret") or "",
            int(params.get("adults", 1) or 1),
            params.get("cabin_class", "ECONOMY"),
            bool(params.get("is_domestic", False)),
        )

    def _normalize_preferences_payload(self, raw: Dict[str, Any] | None) -> Dict[str, Any]:
        default_prefs = self._default_preferences()
        prefs = dict(default_prefs)
        raw_dict = raw if isinstance(raw, dict) else {}

        for key, value in raw_dict.items():
            if key not in prefs:
                prefs[key] = value

        custom_presets = raw_dict.get("custom_presets", {})
        normalized_presets: Dict[str, str] = {}
        if isinstance(custom_presets, dict):
            for code, name in custom_presets.items():
                normalized_code = _extract_airport_code(code)
                if validate_airport_code(normalized_code):
                    normalized_presets[normalized_code] = str(name or normalized_code).strip()
        prefs["custom_presets"] = normalized_presets

        history_items: List[Dict[str, Any]] = []
        raw_history = raw_dict.get("search_history", [])
        if isinstance(raw_history, list):
            seen_keys: set[tuple[Any, ...]] = set()
            for item in raw_history:
                if not isinstance(item, dict):
                    continue
                normalized = normalize_search_params(item)
                if not self._has_required_search_fields(normalized):
                    continue
                key = self._history_key(normalized)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                history_items.append(normalized)
        prefs["search_history"] = history_items[:20]

        last_search = raw_dict.get("last_search", {})
        if isinstance(last_search, dict):
            normalized_last_search = normalize_search_params(last_search)
            prefs["last_search"] = (
                normalized_last_search if self._has_required_search_fields(normalized_last_search) else {}
            )

        profiles = raw_dict.get("saved_profiles", {})
        normalized_profiles: Dict[str, Dict[str, Any]] = {}
        if isinstance(profiles, dict):
            for name, value in profiles.items():
                if not isinstance(value, dict):
                    continue
                normalized = normalize_search_params(value)
                if self._has_required_search_fields(normalized):
                    normalized_profiles[str(name)] = normalized
        prefs["saved_profiles"] = normalized_profiles

        preferred_times = raw_dict.get("preferred_times", {})
        if isinstance(preferred_times, dict):
            try:
                start = int(preferred_times.get("departure_start", 0))
            except Exception:
                start = 0
            try:
                end = int(preferred_times.get("departure_end", 24))
            except Exception:
                end = 24
            prefs["preferred_times"] = {
                "departure_start": max(0, min(start, 23)),
                "departure_end": max(1, min(end, 24)),
            }

        theme = str(raw_dict.get("theme", default_prefs["theme"]) or default_prefs["theme"]).lower()
        prefs["theme"] = theme if theme in {"dark", "light"} else default_prefs["theme"]

        try:
            max_results = int(raw_dict.get("max_results", default_prefs["max_results"]) or default_prefs["max_results"])
        except Exception:
            max_results = default_prefs["max_results"]
        prefs["max_results"] = max(50, min(max_results, 2000))

        prefs["alert_auto_check_enabled"] = _coerce_bool(
            raw_dict.get("alert_auto_check_enabled", default_prefs["alert_auto_check_enabled"]),
            default_prefs["alert_auto_check_enabled"],
        )
        try:
            interval_min = int(
                raw_dict.get("alert_auto_check_interval_min", default_prefs["alert_auto_check_interval_min"])
                or default_prefs["alert_auto_check_interval_min"]
            )
        except Exception:
            interval_min = default_prefs["alert_auto_check_interval_min"]
        prefs["alert_auto_check_interval_min"] = max(5, min(interval_min, 1440))
        prefs["schema_version"] = SEARCH_PARAMS_SCHEMA_VERSION
        return prefs
        
    def _load(self) -> Dict[str, Any]:
        """설정 파일 로드 또는 기본값 생성"""
        default_prefs = self._default_preferences()
        
        if not os.path.exists(self.filepath):
            return default_prefs
            
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return self._normalize_preferences_payload(json.load(f))
        except Exception as e:
            logger.warning(f"Error loading preferences: {e}")
            return default_prefs

    def save(self):
        """설정 파일 저장"""
        try:
            self.preferences = self._normalize_preferences_payload(self.preferences)
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.preferences, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.warning(f"Error saving preferences: {e}")

    # --- Presets ---
    def add_preset(self, code: str, name: str):
        self.preferences["custom_presets"][code] = name
        self.save()
        
    def remove_preset(self, code: str):
        if code in self.preferences["custom_presets"]:
            del self.preferences["custom_presets"][code]
            self.save()
            
    def get_all_presets(self) -> Dict[str, str]:
        # 기본 AIRPORTS와 사용자 프리셋 병합
        return {**AIRPORTS, **self.preferences.get("custom_presets", {})}

    # --- History ---
    def add_history(self, search_info: Dict[str, Any]):
        normalized = normalize_search_params(search_info)
        if not self._has_required_search_fields(normalized):
            return

        history = []
        new_key = self._history_key(normalized)
        for item in self.preferences["search_history"]:
            if self._history_key(item) != new_key:
                history.append(item)
        history.insert(0, normalized)
        # 최대 20개 유지
        self.preferences["search_history"] = history[:20]
        self.save()
        
    def get_history(self) -> List[Dict[str, Any]]:
        return self.preferences["search_history"]

    # --- Profiles ---
    def save_profile(self, name: str, params: Dict[str, Any]):
        normalized = normalize_search_params(params)
        if not self._has_required_search_fields(normalized):
            return
        self.preferences["saved_profiles"][name] = normalized
        self.save()
        
    def get_profile(self, name: str) -> Dict[str, Any]:
        value = self.preferences["saved_profiles"].get(name, {})
        return normalize_search_params(value) if isinstance(value, dict) else {}
        
    def delete_profile(self, name: str):
        if name in self.preferences["saved_profiles"]:
            del self.preferences["saved_profiles"][name]
            self.save()
            
    def get_all_profiles(self) -> Dict[str, Any]:
        profiles = self.preferences.get("saved_profiles", {})
        if not isinstance(profiles, dict):
            return {}
        return {
            str(name): normalize_search_params(value)
            for name, value in profiles.items()
            if isinstance(value, dict)
        }

    # --- Last Search ---
    def save_last_search(self, data: Dict[str, Any]):
        normalized = normalize_search_params(data)
        self.preferences["last_search"] = (
            normalized if self._has_required_search_fields(normalized) else {}
        )
        self.save()
        
    def get_last_search(self) -> Dict[str, Any]:
        value = self.preferences.get("last_search", {})
        return normalize_search_params(value) if isinstance(value, dict) else {}
        
    # --- Preferred Time ---
    def set_preferred_time(self, start: int, end: int):
        self.preferences["preferred_times"] = {"departure_start": start, "departure_end": end}
        self.save()
        
    def get_preferred_time(self) -> Dict[str, int]:
        return self.preferences.get("preferred_times", {"departure_start": 0, "departure_end": 24})

    # --- Max Results ---
    def set_max_results(self, limit: int):
        self.preferences["max_results"] = limit
        self.save()

    def get_max_results(self) -> int:
        return self.preferences.get("max_results", 1000)

    # --- Theme ---
    def get_theme(self) -> str:
        """테마 설정 반환 ('dark' 또는 'light')"""
        return self.preferences.get("theme", "dark")
    
    def set_theme(self, theme: str):
        """테마 설정 저장"""
        if theme in ("dark", "light"):
            self.preferences["theme"] = theme
            self.save()

    # --- Alert Auto Check ---
    def set_alert_auto_check(self, enabled: bool, interval_min: int):
        """가격 알림 자동 점검 설정 저장"""
        safe_interval = max(5, min(int(interval_min), 1440))
        self.preferences["alert_auto_check_enabled"] = bool(enabled)
        self.preferences["alert_auto_check_interval_min"] = safe_interval
        self.save()

    def get_alert_auto_check(self) -> Dict[str, Any]:
        """가격 알림 자동 점검 설정 반환"""
        raw_interval = self.preferences.get("alert_auto_check_interval_min", 30)
        try:
            interval_min = int(raw_interval)
        except Exception:
            interval_min = 30
        return {
            "enabled": bool(self.preferences.get("alert_auto_check_enabled", False)),
            "interval_min": max(5, min(interval_min, 1440)),
        }

    # --- Export/Import Settings ---
    def export_all_settings(self, filepath: str) -> bool:
        """모든 설정을 JSON 파일로 내보내기
        
        Args:
            filepath: 저장할 파일 경로
        
        Returns:
            성공 여부
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.preferences, f, ensure_ascii=False, indent=4)
            logger.info(f"Settings exported to: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to export settings: {e}")
            return False
    
    def import_settings(self, filepath: str) -> bool:
        """JSON 파일에서 설정 가져오기 (현재 설정에 병합)
        
        Args:
            filepath: 불러올 파일 경로
        
        Returns:
            성공 여부
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                imported = json.load(f)

            if not isinstance(imported, dict):
                raise ValueError("Settings payload must be a JSON object")

            merged = dict(self.preferences)
            imported_presets = imported.get("custom_presets")
            if isinstance(imported_presets, dict):
                merged["custom_presets"] = {**self.preferences.get("custom_presets", {}), **imported_presets}

            imported_profiles = imported.get("saved_profiles")
            if isinstance(imported_profiles, dict):
                merged["saved_profiles"] = {**self.preferences.get("saved_profiles", {}), **imported_profiles}

            imported_last_search = imported.get("last_search")
            if isinstance(imported_last_search, dict):
                merged["last_search"] = imported_last_search

            imported_history = imported.get("search_history")
            if isinstance(imported_history, list):
                merged["search_history"] = imported_history + list(self.preferences.get("search_history", []))

            for key, value in imported.items():
                if key in {"custom_presets", "saved_profiles", "last_search", "search_history"}:
                    continue
                merged[key] = value

            self.preferences = self._normalize_preferences_payload(merged)
            self.save()
            logger.info(f"Settings imported from: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to import settings: {e}")
            return False

