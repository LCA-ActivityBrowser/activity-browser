"""Contribution registries for base composition (Pages/Panes-style).

Plugins (and base chapters) register Actions and Settings chapters here so MainWindow /
MenuBar / SettingsPage can compose without hard-coding every contribution.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Dict, List, Optional, Tuple, Type

# id -> ABAction subclass (base + plugin contributions)
action_contributions: Dict[str, Type] = {}

# display title -> BaseSettingsChapter subclass (ordered)
settings_chapters: "OrderedDict[str, Type]" = OrderedDict()

# Base Plugins menu items: (menu_path_relative_to_Plugins_root, action_id)
plugins_menu_contributions: List[Tuple[str, str]] = []

# plugin_id -> [(relative_menu_path, action_id), ...]
plugin_submenu_items: Dict[str, List[Tuple[str, str]]] = {}

# plugin_id -> display name for Plugins submenu
plugin_display_names: Dict[str, str] = {}

# contribution id -> show_by_default for pages/panes
page_show_defaults: Dict[str, bool] = {}
pane_show_defaults: Dict[str, bool] = {}


def register_action(action_id: str, action_class: Type) -> None:
    if action_id in action_contributions:
        raise ValueError(f"Action contribution id already registered: {action_id!r}")
    action_contributions[action_id] = action_class


def register_settings_chapter(title: str, chapter_class: Type) -> None:
    if title in settings_chapters:
        raise ValueError(f"Settings chapter already registered: {title!r}")
    settings_chapters[title] = chapter_class


def register_plugins_menu_item(menu_path: str, action_id: str) -> None:
    plugins_menu_contributions.append((menu_path, action_id))
