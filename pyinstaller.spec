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

binaries = []
extra_datas = []
extra_hiddenimports = []


def _replace_dir(src: Path, dest: Path) -> None:
    import shutil

    if dest.is_symlink() or dest.is_file():
        dest.unlink()
    elif dest.is_dir():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, symlinks=False)
    print(f"Copied {src.name} -> {dest}")


def _copy_macos_qtwebengine_support(app_path: Path) -> None:
    """Ship QtWebEngineProcess + resource .pak files into the .app.

    Missing either causes QWebEnginePage to abort() (SIGABRT).
    """
    import PySide6

    qt_lib = Path(PySide6.__file__).resolve().parent / "Qt" / "lib"
    src_fw = qt_lib / "QtWebEngineCore.framework"
    src_helpers = src_fw / "Helpers"
    src_resources = src_fw / "Resources"
    if not src_helpers.is_dir() or not src_resources.is_dir():
        raise SystemExit(
            f"Incomplete QtWebEngineCore.framework under {src_fw} "
            "(need Helpers and Resources)"
        )

    for fw in app_path.glob("**/QtWebEngineCore.framework"):
        proc = fw / "Helpers/QtWebEngineProcess.app/Contents/MacOS/QtWebEngineProcess"
        if not proc.is_file():
            _replace_dir(src_helpers, fw / "Helpers")
        # Resources hold icudtl.dat / *.pak; Qt searches framework/Resources first.
        if not (fw / "Resources" / "icudtl.dat").is_file():
            _replace_dir(src_resources, fw / "Resources")


def _collect_prefix_libs(patterns, dest, *, resolve=False):
    """Collect ``(src, dest)`` pairs for shared libs under ``sys.prefix``."""
    out = []
    for pattern in patterns:
        for path in Path(sys.prefix).glob(pattern):
            if path.is_file() or path.is_symlink():
                out.append((str(path.resolve() if resolve else path), dest))
    return out


# Keep freeze-env relative layout inside onedir / .app ``_internal``.
if sys.platform == "win32" or sys.platform.startswith("linux"):
    try:
        d, b, h = collect_all("pypardiso")
        extra_datas += d
        binaries += b
        extra_hiddenimports += h
    except Exception as exc:  # pragma: no cover - packaging diagnostics
        print(f"WARNING: collect_all(pypardiso) failed: {exc}")

    if sys.platform == "win32":
        binaries += _collect_prefix_libs(
            (
                "Library/bin/mkl_*.dll",
                "Library/bin/libiomp*.dll",
                "Library/bin/libimalloc.dll",
                "Library/bin/tbb*.dll",
                "Library/bin/tbbmalloc*.dll",
            ),
            "Library/bin",
        )
    else:
        binaries += _collect_prefix_libs(
            ("lib/libmkl_*.so*", "lib/libiomp*.so*", "lib/libtbb*.so*"),
            "lib",
        )

    if not any("mkl_rt" in Path(src).name for src, _ in binaries):
        raise SystemExit(
            "Fast solver libs not found under sys.prefix "
            f"({sys.prefix}). On Windows/Linux x86_64 install pypardiso "
            "(pulls in the pip `mkl` package) before running PyInstaller."
        )

elif sys.platform == "darwin":
    try:
        d, b, h = collect_all("scikits.umfpack")
        extra_datas += d
        binaries += b
        extra_hiddenimports += h
    except Exception as exc:  # pragma: no cover - packaging diagnostics
        raise SystemExit(
            f"collect_all(scikits.umfpack) failed: {exc}. "
            "Install scikit-umfpack (conda-forge) into the freeze env before PyInstaller."
        ) from exc

    binaries += _collect_prefix_libs(
        (
            "lib/libumfpack*.dylib*",
            "lib/libsuitesparseconfig*.dylib*",
            "lib/libamd*.dylib*",
            "lib/libcamd*.dylib*",
            "lib/libcolamd*.dylib*",
            "lib/libccolamd*.dylib*",
            "lib/libcholmod*.dylib*",
        ),
        "lib",
        resolve=True,
    )
    required = ("libumfpack", "libsuitesparseconfig", "libamd")
    missing = [
        name
        for name in required
        if not any(Path(src).name.startswith(name) for src, _ in binaries)
    ]
    if missing:
        raise SystemExit(
            "Fast solver libs missing under sys.prefix "
            f"({sys.prefix}): {', '.join(missing)}. Install scikit-umfpack "
            "from conda-forge before running PyInstaller."
        )

block_cipher = None

# collect_all pulls package data *and* modules. Using only collect_data_files
# creates an on-disk activity_browser/ tree without .py files, which shadows
# the frozen package (namespace package) and breaks imports like __main__.
ab_datas, ab_binaries, ab_hiddenimports = collect_all("activity_browser")
binaries += ab_binaries
ab_datas += extra_datas

if license_file.exists():
    ab_datas.append((str(license_file), "."))

hiddenimports = sorted(
    set(
        ab_hiddenimports
        + extra_hiddenimports
        + [
            "activity_browser",
            "activity_browser.__main__",
            "PySide6",
            # Named so PyInstaller's WebEngine hooks run (AB imports via qtpy).
            "PySide6.QtWebEngineCore",
            "PySide6.QtWebEngineWidgets",
            "PySide6.QtWebEngineQuick",
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

# Windows: keep a console so startup failures are visible (stderr).
# macOS: console=True makes PyInstaller set LSBackgroundOnly=True on the .app,
# so Launch Services treats AB as a background agent and Finder launches leave
# a Terminal/bash window after the splash. Use a windowed bundle instead.
# Linux: console has no Finder equivalent; keep True for AppImage stderr.
_console = sys.platform != "darwin"

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="activity-browser",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX packing commonly triggers browser/AV false positives on Windows.
    upx=False,
    console=_console,
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
    upx=False,
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
            # Belt-and-suspenders if console is ever flipped back to True.
            "LSBackgroundOnly": False,
        },
    )
    _copy_macos_qtwebengine_support(spec_root / "dist" / "Activity Browser.app")
