"""Settings status/diagnostic text builders (SRP: pure text computation).

Extracted from `SettingsDialog` so status rendering is testable without Qt.
"""

from datetime import datetime, timedelta
from typing import Any, Dict


def build_alert_auto_status_text(
    enabled: bool, interval_min: int, summary: Dict[str, Any]
) -> str:
    interval_min = max(5, int(interval_min))
    active_count = int(summary.get("active_count", 0) or 0)
    last_checked = str(summary.get("last_checked") or "-")
    last_error = str(summary.get("last_error") or "없음")
    next_check = "-"
    if enabled and last_checked and last_checked != "-":
        try:
            last_dt = datetime.strptime(last_checked, "%Y-%m-%d %H:%M:%S")
            next_check = (last_dt + timedelta(minutes=interval_min)).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            next_check = "계산 불가"
    elif enabled:
        next_check = f"앱 실행 중 {interval_min}분 주기"
    state = "활성" if enabled else "비활성"
    return (
        f"자동 점검: {state} | 활성 알림: {active_count}건 | "
        f"마지막 점검: {last_checked} | 다음 예정: {next_check}\n"
        f"최근 실패: {last_error}"
    )


def build_diagnostics_text(
    summary: Dict[str, Any], selector: Dict[str, Any]
) -> str:
    error_top = summary.get("top_errors", [])
    top_text = ", ".join(f"{e['error_code']}({e['count']})" for e in error_top[:3]) if error_top else "없음"
    return (
        f"성공률: {summary.get('success_rate', 0.0):.1f}% | "
        f"수동모드 전환률: {summary.get('manual_mode_rate', 0.0):.1f}%\n"
        f"총 이벤트: {summary.get('total_events', 0)} | 주요 오류코드: {top_text}\n"
        f"Selector Health: {selector.get('overall_success_rate', 0.0):.1f}% "
        f"(표본 {selector.get('sample_count', 0)}건)"
    )
