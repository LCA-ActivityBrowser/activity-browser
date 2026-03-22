# -*- coding: utf-8 -*-
from loguru import logger
from pathlib import Path

from qtpy import QtWidgets

from bw2data import projects

from activity_browser.app import settings, signals

from .startup import StartupSettingsChapter
from .appearance import AppearanceSettingsChapter
from .project_manager import ProjectManagerSettingsChapter
from .metadatastore import MetadataStoreSettingsChapter
from .plugins import PluginsSettingsChapter


class SettingsPage(QtWidgets.QWidget):
    """Settings page with a sidebar navigation for different settings chapters."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsPage")
        
        # Store initial state for cancel functionality
        self.last_project = projects.current
        self.last_bwdir = projects._base_data_dir
        
        # Chapter list (sidebar)
        self.chapter_list = QtWidgets.QListWidget()
        self.chapter_list.setMaximumWidth(200)
        self.chapter_list.setMinimumWidth(100)
        self.chapter_list.setSpacing(2)
        
        # Stacked widget for chapter content
        self.content_stack = QtWidgets.QStackedWidget()
        
        # Create chapters
        self.startup_chapter = StartupSettingsChapter(self)
        self.appearance_chapter = AppearanceSettingsChapter(self)
        self.project_manager_chapter = ProjectManagerSettingsChapter(self)
        self.metadatastore_chapter = MetadataStoreSettingsChapter(self)
        self.plugins_chapter = PluginsSettingsChapter(self)

        # Add chapters to the stack
        self.chapters = [
            ("Startup", self.startup_chapter),
            ("Appearance", self.appearance_chapter),
            ("Projects", self.project_manager_chapter),
            ("Metadata Store", self.metadatastore_chapter),
            ("Plugins", self.plugins_chapter),
        ]
        
        for name, widget in self.chapters:
            self.chapter_list.addItem(name)
            self.content_stack.addWidget(widget)
        
        # Select first chapter by default
        self.chapter_list.setCurrentRow(0)
        
        # Buttons
        self.button_layout = QtWidgets.QHBoxLayout()
        self.save_button = QtWidgets.QPushButton("Save")
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.restore_defaults_button = QtWidgets.QPushButton("Restore Defaults")
        
        self.button_layout.addWidget(self.restore_defaults_button)
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.cancel_button)
        self.button_layout.addWidget(self.save_button)
        
        # Build layout
        self.build_layout()
        self.connect_signals()
        
        # Store initial state and disable save button initially
        self.save_button.setEnabled(False)
    
    def build_layout(self):
        """Build the main layout with sidebar and content area."""
        # Main content area with sidebar and content
        content_layout = QtWidgets.QHBoxLayout()
        content_layout.addWidget(self.chapter_list)
        
        # Add vertical separator
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.VLine)
        separator.setFrameShadow(QtWidgets.QFrame.Sunken)
        content_layout.addWidget(separator)
        
        content_layout.addWidget(self.content_stack, 1)
        
        # Main layout
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.addLayout(content_layout, 1)
        main_layout.addLayout(self.button_layout)
        
        self.setLayout(main_layout)
        
        # Set minimum size for resizability
        self.setMinimumSize(400, 300)
    
    def connect_signals(self):
        """Connect signals and slots."""
        signals.project.changed.connect(self.reset_all)

        self.chapter_list.currentRowChanged.connect(self.content_stack.setCurrentIndex)
        self.save_button.clicked.connect(self.save_settings)
        self.cancel_button.clicked.connect(self.cancel_settings)
        self.restore_defaults_button.clicked.connect(self.restore_defaults)
        
        # Connect change signals from each chapter
        for name, chapter in self.chapters:
            if hasattr(chapter, 'changed'):
                chapter.changed.connect(self.on_chapter_changed)

    def on_chapter_changed(self):
        """Called when any chapter's settings change."""
        has_changes = self.has_changes()
        self.save_button.setEnabled(has_changes)
    
    def has_changes(self):
        """Check if any chapter has unsaved changes."""
        for name, chapter in self.chapters:
            if hasattr(chapter, 'has_changes') and chapter.has_changes():
                return True
        return False
    
    def save_settings(self):
        """Save all settings from all chapters."""
        for name, chapter in self.chapters:
            if hasattr(chapter, 'set_settings'):
                chapter.set_settings()
        
        settings.save()
        logger.info("Settings saved successfully")
        
        # Reset all chapters to the new saved state
        self.reset_all()
    
    def cancel_settings(self):
        """Cancel changes and revert to previous state."""
        logger.info("Cancelling settings changes")
        self.reset_all()
            
    def restore_defaults(self):
        """Restore default settings for the current chapter."""
        logger.info("Restoring default settings")
        settings.restore_defaults()
        self.reset_all()
    
    def reset_all(self):
        """Reset all chapters to their initial states."""
        for name, chapter in self.chapters:
            if hasattr(chapter, 'reset'):
                chapter.reset()
        self.save_button.setEnabled(False)

