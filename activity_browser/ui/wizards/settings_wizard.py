# -*- coding: utf-8 -*-
import os
from pathlib import Path
from logging import getLogger

import peewee
from peewee import SqliteDatabase
from qtpy import QtCore, QtWidgets, PYSIDE6
from qtpy.QtCore import Qt

from activity_browser import ab_settings, actions
from activity_browser.mod.bw2data import projects

log = getLogger(__name__)


class SettingsWizard(QtWidgets.QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_project = projects.current
        self.last_bwdir = projects.base_dir

        self.setWindowTitle("Activity Browser Settings")
        self.settings_page = SettingsPage(self)
        self.addPage(self.settings_page)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.button(QtWidgets.QWizard.BackButton).hide()
        self.button(QtWidgets.QWizard.FinishButton).clicked.connect(self.save_settings)
        self.button(QtWidgets.QWizard.CancelButton).clicked.connect(self.cancel)

    def save_settings(self):
        # directory
        current_bw_dir = ab_settings.current_bw_dir
        field = self.field("current_bw_dir")
        if field and field != current_bw_dir:
            ab_settings.custom_bw_dir = field
            ab_settings.current_bw_dir = field
            log.info(f"Saved startup brightway directory as: {field}")

        # project
        field_project = self.field("startup_project")
        current_startup_project = ab_settings.startup_project
        if field_project and field_project != current_startup_project:
            new_startup_project = field_project
            ab_settings.startup_project = new_startup_project
            log.info(f"Saved startup project as: {new_startup_project}")

        ab_settings.write_settings()
        projects.change_base_directories(Path(field))

    def cancel(self):
        log.info("Going back to before settings were changed.")
        if projects.base_dir != self.last_bwdir:
            projects.change_base_directories(Path(self.last_bwdir))


class SettingsPage(QtWidgets.QWizardPage):
    # TODO Look to add a hover event for switching spaces
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = parent
        self.complete = False

        self.startup_project_combobox = QtWidgets.QComboBox(self)
        self.update_project_combo()

        self.registerField(
            "startup_project", self.startup_project_combobox, "currentText"
        )

        self.bwdir_variables = set(ab_settings.custom_bw_dir)
        self.bwdir = QtWidgets.QComboBox(self)

        self.bwdir_browse_button = QtWidgets.QPushButton("Browse", self)
        self.bwdir_remove_button = QtWidgets.QPushButton("Remove", self)
        self.update_combobox(self.bwdir, ab_settings.custom_bw_dir)
        self.restore_defaults_button = QtWidgets.QPushButton("Restore defaults", self)
        self.bwdir_name = QtWidgets.QLineEdit(self.bwdir.currentText(), self)
        self.registerField("current_bw_dir", self.bwdir_name)
        self.message_label = QtWidgets.QLabel("", self)

        # startup project
        self.startup_project_combobox = QtWidgets.QComboBox(self)
        self.update_project_combo()

        self.registerField(
            "startup_project", self.startup_project_combobox, "currentText"
        )

        # light/dark theme
        self.theme_combo = QtWidgets.QComboBox(self)
        self.theme_combo.addItems([
            "Light theme",
            "Dark theme compatibility"
        ])
        self.theme_combo.setCurrentText(ab_settings.theme)
        self.registerField(
            "theme_cbox", self.theme_combo, "currentText"
        )

        # Startup options
        self.startup_groupbox = QtWidgets.QGroupBox("Startup Options", self)
        self.startup_layout = QtWidgets.QGridLayout(self)
        self.startup_layout.addWidget(QtWidgets.QLabel("Brightway Dir: ", self), 0, 0)
        self.startup_layout.addWidget(self.bwdir, 0, 1)
        self.startup_layout.addWidget(self.bwdir_browse_button, 0, 2)
        self.startup_layout.addWidget(self.bwdir_remove_button, 0, 3)
        self.startup_layout.addWidget(QtWidgets.QLabel("Startup Project: ", self), 1, 0)
        self.startup_layout.addWidget(self.startup_project_combobox, 1, 1)
        self.startup_layout.addWidget(QtWidgets.QLabel("Theme: ", self), 2, 0)
        self.startup_layout.addWidget(self.theme_combo, 2, 1)
        self.startup_layout.addWidget(QtWidgets.QLabel("(Requires restart)", self), 2, 2)
        self.startup_layout.addWidget(self.message_label, 2, 0, 1, 3)

        self.startup_groupbox.setLayout(self.startup_layout)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.startup_groupbox)

        if not PYSIDE6:
            self.layout.addWidget(PySide6Switch(self))

        self.layout.addStretch()
        self.layout.addWidget(self.restore_defaults_button)
        self.setLayout(self.layout)
        self.setFinalPage(True)
        self.setButtonText(QtWidgets.QWizard.FinishButton, "Save")

        # signals
        self.startup_project_combobox.currentIndexChanged.connect(self.changed)
        self.bwdir_browse_button.clicked.connect(self.bwdir_browse)
        self.bwdir_remove_button.clicked.connect(self.bwdir_remove)
        self.bwdir.currentTextChanged.connect(self.bwdir_change)
        self.theme_combo.currentTextChanged.connect(self.theme_change)
        self.restore_defaults_button.clicked.connect(self.restore_defaults)

    def bw_projects(self, path: str):
        """Finds the bw_projects from the brightway2 environment provided by path"""
        # open the project database
        database_file = os.path.join(path, "projects.db")
        if not os.path.exists(database_file):
            return []
        db = SqliteDatabase(database_file)

        # find all project names using sql query and return
        try:
            cursor = db.execute_sql('SELECT "name" FROM "projectdataset"')
        except peewee.OperationalError as e:
            if "no such table" in str(e):
                return []
            raise
        return [i[0] for i in cursor.fetchall()]

    def restore_defaults(self):
        self.change_bw_dir(ab_settings.get_default_directory())
        self.startup_project_combobox.setCurrentText(
            ab_settings.get_default_project_name()
        )

    def bwdir_remove(self):
        """
        Removes the project from the AB settings, has additional possiblity of removing data
        contained on 'disk'. Provides a warning before execution.
        """
        hard_deletion = QtWidgets.QMessageBox.question(
            self,
            "Delete Brightway2 directory?",
            "This action will remove the local information only, click"
            "'Yes' to remove\nthe projects. Data on the \"disk\" will remain"
            " untouched and needs to be removed manually",
            QtWidgets.QMessageBox.Yes,
            QtWidgets.QMessageBox.Cancel,
        )
        if hard_deletion == QtWidgets.QMessageBox.Cancel:
            return

        removed_dir = self.bwdir.currentText()
        removed_index = self.bwdir.currentIndex()
        self.bwdir.blockSignals(True)
        self.bwdir.setCurrentIndex(-1)
        self.bwdir.removeItem(removed_index)
        self.bwdir.blockSignals(False)
        self.bwdir_variables.remove(removed_dir)
        ab_settings.remove_custom_bw_dir(removed_dir)

    def bwdir_change(self, path: str):
        """
        Executes on emission of a signal from changes to the QComboBox holding bw2 environments
        Scope: Limited to
            SettingsPage class - can create new environments and bw2data.projects (exceptions are permitted), will update
                contents of the Project QComboBox
            settings::ABSettings - uses but doesn't set bw2 variables, sets variables in the settings file
        """
        self.change_bw_dir(path)

    def theme_change(self, theme: str):
        """Change the theme."""
        if ab_settings.theme != theme:
            ab_settings.theme = theme
            self.changed()

    def bwdir_browse(self):
        """
        Executes on emission of a signal from the browse button
        Scope: Limited to
            SettingsPage class - provides a file path as a string to the QComboBox holding
                bw2data environments
        """
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select a brightway2 database folder"
        )
        if path:
            self.change_bw_dir(os.path.normpath(path))

    def change_bw_dir(self, path):
        """Set startup brightway directory.
        Switch to this directory if user wishes (this will update the "projects" combobox correctly).
        """
        if path not in self.bwdir_variables:
            self.combobox_add_dir(self.bwdir, path)

        self.setField("current_bw_dir", self.bwdir_name.text())
        self.bwdir_name.setText(path)
        self.update_project_combo(path=self.bwdir_name.text())
        self.bwdir.blockSignals(True)
        self.bwdir.setCurrentText(self.bwdir_name.text())
        self.bwdir.blockSignals(False)
        self.changed()

        # if no projects exist in this directory: ask user if he wants to set up a new brightway data directory here
        if not os.path.isfile(os.path.join(path, "projects.db")):
            self.message_label.setText(
                "No projects found in this directory. A new one will be created."
            )
        else:
            self.message_label.setText("")

    def update_project_combo(self, initialization: bool = True, path: str = None):
        """
        Updates the project combobox when loading a new brightway environment
        """
        self.startup_project_combobox.clear()
        if path:
            self.project_names = self.bw_projects(path)
        else:
            self.project_names = self.bw_projects(ab_settings.current_bw_dir)
        if self.project_names:
            self.startup_project_combobox.addItems(self.project_names)
        else:
            log.warning("No projects found in this directory.")

        if ab_settings.startup_project in self.project_names:
            self.startup_project_combobox.setCurrentText(ab_settings.startup_project)
        else:
            self.startup_project_combobox.setCurrentIndex(-1)
        if not initialization:
            self.changed()

    def combobox_add_dir(self, box: QtWidgets.QComboBox, path: str) -> None:
        """Adds a single directory to the QComboBox."""
        box.blockSignals(True)
        box.addItems([path])
        box.blockSignals(False)
        if path not in self.bwdir_variables:
            self.bwdir_variables.add(path)
            ab_settings.custom_bw_dir = path

    def update_combobox(self, box: QtWidgets.QComboBox, labels: list) -> None:
        """Update the combobox menu."""
        correct_settings = False
        current_dir = ab_settings.current_bw_dir
        for i, dir in enumerate(ab_settings.custom_bw_dir):
            self.bwdir_variables.add(dir)
            if dir == current_dir:
                box.blockSignals(True)
                box.clear()
                box.insertItems(0, labels)
                box.blockSignals(False)
                box.setCurrentIndex(i)
                correct_settings = True
        if correct_settings:
            return
        QtWidgets.QMessageBox.warning(
            self,
            "Discrepancy in the ABsettings.json file",
            "The value provided for the current brightway directory does not exist\n"
            "in the available list of directories. Please check the settings file.",
            QtWidgets.QMessageBox.Ok,
        )

    def changed(self):
        self.wizard.button(QtWidgets.QWizard.BackButton).hide()
        self.complete = True
        self.completeChanged.emit()

    def isComplete(self):
        return self.complete


class PySide6Switch(QtWidgets.QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Upgrade GUI back-end", parent)
        self.upgrade_button = actions.PysideUpgrade.get_QButton()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.upgrade_button)
        self.setLayout(layout)

