import subprocess
import sys


def test_live_smoke_script_help_runs_from_repo_root():
    completed = subprocess.run(
        [sys.executable, "scripts/live_smoke_search.py", "--help"],
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert completed.returncode == 0
    assert "Run manual live smoke searches." in completed.stdout
