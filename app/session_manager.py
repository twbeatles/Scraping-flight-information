"""Session save/load utilities."""

import json
import logging
from datetime import datetime

import config

logger = logging.getLogger(__name__)

class SessionManager:
    """세션 저장/복원 관리자"""
    
    @staticmethod
    def _safe_serialize(obj):
        """객체를 JSON 직렬화 가능한 형태로 안전하게 변환"""
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif hasattr(obj, '__dict__'):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
        else:
            # 기본 타입은 그대로 반환, 직렬화 불가능한 경우 문자열로 변환
            try:
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                return str(obj)
    
    @staticmethod
    def save_session(filepath: str, search_params: dict, results: list) -> bool:
        """세션을 JSON 파일로 저장 (직렬화 검증 포함)"""
        try:
            # 결과 데이터를 안전하게 직렬화
            serialized_results = []
            for r in results:
                try:
                    serialized = SessionManager._safe_serialize(r)
                    # 직렬화 가능 여부 사전 검증
                    json.dumps(serialized)
                    serialized_results.append(serialized)
                except (TypeError, ValueError) as e:
                    logger.warning(f"결과 직렬화 실패, 건너뜀: {e}")
                    continue
            
            session_data = {
                "schema_version": config.SEARCH_PARAMS_SCHEMA_VERSION,
                "saved_at": datetime.now().isoformat(),
                "search_params": config.normalize_search_params(search_params),
                "results": serialized_results
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logging.error(f"Session save error: {e}")
            return False
    
    @staticmethod
    def load_session(filepath: str) -> tuple:
        """저장된 세션 로드, (params, results, saved_at) 반환"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 결과를 FlightResult 객체로 변환
            from scraper_v2 import FlightResult
            results = []
            for r in data.get("results", []):
                flight = FlightResult(
                    airline=r.get("airline", "Unknown"),
                    price=r.get("price", 0),
                    currency=r.get("currency", "KRW"),
                    departure_time=r.get("departure_time", ""),
                    arrival_time=r.get("arrival_time", ""),
                    duration=r.get("duration", ""),
                    stops=r.get("stops", 0),
                    flight_number=r.get("flight_number", ""),
                    source=r.get("source", "Session"),
                    return_departure_time=r.get("return_departure_time", ""),
                    return_arrival_time=r.get("return_arrival_time", ""),
                    return_duration=r.get("return_duration", ""),
                    return_stops=r.get("return_stops", 0),
                    is_round_trip=r.get("is_round_trip", False),
                    outbound_price=r.get("outbound_price", 0),
                    return_price=r.get("return_price", 0),
                    return_airline=r.get("return_airline", ""),
                    confidence=float(r.get("confidence", 0.0) or 0.0),
                    extraction_source=r.get("extraction_source", ""),
                )
                results.append(flight)
            
            params = config.normalize_search_params(data.get("search_params", {}))
            return params, results, data.get("saved_at", "")
        except Exception as e:
            logging.error(f"Session load error: {e}")
            return {}, [], ""


# --- Calendar View Dialog ---

# --- Main Window ---
