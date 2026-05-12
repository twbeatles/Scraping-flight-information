"""Backward-compatible facade for application entrypoint."""

from app.main_window import MainWindow, main, MAX_PRICE_FILTER, resolve_log_level
from app.session_manager import SessionManager

__all__ = ["MainWindow", "main", "MAX_PRICE_FILTER", "SessionManager", "resolve_log_level"]

if __name__ == "__main__":
    main()
