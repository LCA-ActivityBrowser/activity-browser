# -*- coding: utf-8 -*-
from .settings_page import SettingsPage
from .base import BaseSettingsChapter
from .startup import StartupSettingsChapter
from .appearance import AppearanceSettingsChapter
from .project_manager import ProjectManagerSettingsChapter
from .metadatastore import MetadataStoreSettingsChapter
from .plugins import PluginsSettingsChapter
from .base_chapters import BASE_SETTINGS_CHAPTERS, register_base_settings_chapters

register_base_settings_chapters()

__all__ = [
    "SettingsPage",
    "BaseSettingsChapter",
    "StartupSettingsChapter",
    "AppearanceSettingsChapter",
    "ProjectManagerSettingsChapter",
    "MetadataStoreSettingsChapter",
    "PluginsSettingsChapter",
    "BASE_SETTINGS_CHAPTERS",
    "register_base_settings_chapters",
]
