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
    'playwright._impl._api_types',
    
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
