# -*- coding: utf-8 -*-
import os
from loguru import logger
from pathlib import Path

from peewee import SqliteDatabase, OperationalError
from qtpy import QtCore, QtWidgets

from bw2data import projects

from activity_browser.app import settings, panes, pages
from .base import BaseSettingsChapter


class StartupSettingsChapter(BaseSettingsChapter):
    """Chapter for startup-related settings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Brightway directory
        self.bwdir_combo = QtWidgets.QComboBox()
        self.bwdir_browse_button = QtWidgets.QPushButton("Browse")
        self.bwdir_remove_button = QtWidgets.QPushButton("Remove")
        
        # Startup project
        self.startup_project_combo = QtWidgets.QComboBox()
        
        # Shown panes checkboxes
        self.pane_checkboxes = {}
        self.available_panes = list(panes.base_panes.keys())
        for pane_name in self.available_panes:
            self.pane_checkboxes[pane_name] = QtWidgets.QCheckBox(pane_name)
        
        # Shown pages checkboxes
        self.page_checkboxes = {}
        self.available_pages = list(pages.base_pages.keys())
        for page_name in self.available_pages:
            self.page_checkboxes[page_name] = QtWidgets.QCheckBox(page_name)
        
        self.build_layout()
        self.connect_signals()
        self.reset()
    
    def build_layout(self):
        """Build the chapter layout."""
        layout = QtWidgets.QVBoxLayout()
        
        # Brightway directory section
        bwdir_group = QtWidgets.QGroupBox("Brightway Directory")
        bwdir_layout = QtWidgets.QGridLayout()
        bwdir_layout.addWidget(QtWidgets.QLabel("Directory:"), 0, 0)
        bwdir_layout.addWidget(self.bwdir_combo, 0, 1)
        bwdir_layout.addWidget(self.bwdir_browse_button, 0, 2)
        bwdir_layout.addWidget(self.bwdir_remove_button, 0, 3)
        bwdir_group.setLayout(bwdir_layout)
        
        # Startup project section
        project_group = QtWidgets.QGroupBox("Startup Project")
        project_layout = QtWidgets.QGridLayout()
        project_layout.addWidget(QtWidgets.QLabel("Project:"), 0, 0)
        project_layout.addWidget(self.startup_project_combo, 0, 1)
        project_group.setLayout(project_layout)
        
        # Shown panes section
        panes_group = QtWidgets.QGroupBox("Panes shown at startup")
        panes_layout = QtWidgets.QVBoxLayout()
        for pane_name in self.available_panes:
            panes_layout.addWidget(self.pane_checkboxes[pane_name])
        panes_group.setLayout(panes_layout)
        
        # Shown pages section
        pages_group = QtWidgets.QGroupBox("Pages shown at startup")
        pages_layout = QtWidgets.QVBoxLayout()
        for page_name in self.available_pages:
            pages_layout.addWidget(self.page_checkboxes[page_name])
        pages_group.setLayout(pages_layout)
        
        layout.addWidget(bwdir_group)
        layout.addWidget(project_group)
        layout.addWidget(panes_group)
        layout.addWidget(pages_group)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def connect_signals(self):
        """Connect signals and slots."""
        self.bwdir_browse_button.clicked.connect(self.browse_bwdir)
        self.bwdir_remove_button.clicked.connect(self.remove_bwdir)
        
        # Emit changed signal when settings change
        self.bwdir_combo.currentTextChanged.connect(lambda: self.changed.emit())
        self.bwdir_combo.currentTextChanged.connect(self.show_virtual_projects)
        self.startup_project_combo.currentTextChanged.connect(lambda: self.changed.emit())
        
        # Connect checkboxes
        for checkbox in self.pane_checkboxes.values():
            checkbox.stateChanged.connect(lambda: self.changed.emit())
        for checkbox in self.page_checkboxes.values():
            checkbox.stateChanged.connect(lambda: self.changed.emit())
    
    # --- Settings management methods --- #
    def reset(self):
        """(Re)set to initial values."""
        self.bwdir_combo.clear()
        self.bwdir_combo.addItems(settings["startup"].get("saved_brightway_directories", []))
        self.bwdir_combo.setCurrentText(settings["startup"]["brightway_directory"])

        self.startup_project_combo.clear()
        self.startup_project_combo.addItems(self.get_projects_from_path(settings["startup"]["brightway_directory"]))
        self.startup_project_combo.setCurrentText(settings["startup"]["startup_project"])
        
        # Set pane checkboxes
        shown_panes = settings["startup"].get("shown_panes", [])
        for pane_name, checkbox in self.pane_checkboxes.items():
            checkbox.setChecked(pane_name in shown_panes)
        
        # Set page checkboxes
        shown_pages = settings["startup"].get("shown_pages", [])
        for page_name, checkbox in self.page_checkboxes.items():
            checkbox.setChecked(page_name in shown_pages)

    def has_changes(self):
        """Check if there are unsaved changes."""
        current_state = {
            'brightway_directory': self.bwdir_combo.currentText(),
            'saved_brightway_directories': [self.bwdir_combo.itemText(i) for i in range(self.bwdir_combo.count())],
            'startup_project': self.startup_project_combo.currentText(),
            'shown_panes': [name for name, cb in self.pane_checkboxes.items() if cb.isChecked()],
            'shown_pages': [name for name, cb in self.page_checkboxes.items() if cb.isChecked()],
        }
        initial_state = {
            'brightway_directory': settings["startup"]["brightway_directory"],
            'saved_brightway_directories': settings["startup"].get("saved_brightway_directories", []),
            'startup_project':  settings["startup"]["startup_project"],
            'shown_panes': settings["startup"].get("shown_panes", []),
            'shown_pages': settings["startup"].get("shown_pages", []),
        }
        return current_state != initial_state
    
    def set_settings(self):
        """Save startup settings."""

        settings["startup"]["brightway_directory"] = self.bwdir_combo.currentText()
        settings["startup"]["saved_brightway_directories"] = [self.bwdir_combo.itemText(i) for i in range(self.bwdir_combo.count())]
        settings["startup"]["startup_project"] = self.startup_project_combo.currentText()
        
        # Save shown panes and pages
        settings["startup"]["shown_panes"] = [name for name, cb in self.pane_checkboxes.items() if cb.isChecked()]
        settings["startup"]["shown_pages"] = [name for name, cb in self.page_checkboxes.items() if cb.isChecked()]
    
    # --- Helper methods --- #    
    def browse_bwdir(self):
        """Browse for a brightway directory."""
        path = Path(QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select a brightway2 database folder"
        ))
        if not path:
            return
        
        if (path / "projects.db").is_file():
            self.bwdir_combo.addItem(str(path))
            self.bwdir_combo.setCurrentText(str(path))
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "New brightway data directory?",
            'This directory does not contain any projects. Switching to this directory will create a new brightway2 data folder here.',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
        )

        if reply == QtWidgets.QMessageBox.Cancel:
            return
        
        self.bwdir_combo.addItem(str(path))       
        self.bwdir_combo.setCurrentText(str(path))

    def remove_bwdir(self):
        """Remove the selected brightway directory from the list."""
        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete Brightway2 directory?",
            "This action will remove the local information only, click 'Yes' to remove\n"
            "the projects. Data on the 'disk' will remain untouched and needs to be removed manually",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
        )
        if reply == QtWidgets.QMessageBox.Cancel:
            return
        
        removed_index = self.bwdir_combo.currentIndex()
        self.bwdir_combo.setCurrentText(settings["startup"]["brightway_directory"])
        self.bwdir_combo.removeItem(removed_index)

    def show_virtual_projects(self):
        """Show projects from the virtual Brightway directory."""
        virtual_projects = self.get_projects_from_path(self.bwdir_combo.currentText())
        startup = settings["startup"]["startup_project"]

        self.startup_project_combo.clear()
        self.startup_project_combo.addItems(virtual_projects if virtual_projects else ["default"])
        self.startup_project_combo.setCurrentText(startup if startup in virtual_projects else "default")

    def get_projects_from_path(self, path: str):
        """Get project names from a brightway directory."""
        database_file = os.path.join(path, "projects.db")
        if not os.path.exists(database_file):
            return []
        db = SqliteDatabase(database_file)
        
        try:
            cursor = db.execute_sql('SELECT "name" FROM "projectdataset"')
        except OperationalError as e:
            if "no such table" in str(e):
                return []
            raise
        return [i[0] for i in cursor.fetchall()]
