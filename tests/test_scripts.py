import subprocess
import sys

from scripts.live_smoke_search import _violates_smoke_thresholds


def test_live_smoke_script_help_runs_from_repo_root():
    completed = subprocess.run(
        [sys.executable, "scripts/live_smoke_search.py", "--help"],
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert completed.returncode == 0
    assert "Run manual live smoke searches." in completed.stdout


def test_live_smoke_threshold_detects_cap_and_stale_manual_reason():
    summary = {
        "route": "ICN->NRT",
        "result_count": 1,
        "manual_reason": "international_api_failed",
        "cleanup_ok": True,
        "metrics": {"fetched_pages": 51},
    }

    assert _violates_smoke_thresholds(summary, page_cap=50) is True


def test_live_smoke_threshold_accepts_clean_summary():
    summary = {
        "route": "ICN->NRT",
        "result_count": 1,
        "manual_reason": "",
        "cleanup_ok": True,
        "metrics": {"fetched_pages": 50},
    }

    assert _violates_smoke_thresholds(summary, page_cap=50) is False
