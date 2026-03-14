# -*- mode: python ; coding: utf-8 -*-
"""
Flight Bot v2.5 - PyInstaller Build Spec (Optimized for Lightweight Build)
빌드: pyinstaller --clean flight_bot.spec
"""

block_cipher = None

# ===== 경량화를 위한 제외 목록 =====
excludes = [
    # 데이터 과학/시각화 (미사용)
    'matplotlib', 'numpy', 'pandas', 'scipy', 'PIL', 'cv2',
    'seaborn', 'plotly', 'bokeh', 'altair', 'sympy',
    
    # 테스트/개발 도구
    'unittest', 'pytest', 'nose', 'pdb', 'pydoc', 'doctest',
    'IPython', 'jupyter', 'notebook', 'ipykernel',
    
    # 불필요한 표준 라이브러리
    'tkinter', 'turtle', 'idlelib', 'turtledemo',
    'email', 'xml.dom', 'xml.sax', 'xmlrpc',
    'distutils', 'setuptools', 'pkg_resources', 'pip', 'ensurepip',
    'lib2to3', 'test', 'tests',
    
    # 네트워크/서버 (미사용)
    'flask', 'django', 'tornado', 'aiohttp', 'fastapi',
    'http.server', 'ftplib', 'telnetlib', 'socketserver',
    
    # 기타 미사용
    'curses', 'multiprocessing.popen_spawn_posix',
]

# ===== Hidden Imports =====
hiddenimports = [
    # PyQt6 필수 모듈
    'PyQt6.QtCore',
    'PyQt6.QtGui', 
    'PyQt6.QtWidgets',
    
    # Playwright
    'playwright.sync_api',
    'playwright._impl._api_structures',
    
    # asyncio (Windows 필수)
    'asyncio',
    'asyncio.windows_events',
    'asyncio.windows_utils',
    'asyncio.proactor_events',
    'asyncio.selector_events',
    
    # 표준 라이브러리 (동적 임포트)
    'json',
    'logging',
    'sqlite3',
    'threading',
    'concurrent.futures',
    'shutil',
    'tempfile',
    # Facade modules (public import compatibility)
    'database',
    'scraper_v2',
    'ui.components',
    'ui.dialogs',
    'ui.styles',
    'ui.workers',
    # Refactored package modules (facade-compatible split)
    'app.main_window',
    'app.session_manager',
    'app.mainwindow.shared',
    'app.mainwindow.ui_bootstrap',
    'app.mainwindow.ui_bootstrap_sections',
    'app.mainwindow.telemetry',
    'app.mainwindow.auto_alert',
    'app.mainwindow.worker_lifecycle',
    'app.mainwindow.favorites',
    'app.mainwindow.exports',
    'app.mainwindow.search_single',
    'app.mainwindow.search_multi',
    'app.mainwindow.search_date_range',
    'app.mainwindow.manual_mode',
    'app.mainwindow.filtering',
    'app.mainwindow.history',
    'app.mainwindow.session',
    'app.mainwindow.calendar',
    'app.mainwindow.app_lifecycle',
    'scraping.errors',
    'scraping.models',
    'scraping.playwright_scraper',
    'scraping.playwright_browser',
    'scraping.playwright_search',
    'scraping.playwright_domestic',
    'scraping.playwright_results',
    'scraping.extract_domestic',
    'scraping.extract_international',
    'scraping.searcher',
    'scraping.parallel',
    'storage.models',
    'storage.schema',
    'storage.flight_database',
    'storage.db_favorites',
    'storage.db_history_logs',
    'storage.db_telemetry',
    'storage.db_alerts',
    'storage.db_last_search',
    'ui.components_primitives',
    'ui.components_filter_panel',
    'ui.components_result_table',
    'ui.components_log_viewer',
    'ui.components_search_panel',
    'ui.search_panel_shared',
    'ui.search_panel_build',
    'ui.search_panel_actions',
    'ui.search_panel_state',
    'ui.search_panel_widget',
    'ui.dialogs_base',
    'ui.dialogs_calendar',
    'ui.dialogs_combination',
    'ui.dialogs_search',
    'ui.dialogs_search_multi',
    'ui.dialogs_search_date_range',
    'ui.dialogs_search_results',
    'ui.dialogs_tools',
    'ui.dialogs_tools_shortcuts',
    'ui.dialogs_tools_price_alert',
    'ui.dialogs_tools_settings',
    'ui.styles_dark',
    'ui.styles_light',
    'ui.workers_search',
    'ui.workers_parallel',
    'ui.workers_alerts',
]

# ===== 데이터 파일 =====
datas = [
    # ('icon.ico', '.'),
]

a = Analysis(
    ['gui_v2.py'],
    pathex=[],
    binaries=[],
    datas=datas,
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

# ===== 바이너리 필터링 (추가 경량화) =====
a.binaries = [b for b in a.binaries if not any(
    exclude in b[0].lower() for exclude in [
        # 미사용 Qt 모듈
        'qt6quick', 'qt6qml', 'qt6network', 'qt63d',
        'qt6multimedia', 'qt6pdf', 'qt6webengine',
        'qt6bluetooth', 'qt6nfc', 'qt6sensors',
        'qt6positioning', 'qt6serialport', 'qt6charts',
        'qt6designer', 'qt6help', 'qt6test',
        'qt6webenginequick', 'qt6webview',
        # OpenSSL (Playwright 자체 포함)
        'libcrypto', 'libssl',
    ]
)]

# ===== 추가 경량화: 불필요한 pure python 모듈 제거 =====
a.pure = [p for p in a.pure if not any(
    p[0].startswith(exclude) for exclude in [
        'test.', 'tests.', 'unittest.', '_pytest',
    ]
)]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FlightBot_v2.5',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# ===== 빌드 가이드 =====
# 1. UPX 설치 (선택): https://github.com/upx/upx/releases
# 2. 빌드 명령: pyinstaller --clean flight_bot.spec
# 3. 예상 크기: ~80-120MB (Playwright 포함)
# 4. 실행 전 Playwright 브라우저 설치 필요: playwright install chromium

