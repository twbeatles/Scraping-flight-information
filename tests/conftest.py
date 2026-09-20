import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_PYQT_TEST_FILES = {
    "test_dialog_validations.py",
    "test_facade_imports.py",
    "test_gui_guards.py",
    "test_gui_search_panel.py",
    "test_gui_results.py",
    "test_gui_alerts_export.py",
    "test_parallel_workers.py",
    "test_domestic_api.py",
    "test_international_api.py",
    "test_searcher_core.py",
    "test_search_urls.py",
}

try:
    from PyQt6.QtWidgets import QApplication as _QApplication
except ImportError as exc:
    _QApplication = None
    _PYQT_IMPORT_ERROR = exc
else:
    _PYQT_IMPORT_ERROR = None


def pytest_ignore_collect(collection_path, config):
    del config
    if _PYQT_IMPORT_ERROR is None:
        return False
    return collection_path.name in _PYQT_TEST_FILES


def pytest_report_header(config):
    del config
    if _PYQT_IMPORT_ERROR is None:
        return None
    return f"PyQt unavailable, skipping GUI-dependent tests: {_PYQT_IMPORT_ERROR}"


@pytest.fixture(scope="session")
def qapp():
    if _PYQT_IMPORT_ERROR is not None or _QApplication is None:
        pytest.skip(f"PyQt unavailable: {_PYQT_IMPORT_ERROR}")
    app = _QApplication.instance()
    if app is None:
        app = _QApplication([])
    return app
