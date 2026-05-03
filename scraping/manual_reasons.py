"""User-facing labels for scraper manual/fallback reasons."""

from __future__ import annotations


MANUAL_REASON_LABELS = {
    "international_api_failed": "국제선 API 응답 변경 또는 추출 실패",
    "international_api_key_missing": "국제선 검색 key 탐지 실패",
    "international_api_status_failed": "국제선 API 상태 확인 실패",
    "international_api_http_failed": "국제선 API HTTP 오류",
    "international_api_status_timeout": "국제선 API 응답 대기 시간 초과",
    "international_api_result_fetch_failed": "국제선 결과 API 호출 실패",
    "international_api_payload_mismatch": "국제선 API 응답 형식 변경 의심",
    "international_api_exception": "국제선 API 처리 중 예외 발생",
    "domestic_api_failed": "국내선 API 응답 변경 또는 추출 실패",
    "domestic_api_key_missing": "국내선 검색 key 탐지 실패",
    "domestic_api_result_fetch_failed": "국내선 결과 API 호출 실패",
    "domestic_api_payload_mismatch": "국내선 API 응답 형식 변경 의심",
    "domestic_return_key_missing": "국내선 귀국편 key 탐지 실패",
    "dom_fallback_gap_risk": "화면 결과 일부 누락 가능성 감지",
}


def describe_manual_reason(reason: str) -> str:
    """Return a stable Korean label while preserving unknown reason codes."""

    reason = str(reason or "").strip()
    if not reason:
        return "자동 추출 실패"
    return MANUAL_REASON_LABELS.get(reason, reason)
