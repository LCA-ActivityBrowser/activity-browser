# -*- coding: utf-8 -*-
"""Public plugins API (stable under PLUGINS_API_VERSION)."""

from activity_browser.app.actions.base import ABAction
from activity_browser.app.pages.settings.base import BaseSettingsChapter
from activity_browser.ui.widgets.abstract_page import ABAbstractPage
from activity_browser.ui.widgets.abstract_pane import ABAbstractPane

from .context import PluginContext
from .host_ui import reveal_page, reveal_pane
from .safe_bw_connection import safe_bw_connection
from .version import PLUGINS_API_VERSION

__all__ = [
    "PLUGINS_API_VERSION",
    "PluginContext",
    "ABAbstractPage",
    "ABAbstractPane",
    "ABAction",
    "BaseSettingsChapter",
    "reveal_page",
    "reveal_pane",
    "safe_bw_connection",
]
