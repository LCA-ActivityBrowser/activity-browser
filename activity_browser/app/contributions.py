"""Contribution registries for base composition (Pages/Panes-style).

Plugins (and base chapters) register Actions and Settings chapters here so MainWindow /
MenuBar / SettingsPage can compose without hard-coding every contribution.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Tuple, Type

# id -> ABAction subclass (base + plugin contributions)
action_contributions: Dict[str, Type] = {}

# chapter id -> SettingsChapterContribution (ordered)
settings_chapters: "OrderedDict[str, SettingsChapterContribution]" = OrderedDict()

# Base Plugins menu items: (menu_path_relative_to_Plugins_root, action_id)
plugins_menu_contributions: List[Tuple[str, str]] = []

# plugin_id -> [(relative_menu_path, action_id), ...]
plugin_submenu_items: Dict[str, List[Tuple[str, str]]] = {}

# plugin_id -> display name for Plugins submenu
plugin_display_names: Dict[str, str] = {}


@dataclass(frozen=True)
class SettingsChapterContribution:
    chapter_id: str
    title: str
    chapter_class: Type


def register_action(action_id: str, action_class: Type) -> None:
    if action_id in action_contributions:
        raise ValueError(f"Action contribution id already registered: {action_id!r}")
    action_contributions[action_id] = action_class


def register_settings_chapter(
    chapter_id: str,
    chapter_class: Type,
    *,
    title: str | None = None,
) -> None:
    if chapter_id in settings_chapters:
        raise ValueError(f"Settings chapter already registered: {chapter_id!r}")
    display_title = title if title is not None else chapter_id
    settings_chapters[chapter_id] = SettingsChapterContribution(
        chapter_id, display_title, chapter_class
    )


def register_plugins_menu_item(menu_path: str, action_id: str) -> None:
    plugins_menu_contributions.append((menu_path, action_id))
