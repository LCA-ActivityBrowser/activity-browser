# -*- coding: utf-8 -*-
"""Base Settings chapters registered with the contribution registry.

Base chapters ship with Activity Browser (same idea as ``pages.base_pages``).
Plugins add chapters later via ``PluginContext.register_settings_chapter``.
"""
from __future__ import annotations

from typing import Iterable, Tuple, Type

from activity_browser.app import contributions

from .appearance import AppearanceSettingsChapter
from .metadatastore import MetadataStoreSettingsChapter
from .plugins import PluginsSettingsChapter
from .project_manager import ProjectManagerSettingsChapter
from .startup import StartupSettingsChapter

# Sidebar order for base Settings chapters.
BASE_SETTINGS_CHAPTERS: Tuple[Tuple[str, Type], ...] = (
    ("Startup", StartupSettingsChapter),
    ("Appearance", AppearanceSettingsChapter),
    ("Projects", ProjectManagerSettingsChapter),
    ("Metadata Store", MetadataStoreSettingsChapter),
    ("Plugins", PluginsSettingsChapter),
)


def register_base_settings_chapters(
    chapters: Iterable[Tuple[str, Type]] = BASE_SETTINGS_CHAPTERS,
) -> None:
    """Register base chapters; safe to call more than once."""
    for title, chapter_class in chapters:
        if title not in contributions.settings_chapters:
            contributions.register_settings_chapter(title, chapter_class)
