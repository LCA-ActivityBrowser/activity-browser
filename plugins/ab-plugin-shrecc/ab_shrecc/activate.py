# -*- coding: utf-8 -*-
"""Register SHRECC plugin contributions."""
from activity_browser.plugins import PluginContext

from . import ids
from .actions import OpenShreccPage
from .page import ShreccPluginPage
from .settings_chapter import ShreccSettingsChapter


def activate(ctx: PluginContext) -> None:
    signals = ctx.signals
    settings = ctx.settings

    class PluginShreccPage(ShreccPluginPage):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, signals=signals, **kwargs)

    class PluginShreccSettingsChapter(ShreccSettingsChapter):
        def __init__(self, parent=None):
            super().__init__(parent, plugin_settings=settings)

    ctx.register_page(
        ids.PAGE,
        PluginShreccPage,
        title="SHRECC",
        show_by_default=False,
    )
    ctx.register_action(ids.SHOW_PAGE, OpenShreccPage)
    ctx.register_menu_item("Open SHRECC", ids.SHOW_PAGE)
    ctx.register_settings_chapter(
        ids.SETTINGS,
        PluginShreccSettingsChapter,
        title="SHRECC",
    )
