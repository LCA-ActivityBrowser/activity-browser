# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Activity Browser stand-alone builds (onedir)."""
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

# collect_all imports package submodules in a subprocess. On headless CI Linux
# that pulls in Qt and aborts without a platform plugin unless we set this.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# SPECPATH is injected by PyInstaller when this file is executed.
spec_root = Path(SPECPATH).resolve()
license_file = spec_root / "LICENSE.txt"
icon_ico = spec_root / "activity_browser" / "static" / "icons" / "main" / "activitybrowser.ico"
icon_png = spec_root / "activity_browser" / "static" / "icons" / "main" / "activitybrowser.png"

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
    binaries = [
        (str(bin_dir / dll), "lib")
        for dll in pardiso_deps
        if (bin_dir / dll).exists()
    ]
else:
    binaries = []

block_cipher = None

# collect_all pulls package data *and* modules. Using only collect_data_files
# creates an on-disk activity_browser/ tree without .py files, which shadows
# the frozen package (namespace package) and breaks imports like __main__.
ab_datas, ab_binaries, ab_hiddenimports = collect_all("activity_browser")
binaries += ab_binaries

if license_file.exists():
    ab_datas.append((str(license_file), "."))

hiddenimports = sorted(
    set(
        ab_hiddenimports
        + [
            "activity_browser",
            "activity_browser.__main__",
            "PySide6",
            "bw2data",
            "bw2io",
            "bw2calc",
            "pypardiso",
            "scikits.umfpack",
        ]
    )
)

a = Analysis(
    ["run-activity-browser.py"],
    pathex=[],
    binaries=binaries,
    datas=ab_datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name="activity-browser",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_ico) if icon_ico.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="activity-browser",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Activity Browser.app",
        icon=str(icon_png) if icon_png.exists() else None,
        bundle_identifier="org.activity-browser.ActivityBrowser",
        info_plist={
            "CFBundleName": "Activity Browser",
            "CFBundleDisplayName": "Activity Browser",
            "CFBundleShortVersionString": "3.0.0",
            "NSHighResolutionCapable": True,
        },
    )
