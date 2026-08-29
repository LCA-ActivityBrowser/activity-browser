"""Pure-logic tests for Linux/Wayland Qt WebEngine GPU fallback flags."""
import os

import pytest

from activity_browser.ui.core.application import (
    _WAYLAND_FLAGS,
    _is_linux_wayland,
    _webengine_flags,
)


@pytest.fixture(autouse=True)
def _clean_qt_env(monkeypatch):
    for key in (
        "QT_QPA_PLATFORM",
        "QTWEBENGINE_CHROMIUM_FLAGS",
        "XDG_SESSION_TYPE",
        "WAYLAND_DISPLAY",
    ):
        monkeypatch.delenv(key, raising=False)


def test_is_linux_wayland_by_session_type(monkeypatch):
    monkeypatch.setattr("activity_browser.ui.core.application.sys.platform", "linux")
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    assert _is_linux_wayland() is True


def test_is_linux_wayland_by_wayland_display(monkeypatch):
    monkeypatch.setattr("activity_browser.ui.core.application.sys.platform", "linux")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    assert _is_linux_wayland() is True


def test_is_linux_wayland_false_on_xcb_override(monkeypatch):
    monkeypatch.setattr("activity_browser.ui.core.application.sys.platform", "linux")
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("QT_QPA_PLATFORM", "xcb")
    assert _is_linux_wayland() is False


def test_is_linux_wayland_false_on_windows(monkeypatch):
    monkeypatch.setattr("activity_browser.ui.core.application.sys.platform", "win32")
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    assert _is_linux_wayland() is False


def test_webengine_flags_adds_wayland_gpu_disable(monkeypatch):
    monkeypatch.setattr("activity_browser.ui.core.application.sys.platform", "linux")
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    _webengine_flags()
    flags = os.environ["QTWEBENGINE_CHROMIUM_FLAGS"].split()
    for flag in _WAYLAND_FLAGS:
        assert flag in flags


def test_webengine_flags_skips_wayland_on_xcb(monkeypatch):
    monkeypatch.setattr("activity_browser.ui.core.application.sys.platform", "linux")
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("QT_QPA_PLATFORM", "xcb")
    _webengine_flags()
    assert "QTWEBENGINE_CHROMIUM_FLAGS" not in os.environ or not any(
        f in os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "").split()
        for f in _WAYLAND_FLAGS
    )
