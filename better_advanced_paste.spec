# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

block_cipher = None

project_dir = Path(os.path.abspath('.'))

datas = [
    (str(project_dir / 'ui.html'), '.'),
    (str(project_dir / 'settings.html'), '.'),
    # Include app icon for runtime (window icon) access
    (str(project_dir / 'icon.ico'), '.'),
]

hiddenimports = [
    # Ensure Windows keyring backend is available
    'win32ctypes.core',
    'keyring.backends',
    'keyring.backends.Windows',
]

excludes = [
    # Exclude heavy/unused GUI backends to keep size minimal
    'cefpython3',
    'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
    'gi', 'gtk', 'tkinter',
]


a = Analysis(
    ['main.py'],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
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
    exclude_binaries=False,
    name='BetterAdvancedPaste',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=True,
    # Set the executable file icon
    icon=str(project_dir / 'icon.ico'),
)
app = exe
