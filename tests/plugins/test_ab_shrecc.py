"""SHRECC plugin discovery tests (skip if package not installed)."""
import pytest
from importlib.metadata import entry_points


def _shrecc_ep():
    return next(
        (ep for ep in entry_points(group="activity_browser.plugins") if ep.name == "ab_shrecc"),
        None,
    )


pytestmark = pytest.mark.skipif(
    _shrecc_ep() is None,
    reason="Install with: pip install -e ./plugins/ab-plugin-shrecc",
)


def test_ab_shrecc_entry_point_loadable():
    ep = _shrecc_ep()
    activate = ep.load()
    assert callable(activate)


def test_ab_shrecc_activate_registers_ids(monkeypatch):
    from activity_browser.app import contributions as contrib
    from activity_browser.app import pages
    from activity_browser.plugins.context import PluginContext
    from activity_browser.plugins.version import PLUGINS_API_VERSION

    ep = _shrecc_ep()
    activate = ep.load()
    import ab_shrecc

    assert str(ab_shrecc.PLUGINS_API_VERSION) == PLUGINS_API_VERSION

    pages_backup = dict(pages.base_pages)
    actions_backup = dict(contrib.action_contributions)
    chapters_backup = contrib.settings_chapters.copy()
    submenu_backup = {k: list(v) for k, v in contrib.plugin_submenu_items.items()}
    try:
        ctx = PluginContext(
            "ab_shrecc",
            application=object(),
            signals=object(),
            settings=_settings_stub(),
        )
        activate(ctx)
        assert "ab_shrecc.page" in pages.base_pages
        assert "ab_shrecc.show_page" in contrib.action_contributions
        assert "ab_shrecc.settings" in contrib.settings_chapters
        assert contrib.settings_chapters["ab_shrecc.settings"].title == "SHRECC"
        submenu = contrib.plugin_submenu_items.get("ab_shrecc", [])
        assert any(item[1] == "ab_shrecc.show_page" for item in submenu)
        startup = ctx._settings.global_config.get("startup", {})
        assert "ab_shrecc.page" not in startup.get("shown_pages", [])
    finally:
        pages.base_pages.clear()
        pages.base_pages.update(pages_backup)
        contrib.action_contributions.clear()
        contrib.action_contributions.update(actions_backup)
        contrib.settings_chapters.clear()
        contrib.settings_chapters.update(chapters_backup)
        contrib.plugin_submenu_items.clear()
        contrib.plugin_submenu_items.update(submenu_backup)


class _settings_stub(dict):
    def __init__(self):
        super().__init__({"plugins": {"enabled_plugins": [], "data": {}}})
        self.global_config = {"plugins": self["plugins"], "startup": {"shown_pages": []}}
