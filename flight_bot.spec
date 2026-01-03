# -*- mode: python ; coding: utf-8 -*-
"""
Flight Bot v2.6 - PyInstaller Build Spec (Optimized for Lightweight Build)
빌드: pyinstaller flight_bot.spec
"""

block_cipher = None

# ===== 경량화를 위한 제외 목록 =====
# 미사용 대형 라이브러리 제외
excludes = [
    # 데이터 과학/시각화 (미사용)
    'matplotlib', 'numpy', 'pandas', 'scipy', 'PIL', 'cv2',
    'seaborn', 'plotly', 'bokeh', 'altair',
    
    # 테스트/개발 도구
    'unittest', 'pytest', 'nose', 'pdb', 'pydoc',
    'IPython', 'jupyter', 'notebook', 'ipykernel',
    
    # 불필요한 표준 라이브러리
    'tkinter', 'turtle', 'idlelib',
    'email', 'xml.dom', 'xml.sax', 'xmlrpc',
    'distutils', 'setuptools', 'pkg_resources', 'pip',
    
    # 네트워크/서버 (미사용)
    'flask', 'django', 'tornado', 'aiohttp', 'fastapi',
    'http.server', 'ftplib', 'telnetlib',
    
]

# ===== Hidden Imports =====
# 자동 감지되지 않는 필수 모듈
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
]

# ===== 데이터 파일 =====
datas = [
    # 아이콘 파일이 있는 경우:
    # ('icon.ico', '.'),
    # ('assets/*', 'assets'),
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
# 불필요한 DLL/SO 파일 제외
a.binaries = [b for b in a.binaries if not any(
    exclude in b[0].lower() for exclude in [
        'qt6quick', 'qt6qml', 'qt6network', 'qt63d',
        'qt6multimedia', 'qt6pdf', 'qt6webengine',
        'qt6bluetooth', 'qt6nfc', 'qt6sensors',
        'qt6positioning', 'qt6serialport',
        'libcrypto', 'libssl',  # OpenSSL (Playwright가 자체 포함)
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
    name='FlightBot_v2.6',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # 심볼 제거 (경량화)
    upx=True,    # UPX 압축 활성화
    upx_exclude=[
        'vcruntime140.dll',  # UPX 호환성 문제 방지
        'python*.dll',
    ],
    runtime_tmpdir=None,
    console=False,  # GUI 앱 - 콘솔 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',  # 아이콘 파일이 있는 경우 주석 해제
)

# ===== 빌드 팁 =====
# 1. UPX 설치 권장: https://github.com/upx/upx/releases
#    - PATH에 추가하면 자동으로 압축 적용
# 2. 빌드 명령: pyinstaller --clean flight_bot.spec
# 3. 예상 크기: ~80-120MB (Playwright 제외 시 ~30MB)
