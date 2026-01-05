
# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

# == 경량화를 위한 제외 모듈 목록 ==
excluded_modules = [
    'matplotlib', 'numpy', 'pandas', 'scipy', 'tkinter', 'notebook',
    'ipython', 'nbconvert', 'nbformat', 'pil', 'pillow',
    'cv2', 'pydoc', 'lib2to3', 'test', 'unittest', 'xmlrpc',
    'email.test', 'email'
]

a = Analysis(
    ['gui_v2.py'],  # 진입점
    pathex=[],
    binaries=[],
    datas=[
        # (소스 경로, 대상 폴더)
        ('scraper_config.py', '.'),  
        ('README.md', '.'),
        ('ui', 'ui'),  # UI 패키지 포함
    ],
    hiddenimports=[
        'ui.styles', 'ui.components', 'ui.workers', 'ui.dialogs',
        'database', 'scraper_v2', 'scraper_config', 'playwright',
        'config'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FlightBot_v3.0',  # 실행 파일 이름
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # UPX 압축 활성화 (가능한 경우)
    console=False,  # 콘솔 숨기기 (GUI 모드)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None  # 필요시 아이콘 경로 추가 (예: 'icon.ico')
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FlightBot_v3.0',
)
