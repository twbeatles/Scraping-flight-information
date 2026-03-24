# -*- mode: python ; coding: utf-8 -*-
"""
Flight Bot v2.5 - PyInstaller Build Spec (Standard GUI Profile)
빌드: pyinstaller --clean FlightBot_v2.5.spec
"""

block_cipher = None

excludes = [
    "matplotlib", "numpy", "pandas", "scipy", "PIL", "cv2",
    "seaborn", "plotly", "bokeh", "altair", "sympy",
    "unittest", "pytest", "nose", "pdb", "pydoc", "doctest",
    "IPython", "jupyter", "notebook", "ipykernel",
    "tkinter", "turtle", "idlelib", "turtledemo",
    "email", "xml.dom", "xml.sax", "xmlrpc",
    "distutils", "setuptools", "pkg_resources", "pip", "ensurepip",
    "lib2to3", "test", "tests",
    "flask", "django", "tornado", "aiohttp", "fastapi",
    "http.server", "ftplib", "telnetlib", "socketserver",
    "curses", "multiprocessing.popen_spawn_posix",
]

hiddenimports = [
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "playwright.sync_api",
    "playwright._impl._api_structures",
    "asyncio",
    "asyncio.windows_events",
    "asyncio.windows_utils",
    "asyncio.proactor_events",
    "asyncio.selector_events",
    "json",
    "logging",
    "sqlite3",
    "threading",
    "concurrent.futures",
    "shutil",
    "tempfile",
    # Facade modules (public import compatibility)
    "database",
    "scraper_v2",
    "ui.components",
    "ui.dialogs",
    "ui.styles",
    "ui.workers",
    # Package roots kept explicit for PyInstaller module graph stability
    "app",
    "app.mainwindow",
    "scraping",
    "storage",
    # Refactored package modules (facade-compatible split)
    "app.main_window",
    "app.session_manager",
    "app.mainwindow.shared",
    "app.mainwindow.ui_bootstrap",
    "app.mainwindow.ui_bootstrap_sections",
    "app.mainwindow.telemetry",
    "app.mainwindow.auto_alert",
    "app.mainwindow.worker_lifecycle",
    "app.mainwindow.favorites",
    "app.mainwindow.exports",
    "app.mainwindow.search_single",
    "app.mainwindow.search_multi",
    "app.mainwindow.search_date_range",
    "app.mainwindow.manual_mode",
    "app.mainwindow.filtering",
    "app.mainwindow.history",
    "app.mainwindow.session",
    "app.mainwindow.calendar",
    "app.mainwindow.app_lifecycle",
    "scraping.errors",
    "scraping.models",
    "scraping.playwright_scraper",
    "scraping.playwright_browser",
    "scraping.playwright_search",
    "scraping.playwright_domestic",
    "scraping.playwright_results",
    "scraping.extract_domestic",
    "scraping.extract_international",
    "scraping.searcher",
    "scraping.search_sources",
    "scraping.parallel",
    "storage.models",
    "storage.schema",
    "storage.flight_database",
    "storage.db_favorites",
    "storage.db_history_logs",
    "storage.db_telemetry",
    "storage.db_alerts",
    "storage.db_last_search",
    "ui.components_primitives",
    "ui.components_filter_panel",
    "ui.components_result_table",
    "ui.components_log_viewer",
    "ui.components_search_panel",
    "ui.search_panel_shared",
    "ui.search_panel_build",
    "ui.search_panel_actions",
    "ui.search_panel_state",
    "ui.search_panel_params",
    "ui.search_panel_widget",
    "ui.dialogs_base",
    "ui.dialogs_calendar",
    "ui.dialogs_combination",
    "ui.dialogs_search",
    "ui.dialogs_search_multi",
    "ui.dialogs_search_date_range",
    "ui.dialogs_search_results",
    "ui.dialogs_tools",
    "ui.dialogs_tools_shortcuts",
    "ui.dialogs_tools_price_alert",
    "ui.dialogs_tools_settings",
    "ui.styles_dark",
    "ui.styles_light",
    "ui.workers_search",
    "ui.workers_parallel",
    "ui.workers_alerts",
]

a = Analysis(
    ["gui_v2.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

a.binaries = [
    b
    for b in a.binaries
    if not any(
        exclude in b[0].lower()
        for exclude in [
            "qt6quick",
            "qt6qml",
            "qt6network",
            "qt63d",
            "qt6multimedia",
            "qt6pdf",
            "qt6webengine",
            "qt6bluetooth",
            "qt6nfc",
            "qt6sensors",
            "qt6positioning",
            "qt6serialport",
            "qt6charts",
            "qt6designer",
            "qt6help",
            "qt6test",
            "qt6webenginequick",
            "qt6webview",
        ]
    )
]

a.pure = [
    p
    for p in a.pure
    if not any(
        p[0].startswith(exclude)
        for exclude in ["test.", "tests.", "unittest.", "_pytest"]
    )
]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="FlightBot_v2.5",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
