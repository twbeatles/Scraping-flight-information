"""
Flight Bot Configuration
Shared constants and settings for scraping and GUI.
"""

import json
import os
import sys
import logging
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
    
    def __init__(self, filepath: str = None):
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
        
    def _load(self) -> Dict[str, Any]:
        """설정 파일 로드 또는 기본값 생성"""
        default_prefs = {
            "custom_presets": {},  # { "Code": "City Name" }
            "search_history": [],  # [ { "origin":..., "dest":..., "date":... } ]
            "last_search": {},     # 마지막 검색 조건
            "preferred_times": {   # 선호 시간대
                "departure_start": 0,    # 0시
                "departure_end": 24      # 24시
            },
            "saved_profiles": {},   # { "ProfileName": { search_params... } }
            "theme": "dark"         # 테마 설정 (dark/light)
        }
        
        if not os.path.exists(self.filepath):
            return default_prefs
            
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return {**default_prefs, **json.load(f)} # 병합하여 새 키 추가 대응
        except Exception as e:
            logger.warning(f"Error loading preferences: {e}")
            return default_prefs

    def save(self):
        """설정 파일 저장"""
        try:
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
        # 중복 제거 (맨 앞으로 이동)
        history = [h for h in self.preferences["search_history"] if h != search_info]
        history.insert(0, search_info)
        # 최대 20개 유지
        self.preferences["search_history"] = history[:20]
        self.save()
        
    def get_history(self) -> List[Dict[str, Any]]:
        return self.preferences["search_history"]

    # --- Profiles ---
    def save_profile(self, name: str, params: Dict[str, Any]):
        self.preferences["saved_profiles"][name] = params
        self.save()
        
    def get_profile(self, name: str) -> Dict[str, Any]:
        return self.preferences["saved_profiles"].get(name, {})
        
    def delete_profile(self, name: str):
        if name in self.preferences["saved_profiles"]:
            del self.preferences["saved_profiles"][name]
            self.save()
            
    def get_all_profiles(self) -> Dict[str, Any]:
        return self.preferences.get("saved_profiles", {})

    # --- Last Search ---
    def save_last_search(self, data: Dict[str, Any]):
        self.preferences["last_search"] = data
        self.save()
        
    def get_last_search(self) -> Dict[str, Any]:
        return self.preferences.get("last_search", {})
        
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
            
            # 현재 설정에 병합
            for key, value in imported.items():
                if key in self.preferences:
                    if isinstance(value, dict) and isinstance(self.preferences[key], dict):
                        # 딕셔너리는 깊은 병합
                        self.preferences[key].update(value)
                    elif isinstance(value, list) and isinstance(self.preferences[key], list):
                        # 리스트는 중복 제거 후 병합
                        existing = self.preferences[key]
                        for item in value:
                            if item not in existing:
                                existing.append(item)
                    else:
                        self.preferences[key] = value
                else:
                    self.preferences[key] = value
            
            self.save()
            logger.info(f"Settings imported from: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to import settings: {e}")
            return False

