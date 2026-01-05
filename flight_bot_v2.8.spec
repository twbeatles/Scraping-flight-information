# -*- mode: python ; coding: utf-8 -*-
# Flight Bot V2.8 PyInstaller Spec File
# Updated: 2026-01

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Playwright data files
playwright_datas = collect_data_files('playwright')

# Hidden imports for PyQt6 and Playwright
hidden_imports = [
    # PyQt6
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    # Playwright
    'playwright',
    'playwright.sync_api',
    'playwright._impl',
    # Standard Library
    'sqlite3',
    'json',
    'webbrowser',
    'dataclasses',
    'logging',
    'time',
    # Custom modules
    'config',
    'database',
    'scraper_v2',
]

# Optional openpyxl for Excel export
try:
    import openpyxl
    hidden_imports.extend([
        'openpyxl',
        'openpyxl.workbook',
        'openpyxl.worksheet',
        'openpyxl.utils',
    ])
    openpyxl_datas = collect_data_files('openpyxl')
except ImportError:
    openpyxl_datas = []

# Optional matplotlib
try:
    import matplotlib
    hidden_imports.extend([
        'matplotlib',
        'matplotlib.backends.backend_qtagg',
        'matplotlib.figure',
    ])
    matplotlib_datas = collect_data_files('matplotlib')
except ImportError:
    matplotlib_datas = []

a = Analysis(
    ['gui_v2.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.py', '.'),
        ('scraper_v2.py', '.'),
        ('database.py', '.'),
    ] + playwright_datas + matplotlib_datas + openpyxl_datas,
    hiddenimports=hidden_imports + collect_submodules('playwright'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 기본 제외
        'tkinter', 'unittest', 'test', 'xmlrpc',
        # 추가 제외 (배포 크기 축소)
        'html.parser', 'http.server',
        'pydoc', 'doctest', 'ftplib', 'turtledemo',
        'lib2to3', 'idlelib', 'distutils', 'ensurepip',
        'venv', 'pdb', 'profile', 'pstats', 'cProfile',
        'curses', 'lzma', 'bz2', 'dbm',
        # 테스트/개발용 모듈 제외
        'pytest', 'setuptools', 'pip', 'wheel',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)


pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FlightBot_v2.8',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # 심볼 제거로 크기 축소
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI 앱이므로 콘솔 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 아이콘 파일이 있다면 'icon.ico' 지정
)
