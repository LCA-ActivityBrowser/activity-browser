"""macOS .app must not ship as a background-only / console bundle."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "pyinstaller.spec"


def test_spec_disables_console_on_darwin():
    """PyInstaller sets LSBackgroundOnly=True when EXE console=True on macOS.

    That makes Finder launches leave a Terminal/bash window after the splash.
    """
    source = SPEC.read_text(encoding="utf-8")
    assert '_console = sys.platform != "darwin"' in source
    assert "console=_console" in source
    assert '"LSBackgroundOnly": False' in source


def test_spec_copies_qtwebengine_support():
    """Welcome/WebEngine abort without QtWebEngineProcess + Resources."""
    source = SPEC.read_text(encoding="utf-8")
    assert "PySide6.QtWebEngineWidgets" in source
    assert "_copy_macos_qtwebengine_support" in source


def test_macos_info_plist_rejects_lsbackgroundonly_true():
    """Red check against a released/bundled Info.plist when provided.

    Set AB_MACOS_INFO_PLIST to a path (e.g. extracted from a DMG) to exercise
    the packaging regression that shipped in 3.0.0b202611151932-stand-alone.
    Skips when unset so normal CI does not need a DMG.
    """
    import os
    import re
    import sys

    path = os.environ.get("AB_MACOS_INFO_PLIST")
    if not path:
        return

    text = Path(path).read_text(encoding="utf-8")
    match = re.search(r"<key>LSBackgroundOnly</key>\s*<(true|false)/>", text)
    if match is not None and match.group(1) == "true":
        print(
            "FAIL: Info.plist has LSBackgroundOnly=true "
            "(macOS .app must use a windowed PyInstaller bundle).",
            file=sys.stderr,
        )
        raise AssertionError("LSBackgroundOnly must not be true")
