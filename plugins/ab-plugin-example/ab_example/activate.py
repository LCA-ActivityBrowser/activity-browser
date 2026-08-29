# -*- coding: utf-8 -*-
"""Register Plugin Example contributions with Activity Browser."""
from activity_browser.plugins import PluginContext

from . import ids
from .actions import ShowExamplePage, ShowExamplePane
from .page import ExamplePage
from .pane import ExamplePane
from .settings_chapter import ExampleSettingsChapter


def activate(ctx: PluginContext) -> None:
    ExamplePage.plugin_settings = ctx.settings
    ExampleSettingsChapter.plugin_settings = ctx.settings

    ctx.register_page(
        ids.PAGE,
        ExamplePage,
        title="Plugin Example Page",
        show_by_default=True,
    )
    ctx.register_pane(
        ids.PANE,
        ExamplePane,
        title="Plugin Example Pane",
        show_by_default=True,
    )
    ctx.register_action(ids.SHOW_PAGE, ShowExamplePage)
    ctx.register_action(ids.SHOW_PANE, ShowExamplePane)
    ctx.register_menu_item("Show example page", ids.SHOW_PAGE)
    ctx.register_menu_item("Show example pane", ids.SHOW_PANE)
    ctx.register_settings_chapter(
        ids.SETTINGS,
        ExampleSettingsChapter,
        title="Plugin Example",
    )
