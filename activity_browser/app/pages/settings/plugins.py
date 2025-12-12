# -*- coding: utf-8 -*-
import importlib.util
from loguru import logger
from qtpy import QtWidgets

from activity_browser.app import settings
from activity_browser.app.pages.settings.base import BaseSettingsChapter
from activity_browser.ui.icons import qicons


class PluginsSettingsChapter(BaseSettingsChapter):
    """Chapter for plugin-related settings."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # List widget to display enabled plugins
        self.plugin_list = QtWidgets.QListWidget()
        self.plugin_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        # Input field for adding new plugins
        self.plugin_input = QtWidgets.QLineEdit()
        self.plugin_input.setPlaceholderText("Enter Python package name (e.g., my_plugin)")

        # Buttons
        self.add_button = QtWidgets.QPushButton("Add")
        self.remove_button = QtWidgets.QPushButton("Remove")
        self.remove_button.setEnabled(False)

        self.build_layout()
        self.connect_signals()
        self.reset()

    def connect_signals(self):
        """Connect signals and slots."""
        self.add_button.clicked.connect(self.add_plugin)
        self.remove_button.clicked.connect(self.remove_plugin)
        self.plugin_input.returnPressed.connect(self.add_plugin)
        self.plugin_list.itemSelectionChanged.connect(self.on_selection_changed)
        self.plugin_list.model().rowsInserted.connect(lambda: self.changed.emit())
        self.plugin_list.model().rowsRemoved.connect(lambda: self.changed.emit())

    def build_layout(self):
        """Build the chapter layout."""
        layout = QtWidgets.QVBoxLayout()

        # Plugin list section
        plugin_group = QtWidgets.QGroupBox("Enabled Plugins")
        plugin_layout = QtWidgets.QVBoxLayout()

        # Description label
        description = QtWidgets.QLabel(
            "Add Python packages that should be imported as plugins.\n"
            "These packages will be loaded when Activity Browser starts."
        )
        description.setWordWrap(True)
        plugin_layout.addWidget(description)

        # List widget
        plugin_layout.addWidget(self.plugin_list)

        # Input section
        input_layout = QtWidgets.QHBoxLayout()
        input_layout.addWidget(self.plugin_input)
        input_layout.addWidget(self.add_button)
        plugin_layout.addLayout(input_layout)

        # Remove button
        plugin_layout.addWidget(self.remove_button)

        plugin_group.setLayout(plugin_layout)

        layout.addWidget(plugin_group)
        layout.addStretch()

        self.setLayout(layout)

    def on_selection_changed(self):
        """Enable/disable remove button based on selection."""
        self.remove_button.setEnabled(len(self.plugin_list.selectedItems()) > 0)

    def module_exists(self, module_name):
        """Check if a module can be found/imported."""
        try:
            spec = importlib.util.find_spec(module_name)
            return spec is not None
        except (ImportError, ModuleNotFoundError, ValueError, AttributeError):
            return False

    def add_plugin_to_list(self, plugin_name):
        """Add a plugin to the list widget with appropriate icon."""
        item = QtWidgets.QListWidgetItem(plugin_name)

        # Check if module exists and add warning icon if not
        if not self.module_exists(plugin_name):
            # Use standard warning icon
            icon = qicons.critical
            item.setIcon(icon)
            item.setToolTip(f"Warning: Module '{plugin_name}' not found. "
                          "Make sure it is installed before starting Activity Browser.")
            logger.warning(f"Plugin module '{plugin_name}' not found")
        else:
            icon = qicons.empty
            item.setIcon(icon)
            item.setToolTip(f"Module '{plugin_name}' is available")

        self.plugin_list.addItem(item)

    def add_plugin(self):
        """Add a plugin to the list."""
        plugin_name = self.plugin_input.text().strip()
        if not plugin_name:
            return

        # Check if plugin already exists
        existing_items = [self.plugin_list.item(i).text() for i in range(self.plugin_list.count())]
        if plugin_name in existing_items:
            QtWidgets.QMessageBox.warning(
                self,
                "Duplicate Plugin",
                f"The plugin '{plugin_name}' is already in the list."
            )
            return

        # Add to list with icon
        self.add_plugin_to_list(plugin_name)
        self.plugin_input.clear()
        logger.debug(f"Added plugin: {plugin_name}")
        self.changed.emit()

    def remove_plugin(self):
        """Remove selected plugin from the list."""
        selected_items = self.plugin_list.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            plugin_name = item.text()
            row = self.plugin_list.row(item)
            self.plugin_list.takeItem(row)
            logger.debug(f"Removed plugin: {plugin_name}")

        self.changed.emit()

    # --- Settings management methods --- #
    def reset(self):
        """(Re)set to initial values."""
        self.plugin_list.clear()
        enabled_plugins = settings["plugins"].get("enabled_plugins", [])
        for plugin in enabled_plugins:
            self.add_plugin_to_list(plugin)
        self.plugin_input.clear()
        self.remove_button.setEnabled(False)

    def has_changes(self):
        """Check if there are unsaved changes."""
        current_plugins = [self.plugin_list.item(i).text() for i in range(self.plugin_list.count())]
        saved_plugins = settings["plugins"].get("enabled_plugins", [])
        return current_plugins != saved_plugins

    def set_settings(self):
        """Save plugin settings."""
        current_plugins = [self.plugin_list.item(i).text() for i in range(self.plugin_list.count())]
        settings["plugins"]["enabled_plugins"] = current_plugins
        logger.info(f"Saved enabled plugins: {current_plugins}")

