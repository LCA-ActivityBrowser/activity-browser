"""Settings plugins chapter enable persistence (thin smoke)."""
from activity_browser.app.pages.settings.plugins import PluginsSettingsChapter
from activity_browser.plugins.loader import PluginRecord


def test_plugins_chapter_restart_banner_only_when_pending(qtbot, monkeypatch):
    from activity_browser import app

    records = [
        PluginRecord(
            plugin_id="demo",
            display_name="Demo",
            enabled=True,
            status="loaded",
        )
    ]
    monkeypatch.setattr(
        "activity_browser.app.pages.settings.plugins.plugin_loader.plugin_records",
        records,
    )
    monkeypatch.setattr(
        "activity_browser.app.pages.settings.plugins.plugin_loader.applied_enabled_ids",
        {"demo"},
    )
    original_global = app.settings.global_config.get("plugins")
    try:
        app.settings.global_config["plugins"] = {
            "enabled_plugins": ["demo"],
            "data": {},
        }
        chapter = PluginsSettingsChapter()
        qtbot.addWidget(chapter)
        chapter.reset()
        assert chapter.restart_banner.isHidden()
        chapter.plugin_list.setCurrentRow(0)
        chapter.enable_check.setChecked(False)
        assert not chapter.restart_banner.isHidden()
        chapter.enable_check.setChecked(True)
        assert chapter.restart_banner.isHidden()
    finally:
        if original_global is None:
            app.settings.global_config.pop("plugins", None)
        else:
            app.settings.global_config["plugins"] = original_global


def test_plugins_chapter_persist_enabled(qtbot, monkeypatch):
    from activity_browser import app

    records = [
        PluginRecord(
            plugin_id="demo",
            display_name="Demo",
            enabled=False,
            status="disabled",
        )
    ]
    monkeypatch.setattr(
        "activity_browser.app.pages.settings.plugins.plugin_loader.plugin_records",
        records,
    )
    original_global = app.settings.global_config.get("plugins")
    try:
        app.settings.global_config["plugins"] = {
            "enabled_plugins": [],
            "data": {},
        }
        chapter = PluginsSettingsChapter()
        qtbot.addWidget(chapter)
        chapter.reset()
        assert chapter.plugin_list.count() == 1
        chapter.plugin_list.setCurrentRow(0)
        chapter.enable_check.setChecked(True)
        assert chapter.has_changes()
        chapter.set_settings()
        assert "demo" in app.settings.global_config["plugins"]["enabled_plugins"]
    finally:
        if original_global is None:
            app.settings.global_config.pop("plugins", None)
        else:
            app.settings.global_config["plugins"] = original_global
