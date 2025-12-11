# -*- coding: utf-8 -*-
from loguru import logger
from qtpy import QtWidgets

from activity_browser.app import settings
from activity_browser.app.pages.settings.base import BaseSettingsChapter


class MetadataStoreSettingsChapter(BaseSettingsChapter):
    """Chapter for metadatastore-related settings."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Caching enabled checkbox
        self.caching_checkbox = QtWidgets.QCheckBox("Enable caching")
        self.caching_checkbox.setToolTip(
            "Enable caching for faster data access. "
            "Disable if you experience memory issues or want to force fresh data loading."
        )

        # Searcher enabled checkbox
        self.searcher_checkbox = QtWidgets.QCheckBox("Enable searcher")
        self.searcher_checkbox.setToolTip(
            "Enable the full-text search functionality for activities and metadata. "
            "Disable if you experience performance issues with large databases."
        )

        self.build_layout()
        self.connect_signals()
        self.reset()

    def connect_signals(self):
        """Connect signals and slots."""
        # Emit changed signal when settings change
        self.caching_checkbox.stateChanged.connect(lambda: self.changed.emit())
        self.searcher_checkbox.stateChanged.connect(lambda: self.changed.emit())

    def build_layout(self):
        """Build the chapter layout."""
        layout = QtWidgets.QVBoxLayout()

        # Metadata store group
        metadatastore_group = QtWidgets.QGroupBox("Metadata Store Options")
        metadatastore_layout = QtWidgets.QVBoxLayout()

        metadatastore_layout.addWidget(self.caching_checkbox)
        metadatastore_layout.addWidget(self.searcher_checkbox)

        # Add description label
        description = QtWidgets.QLabel(
            "These settings control the behavior of the metadata store, "
            "which manages activity and exchange metadata for improved performance."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: gray; font-size: 10pt;")
        metadatastore_layout.addWidget(description)

        metadatastore_group.setLayout(metadatastore_layout)

        layout.addWidget(metadatastore_group)
        layout.addStretch()

        self.setLayout(layout)

    # --- Settings management methods --- #
    def reset(self):
        """(Re)set to initial values."""
        try:
            self.caching_checkbox.setChecked(
                settings["metadatastore"]["caching_enabled"]
            )
            self.searcher_checkbox.setChecked(
                settings["metadatastore"]["searcher_enabled"]
            )
        except (KeyError, TypeError):
            # Use defaults if settings don't exist yet
            self.caching_checkbox.setChecked(True)
            self.searcher_checkbox.setChecked(True)

    def has_changes(self):
        """Check if there are unsaved changes."""
        try:
            current_state = {
                'caching_enabled': self.caching_checkbox.isChecked(),
                'searcher_enabled': self.searcher_checkbox.isChecked(),
            }
            initial_state = {
                'caching_enabled': settings["metadatastore"]["caching_enabled"],
                'searcher_enabled': settings["metadatastore"]["searcher_enabled"],
            }
            return current_state != initial_state
        except (KeyError, TypeError):
            # If settings don't exist, check against defaults
            return (self.caching_checkbox.isChecked() != True or
                    self.searcher_checkbox.isChecked() != True)

    def set_settings(self):
        """Save metadatastore settings."""
        if "metadatastore" not in settings.global_config:
            settings.global_config["metadatastore"] = {}

        settings.global_config["metadatastore"]["caching_enabled"] = self.caching_checkbox.isChecked()
        settings.global_config["metadatastore"]["searcher_enabled"] = self.searcher_checkbox.isChecked()

        logger.info(
            f"Metadatastore settings saved: "
            f"caching={self.caching_checkbox.isChecked()}, "
            f"searcher={self.searcher_checkbox.isChecked()}"
        )

