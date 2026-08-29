"""Example plugin discovery tests (skip if package not installed)."""
import pytest
from importlib.metadata import entry_points


def _example_ep():
    return next(
        (ep for ep in entry_points(group="activity_browser.plugins") if ep.name == "ab_example"),
        None,
    )


pytestmark = pytest.mark.skipif(
    _example_ep() is None,
    reason="Install with: pip install -e ./plugins/ab-plugin-example",
)


def test_ab_example_entry_point_loadable():
    ep = _example_ep()
    activate = ep.load()
    assert callable(activate)


def test_ab_example_activate_registers_ids(monkeypatch):
    from activity_browser.app import contributions as contrib
    from activity_browser.app import pages, panes
    from activity_browser.plugins.context import PluginContext
    from activity_browser.plugins.version import PLUGINS_API_VERSION

    ep = _example_ep()
    activate = ep.load()
    import ab_example

    assert str(ab_example.PLUGINS_API_VERSION) == PLUGINS_API_VERSION

    # Isolate registries for this activate
    pages_backup = dict(pages.base_pages)
    panes_backup = dict(panes.base_panes)
    actions_backup = dict(contrib.action_contributions)
    try:
        ctx = PluginContext(
            "ab_example",
            application=object(),
            signals=object(),
            settings=_settings_stub(),
        )
        activate(ctx)
        assert "ab_example.page" in pages.base_pages
        assert "ab_example.pane" in panes.base_panes
        assert "ab_example.show_page" in contrib.action_contributions
        assert "ab_example.show_pane" in contrib.action_contributions
        assert "ab_example.settings" not in contrib.settings_chapters  # titled
        assert "Plugin Example" in contrib.settings_chapters
    finally:
        pages.base_pages.clear()
        pages.base_pages.update(pages_backup)
        panes.base_panes.clear()
        panes.base_panes.update(panes_backup)
        contrib.action_contributions.clear()
        contrib.action_contributions.update(actions_backup)


class _settings_stub(dict):
    def __init__(self):
        super().__init__({"plugins": {"enabled_plugins": [], "data": {}}})
        self.global_config = {"plugins": self["plugins"]}
