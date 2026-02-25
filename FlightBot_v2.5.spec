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
    "playwright._impl._api_types",
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
