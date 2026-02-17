# -*- mode: python ; coding: utf-8 -*-
"""
Flight Bot v2.5 - PyInstaller Spec File (onefile)
경량화 최적화 + Playwright 지원 + HiDPI 지원
"""
import sys
import os

block_cipher = None

# == 경량화를 위한 제외 모듈 목록 (확장) ==
excluded_modules = [
    # 데이터 분석 라이브러리 (불필요)
    'matplotlib', 'numpy', 'pandas', 'scipy', 'seaborn', 'statsmodels',
    
    # 이미지/미디어 처리 (불필요)
    'PIL', 'pillow', 'cv2', 'opencv', 'imageio', 'skimage',
    
    # Jupyter/IPython (불필요)
    'notebook', 'ipython', 'nbconvert', 'nbformat', 'jupyter',
    'ipykernel', 'ipywidgets',
    
    # GUI 대안 (PyQt6 사용하므로 불필요)
    'tkinter', 'wx', 'kivy', 'pygame',
    
    # 테스트/문서화 (불필요)
    'pydoc', 'doctest', 'lib2to3', 'test', 'unittest', 'pytest',
    
    # 네트워크 (직접 미사용)
    'xmlrpc', 'ftplib', 'nntplib', 'poplib', 'imaplib', 'smtplib',
    'telnetlib',
    
    # 이메일 (불필요)
    'email.test', 'email.mime.audio', 'email.mime.image',
    
    # 기타 무거운 패키지
    'cryptography', 'boto3', 'botocore', 'awscli',
    'django', 'flask', 'tornado', 'twisted',
]

a = Analysis(
    ['gui_v2.py'],  # 메인 진입점
    pathex=[],
    binaries=[],
    datas=[
        # (소스 경로, 대상 폴더) - 필수 파일만 포함
        ('scraper_config.py', '.'),
        ('config.py', '.'),
        ('ui', 'ui'),  # UI 패키지
    ],
    hiddenimports=[
        # UI 모듈
        'ui.styles', 
        'ui.components', 
        'ui.workers', 
        'ui.dialogs',
        
        # 핵심 모듈
        'database', 
        'scraper_v2', 
        'scraper_config', 
        'config',
        'preferences',
        'session_manager',
        
        # Playwright 관련
        'playwright',
        'playwright.sync_api',
        'playwright._impl',
        
        # asyncio Windows 지원 (필수)
        'asyncio',
        'asyncio.windows_events',
        'asyncio.windows_utils',
        
        # PyQt6 플러그인
        'PyQt6.sip',
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
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

# ZIP 압축
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 실행 파일 생성 (onefile 모드)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,    # onefile: 바이너리 포함
    a.zipfiles,    # onefile: zip 파일 포함
    a.datas,       # onefile: 데이터 파일 포함
    [],
    name='FlightBot_v2.5',  # 실행 파일명
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # 디버그 심볼 제거로 경량화
    upx=True,    # UPX 압축 활성화
    upx_exclude=[
        # UPX 압축 제외 (호환성 문제 방지)
        'vcruntime140.dll',
        'python*.dll',
        'Qt*.dll',
    ],
    console=False,  # 콘솔 숨기기 (GUI 전용)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 아이콘 사용 시: 'icon.ico'
)

# onefile 모드에서는 COLLECT 불필요
