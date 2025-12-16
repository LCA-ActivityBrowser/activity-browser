# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files


if sys.platform == "win32":
    pardiso_deps = [
        "libiomp5md.dll",
        "mkl_core.2.dll",
        "mkl_intel_thread.2.dll",
        "mkl_avx2.2.dll",
        "tbbmalloc.dll",
        "mkl_vml_avx2.2.dll",
        "mkl_rt.2.dll",
    ]

    bin_dir = Path(sys.prefix) / "Library" / "bin"
    binaries = [(str(bin_dir / dll), "lib") for dll in pardiso_deps if (bin_dir / dll).exists()]
else:
    binaries = []

block_cipher = None

# Collect all data files from activity_browser package
ab_datas = collect_data_files('activity_browser')

a = Analysis(
    ['run-activity-browser.py'],
    pathex=[],
    binaries=binaries,
    datas=ab_datas,
    hiddenimports=[
        'activity_browser',
        'PySide6',
        'bw2data',
        'bw2io',
        'bw2calc',
        'pypardiso',
        'scikits.umfpack',
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
