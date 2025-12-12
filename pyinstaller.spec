# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
import sys
import glob
from pathlib import Path

def find_mkl_libs():
    """Find MKL DLL files for PyPardiso"""
    patterns = [
        f'{sys.prefix}/Library/bin/mkl_*.dll',
        f'{sys.prefix}/Library/bin/libiomp5md.dll',
    ]

    binaries = []
    for pattern in patterns:
        for lib in glob.glob(pattern):
            binaries.append((lib, '.'))

    return binaries

block_cipher = None

# Collect all data files from activity_browser package
ab_datas = collect_data_files('activity_browser')

a = Analysis(
    ['run-activity-browser.py'],
    pathex=[],
    binaries=find_mkl_libs(),
    datas=ab_datas,
    hiddenimports=[
        'activity_browser',
        'PySide6',
        'bw2data',
        'bw2io',
        'bw2calc',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    a.datas,
    [],
    name='activity-browser',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='activity_browser/static/icons/main/activitybrowser.ico',
)
