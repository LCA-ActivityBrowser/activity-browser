"""Host plugin loader seam tests (fake entry points)."""
import sys
from types import SimpleNamespace

import pytest

from activity_browser.plugins import loader
from activity_browser.plugins.version import PLUGINS_API_VERSION


class _FakeSettings:
    def __init__(self, enabled=None):
        self._data = {
            "plugins": {
                "enabled_plugins": list(enabled or []),
                "data": {},
            }
        }
        self.global_config = {"plugins": self._data["plugins"]}

    def __getitem__(self, key):
        return self._data[key]


def _ep(name, activate, *, dist=None):
    return SimpleNamespace(name=name, load=lambda: activate, dist=dist)


def _register_pkg(name, *, api_version=PLUGINS_API_VERSION, display_name=None):
    """Fake entry-point package — name must match ``_ep(..., name)``."""
    attrs = {"PLUGINS_API_VERSION": api_version}
    if display_name is not None:
        attrs["PLUGIN_DISPLAY_NAME"] = display_name
    sys.modules[name] = type("Pkg", (), attrs)


@pytest.fixture(autouse=True)
def _reset_plugin_side_effects(monkeypatch):
    """Isolate pages/panes/contributions mutations from loader tests."""
    import activity_browser.app.contributions as contrib
    import activity_browser.app.pages as pages
    import activity_browser.app.panes as panes

    pages_backup = dict(pages.base_pages)
    panes_backup = dict(panes.base_panes)
    actions_backup = dict(contrib.action_contributions)
    chapters_backup = contrib.settings_chapters.copy()
    submenu_backup = {k: list(v) for k, v in contrib.plugin_submenu_items.items()}
    display_backup = dict(contrib.plugin_display_names)
    records_backup = list(loader.plugin_records)

    yield

    pages.base_pages.clear()
    pages.base_pages.update(pages_backup)
    panes.base_panes.clear()
    panes.base_panes.update(panes_backup)
    contrib.action_contributions.clear()
    contrib.action_contributions.update(actions_backup)
    contrib.settings_chapters.clear()
    contrib.settings_chapters.update(chapters_backup)
    contrib.plugin_submenu_items.clear()
    contrib.plugin_submenu_items.update(submenu_backup)
    contrib.plugin_display_names.clear()
    contrib.plugin_display_names.update(display_backup)
    loader.plugin_records = records_backup


def test_skips_disabled_plugins(monkeypatch):
    pkg = "tests.fake_plugin_disabled"

    def activate(ctx):
        raise AssertionError("should not activate disabled plugin")

    _register_pkg(pkg)
    monkeypatch.setattr(
        loader,
        "discover_entry_points",
        lambda: [_ep(pkg, activate)],
    )
    records = loader.load_and_activate_plugins(
        application=None, signals=None, settings=_FakeSettings(enabled=[])
    )
    assert len(records) == 1
    assert records[0].status == "disabled"
    assert records[0].plugin_id == pkg


def test_skips_incompatible_api_version(monkeypatch):
    pkg = "tests.fake_plugin_mod"

    def activate(ctx):
        raise AssertionError("should not activate incompatible plugin")

    _register_pkg(pkg, api_version="0")
    monkeypatch.setattr(
        loader,
        "discover_entry_points",
        lambda: [_ep(pkg, activate)],
    )
    records = loader.load_and_activate_plugins(
        application=None, signals=None, settings=_FakeSettings(enabled=[pkg])
    )
    assert records[0].status == "incompatible"
    assert "incompatible" in (records[0].error or "").lower() or "0" in (records[0].error or "")


def test_activates_and_registers_page(monkeypatch):
    from activity_browser.app import pages
    from activity_browser.ui.widgets.abstract_page import ABAbstractPage

    pkg = "tests.fake_plugin_ok"

    class DemoPage(ABAbstractPage):
        title = "Demo"

    def activate(ctx):
        ctx.register_page(f"{ctx.plugin_id}.page", DemoPage, title="Demo Page")

    _register_pkg(pkg, display_name="Demo Plugin")
    monkeypatch.setattr(
        loader,
        "discover_entry_points",
        lambda: [_ep(pkg, activate)],
    )
    records = loader.load_and_activate_plugins(
        application=object(),
        signals=object(),
        settings=_FakeSettings(enabled=[pkg]),
    )
    assert records[0].status == "enabled"
    assert f"{pkg}.page" in pages.base_pages


def test_show_by_default_adds_startup_lists(monkeypatch):
    from activity_browser.ui.widgets.abstract_page import ABAbstractPage
    from activity_browser.ui.widgets.abstract_pane import ABAbstractPane

    pkg = "tests.fake_plugin_startup"

    class DemoPage(ABAbstractPage):
        title = "Demo"

    class DemoPane(ABAbstractPane):
        title = "Demo"

    def activate(ctx):
        ctx.register_page(
            f"{ctx.plugin_id}.page",
            DemoPage,
            title="Demo Page",
        )
        ctx.register_pane(
            f"{ctx.plugin_id}.pane",
            DemoPane,
            title="Demo Pane",
        )
        ctx.register_page(
            f"{ctx.plugin_id}.hidden",
            DemoPage,
            title="Hidden Page",
            show_by_default=False,
        )

    _register_pkg(pkg)
    monkeypatch.setattr(
        loader,
        "discover_entry_points",
        lambda: [_ep(pkg, activate)],
    )
    settings = _FakeSettings(enabled=[pkg])
    settings.global_config = {"plugins": settings._data["plugins"]}
    loader.load_and_activate_plugins(
        application=object(),
        signals=object(),
        settings=settings,
    )
    assert f"{pkg}.page" in settings.global_config["startup"]["shown_pages"]
    assert f"{pkg}.pane" in settings.global_config["startup"]["shown_panes"]
    assert f"{pkg}.hidden" not in settings.global_config["startup"]["shown_pages"]


def test_reads_api_version_from_entry_point_package(monkeypatch):
    """PLUGINS_API_VERSION on the entry-point package works with activate in a submodule."""
    pkg = "fake_plugin_submod"

    def activate(ctx):
        pass

    activate.__module__ = f"{pkg}.activate"
    _register_pkg(pkg)
    monkeypatch.setattr(
        loader,
        "discover_entry_points",
        lambda: [_ep(pkg, activate)],
    )
    records = loader.load_and_activate_plugins(
        application=object(),
        signals=object(),
        settings=_FakeSettings(enabled=[pkg]),
    )
    assert records[0].status == "enabled"


def test_reads_display_name_from_entry_point_package(monkeypatch):
    pkg = "tests.fake_plugin_name"

    def activate(ctx):
        pass

    activate.__module__ = f"{pkg}.activate"
    _register_pkg(pkg, display_name="Friendly Plugin")
    monkeypatch.setattr(
        loader,
        "discover_entry_points",
        lambda: [_ep(pkg, activate)],
    )
    records = loader.load_and_activate_plugins(
        application=object(),
        signals=object(),
        settings=_FakeSettings(enabled=[]),
    )
    assert records[0].display_name == "Friendly Plugin"


def test_fail_soft_continues_to_next_plugin(monkeypatch):
    bad_pkg = "tests.fake_plugin_bad"
    good_pkg = "tests.fake_plugin_good"

    def bad(ctx):
        raise RuntimeError("boom")

    def good(ctx):
        ctx.register_action(f"{ctx.plugin_id}.act", type("A", (), {}))

    _register_pkg(bad_pkg)
    _register_pkg(good_pkg)
    monkeypatch.setattr(
        loader,
        "discover_entry_points",
        lambda: [_ep(bad_pkg, bad), _ep(good_pkg, good)],
    )
    from activity_browser.app import contributions as contrib

    records = loader.load_and_activate_plugins(
        application=object(),
        signals=object(),
        settings=_FakeSettings(enabled=[bad_pkg, good_pkg]),
    )
    assert records[0].status == "failed"
    assert records[1].status == "enabled"
    assert f"{good_pkg}.act" in contrib.action_contributions
