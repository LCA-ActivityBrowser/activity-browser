"""Host plugin loader seam tests (fake entry points)."""
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

    def __getitem__(self, key):
        return self._data[key]


def _ep(name, activate, *, dist=None):
    return SimpleNamespace(name=name, load=lambda: activate, dist=dist)


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
    page_def_backup = dict(contrib.page_show_defaults)
    pane_def_backup = dict(contrib.pane_show_defaults)
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
    contrib.page_show_defaults.clear()
    contrib.page_show_defaults.update(page_def_backup)
    contrib.pane_show_defaults.clear()
    contrib.pane_show_defaults.update(pane_def_backup)
    loader.plugin_records = records_backup


def test_skips_disabled_plugins(monkeypatch):
    def activate(ctx):
        raise AssertionError("should not activate disabled plugin")

    monkeypatch.setattr(
        loader,
        "discover_entry_points",
        lambda: [_ep("demo", activate)],
    )
    records = loader.load_and_activate_plugins(
        application=None, signals=None, settings=_FakeSettings(enabled=[])
    )
    assert len(records) == 1
    assert records[0].status == "disabled"
    assert records[0].plugin_id == "demo"


def test_skips_incompatible_api_version(monkeypatch):
    def activate(ctx):
        raise AssertionError("should not activate incompatible plugin")

    activate.__module__ = "tests.fake_plugin_mod"

    class Mod:
        PLUGINS_API_VERSION = "0"

    import sys

    sys.modules["tests.fake_plugin_mod"] = Mod
    monkeypatch.setattr(
        loader,
        "discover_entry_points",
        lambda: [_ep("old", activate)],
    )
    records = loader.load_and_activate_plugins(
        application=None, signals=None, settings=_FakeSettings(enabled=["old"])
    )
    assert records[0].status == "incompatible"
    assert "incompatible" in (records[0].error or "").lower() or "0" in (records[0].error or "")


def test_activates_and_registers_page(monkeypatch):
    from activity_browser.app import pages
    from activity_browser.ui.widgets.abstract_page import ABAbstractPage

    class DemoPage(ABAbstractPage):
        title = "Demo"

    def activate(ctx):
        ctx.register_page(f"{ctx.plugin_id}.page", DemoPage, title="Demo Page")

    activate.__module__ = "tests.fake_plugin_ok"

    class Mod:
        PLUGINS_API_VERSION = PLUGINS_API_VERSION
        PLUGIN_DISPLAY_NAME = "Demo Plugin"

    import sys

    sys.modules["tests.fake_plugin_ok"] = Mod
    monkeypatch.setattr(
        loader,
        "discover_entry_points",
        lambda: [_ep("demo", activate)],
    )
    records = loader.load_and_activate_plugins(
        application=object(),
        signals=object(),
        settings=_FakeSettings(enabled=["demo"]),
    )
    assert records[0].status == "loaded"
    assert "demo.page" in pages.base_pages


def test_show_by_default_adds_startup_lists(monkeypatch):
    from activity_browser.ui.widgets.abstract_page import ABAbstractPage
    from activity_browser.ui.widgets.abstract_pane import ABAbstractPane

    class DemoPage(ABAbstractPage):
        title = "Demo"

    class DemoPane(ABAbstractPane):
        title = "Demo"

    def activate(ctx):
        ctx.register_page(
            f"{ctx.plugin_id}.page",
            DemoPage,
            title="Demo Page",
            show_by_default=True,
        )
        ctx.register_pane(
            f"{ctx.plugin_id}.pane",
            DemoPane,
            title="Demo Pane",
            show_by_default=True,
        )

    activate.__module__ = "tests.fake_plugin_startup"

    class Mod:
        PLUGINS_API_VERSION = PLUGINS_API_VERSION

    import sys

    sys.modules["tests.fake_plugin_startup"] = Mod
    monkeypatch.setattr(
        loader,
        "discover_entry_points",
        lambda: [_ep("demo", activate)],
    )
    settings = _FakeSettings(enabled=["demo"])
    settings.global_config = {"plugins": settings._data["plugins"]}
    loader.load_and_activate_plugins(
        application=object(),
        signals=object(),
        settings=settings,
    )
    assert "demo.page" in settings.global_config["startup"]["shown_pages"]
    assert "demo.pane" in settings.global_config["startup"]["shown_panes"]


def test_reads_api_version_from_entry_point_package(monkeypatch):
    """PLUGINS_API_VERSION on the package __init__ works when activate is a submodule."""
    from activity_browser.ui.widgets.abstract_page import ABAbstractPage

    class DemoPage(ABAbstractPage):
        title = "Demo"

    def activate(ctx):
        ctx.register_page(f"{ctx.plugin_id}.page", DemoPage, title="Demo Page")

    activate.__module__ = "tests.fake_plugin_submod.activate"

    class Pkg:
        PLUGINS_API_VERSION = PLUGINS_API_VERSION

    class SubMod:
        pass

    import sys

    sys.modules["tests.fake_plugin_submod"] = Pkg
    sys.modules["tests.fake_plugin_submod.activate"] = SubMod
    monkeypatch.setattr(
        loader,
        "discover_entry_points",
        lambda: [_ep("demo", activate)],
    )
    records = loader.load_and_activate_plugins(
        application=object(),
        signals=object(),
        settings=_FakeSettings(enabled=["demo"]),
    )
    assert records[0].status == "loaded"


def test_fail_soft_continues_to_next_plugin(monkeypatch):
    def bad(ctx):
        raise RuntimeError("boom")

    def good(ctx):
        ctx.register_action(f"{ctx.plugin_id}.act", type("A", (), {}))

    bad.__module__ = "tests.fake_plugin_bad"
    good.__module__ = "tests.fake_plugin_good"

    class ModBad:
        PLUGINS_API_VERSION = PLUGINS_API_VERSION

    class ModGood:
        PLUGINS_API_VERSION = PLUGINS_API_VERSION

    import sys

    sys.modules["tests.fake_plugin_bad"] = ModBad
    sys.modules["tests.fake_plugin_good"] = ModGood
    monkeypatch.setattr(
        loader,
        "discover_entry_points",
        lambda: [_ep("bad", bad), _ep("good", good)],
    )
    from activity_browser.app import contributions as contrib

    records = loader.load_and_activate_plugins(
        application=object(),
        signals=object(),
        settings=_FakeSettings(enabled=["bad", "good"]),
    )
    assert records[0].status == "failed"
    assert records[1].status == "loaded"
    assert "good.act" in contrib.action_contributions
