# -*- mode: python ; coding: utf-8 -*-
"""
Flight Bot v2.5 - PyInstaller Build Spec
빌드: pyinstaller flight_bot.spec
"""

block_cipher = None

# 불필요한 라이브러리 제외 (경량화)
excludes = [
    'matplotlib', 'numpy', 'pandas', 'scipy', 'tkinter',
    'unittest', 'email', 'http', 'xml', 'pydoc', 'pdb',
    'distutils', 'setuptools', 'pkg_resources',
    'IPython', 'jupyter', 'notebook', 'PIL', 'cv2'
]

# Hidden imports (자동 감지되지 않는 모듈)
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui', 
    'PyQt6.QtWidgets',
    'playwright.sync_api',
]

a = Analysis(
    ['gui_v2.py'],
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
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI 앱 - 콘솔 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',  # 아이콘 파일이 있는 경우 주석 해제
)
