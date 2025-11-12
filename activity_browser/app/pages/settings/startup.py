# -*- coding: utf-8 -*-
import os
from loguru import logger
from pathlib import Path

from peewee import SqliteDatabase, OperationalError
from qtpy import QtCore, QtWidgets

from bw2data import projects

from activity_browser.app import settings
from .base import BaseSettingsChapter


class StartupSettingsChapter(BaseSettingsChapter):
    """Chapter for startup-related settings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Brightway directory
        self.bwdir_variables = set()
        self.bwdir_combo = QtWidgets.QComboBox()
        self.bwdir_browse_button = QtWidgets.QPushButton("Browse")
        self.bwdir_remove_button = QtWidgets.QPushButton("Remove")
        self.update_bwdir_combo()
        
        # Startup project
        self.startup_project_combo = QtWidgets.QComboBox()
        self.update_project_combo()
        
        self.build_layout()
        self.connect_signals()
    
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
        
        layout.addWidget(bwdir_group)
        layout.addWidget(project_group)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def connect_signals(self):
        """Connect signals and slots."""
        self.bwdir_browse_button.clicked.connect(self.browse_bwdir)
        self.bwdir_remove_button.clicked.connect(self.remove_bwdir)
        
        # Emit changed signal when settings change
        self.bwdir_combo.currentTextChanged.connect(lambda: self.changed.emit())
        self.startup_project_combo.currentTextChanged.connect(lambda: self.changed.emit())
    
    def browse_bwdir(self):
        """Browse for a brightway directory."""
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select a brightway2 database folder"
        )
        if not path:
            return
        
        if os.path.isfile(os.path.join(path, "projects.db")):
            self.bwdir_combo.addItem(path)
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "New brightway data directory?",
            'This directory does not contain any projects. Switching to this directory will create a new brightway2 data folder here.',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
        )

        if reply == QtWidgets.QMessageBox.Cancel:
            return
        
        self.bwdir_combo.addItem(path)       

    
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
        
        removed_dir = self.bwdir_combo.currentText()
        removed_index = self.bwdir_combo.currentIndex()
        self.bwdir_combo.setCurrentText(settings["startup"]["brightway_directory"])
        self.bwdir_combo.removeItem(removed_index)
        settings["startup"]["saved_brightway_directories"].remove(removed_dir)
    
    def update_project_combo(self, path: str = None):
        """Update the project combo box."""
        self.startup_project_combo.clear()
        if path:
            project_names = self.get_projects_from_path(path)
        else:
            project_names = self.get_projects_from_path(settings["startup"]["brightway_directory"])
        
        if project_names:
            self.startup_project_combo.addItems(project_names)
        else:
            logger.warning("No projects found in this directory.")
        
        if settings["startup"]["startup_project"] in project_names:
            self.startup_project_combo.setCurrentText(settings["startup"]["startup_project"])
        else:
            settings["startup"]["startup_project"] = ""
            self.startup_project_combo.setCurrentIndex(-1)
    
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
    
    
    def update_bwdir_combo(self):
        """Update the brightway directory combo box."""
        current_dir = settings["startup"]["brightway_directory"]
        available_dirs = settings["startup"].get("saved_brightway_directories", [])
        
        self.bwdir_combo.clear()
        self.bwdir_combo.addItems(available_dirs)
        self.bwdir_combo.setCurrentText(current_dir)

    def get_current_state(self):
        """Get the current state for change tracking."""
        return {
            'bwdir': self.bwdir_combo.currentText(),
            'startup_project': self.startup_project_combo.currentText(),
        }
    
    def save_settings(self):
        """Save startup settings."""
        # Save brightway directory
        current_bw_dir = settings["startup"]["brightway_directory"]
        new_bw_dir = self.bwdir_combo.currentText()
        if new_bw_dir and new_bw_dir != current_bw_dir:
            settings["startup"]["brightway_directory"] = new_bw_dir
            logger.info(f"Saved startup brightway directory as: {new_bw_dir}")
            projects.change_base_directories(Path(new_bw_dir), update=False)
        
        # Save startup project
        current_startup_project = settings["startup"]["startup_project"]
        new_startup_project = self.startup_project_combo.currentText()
        if new_startup_project and new_startup_project != current_startup_project:
            settings["startup"]["startup_project"] = new_startup_project
            logger.info(f"Saved startup project as: {new_startup_project}")
        
        settings.save()
    
    def reset(self):
        """Reset to initial values."""
        self.update_bwdir_combo(settings["startup"]["brightway_directory"])
        self.update_project_combo()
    
    def restore_defaults(self):
        """Restore default values."""
        default_dir = settings["startup"]["brightway_directory"]
        self.change_bwdir(default_dir)
        self.startup_project_combo.setCurrentText(
            "default" if "default" in self.get_projects_from_path(default_dir) else ""
        )
