# -*- coding: utf-8 -*-
"""Register Plugin Example contributions with Activity Browser.

Pages/chapters that need ``ctx.settings`` or ``ctx.signals`` are registered as
thin subclasses defined here (constructor injection). That stays correct when
several plugins are enabled.
"""
from activity_browser.plugins import PluginContext

from . import ids
from .actions import ShowExamplePage, ShowExamplePane
from .page import ExamplePage
from .pane import ExamplePane
from .settings_chapter import ExampleSettingsChapter


def activate(ctx: PluginContext) -> None:
    settings = ctx.settings
    signals = ctx.signals

    class PluginExamplePage(ExamplePage):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, settings=settings, signals=signals, **kwargs)

    class PluginExampleSettingsChapter(ExampleSettingsChapter):
        def __init__(self, parent=None):
            super().__init__(parent, plugin_settings=settings)

    ctx.register_page(
        ids.PAGE,
        PluginExamplePage,
        title="Plugin Example Page",
    )
    ctx.register_pane(
        ids.PANE,
        ExamplePane,
        title="Plugin Example Pane",
    )
    ctx.register_action(ids.SHOW_PAGE, ShowExamplePage)
    ctx.register_action(ids.SHOW_PANE, ShowExamplePane)
    ctx.register_menu_item("Show example page", ids.SHOW_PAGE)
    ctx.register_menu_item("Show example pane", ids.SHOW_PANE)
    ctx.register_settings_chapter(ids.SETTINGS, PluginExampleSettingsChapter, title="Plugin Example")
