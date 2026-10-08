# -*- coding: utf-8 -*-
import os
from logging import getLogger

from peewee import SqliteDatabase
from PySide2 import QtCore, QtWidgets

from activity_browser import ab_settings
from activity_browser.i18n import _, language_choices
from activity_browser.mod.bw2data import projects

log = getLogger(__name__)

class SettingsWizard(QtWidgets.QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_project = projects.current
        self.last_bwdir = projects.base_dir

        self.setWindowTitle(_("Activity Browser Settings"))
        self.settings_page = SettingsPage(self)
        self.addPage(self.settings_page)
        self.show()
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

        # Language display names are deliberately not persisted.  The stable
        # item data is applied at the next application start.
        language = self.settings_page.language_combo.currentData()
        if language != ab_settings.language:
            ab_settings.language = language
            log.info(f"Saved interface language as: {language} (restart required)")

        ab_settings.write_settings()
        projects.switch_dir(field)

    def cancel(self):
        log.info("Going back to before settings were changed.")
        if projects.base_dir != self.last_bwdir:
            projects.switch_dir(self.last_bwdir)
            projects.set_current(
                self.last_project
            )  # project changes only if directory is changed


class SettingsPage(QtWidgets.QWizardPage):
    # TODO Look to add a hover event for switching spaces
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = parent
        self.complete = False

        # bw dir
        self.bwdir_variables = set()
        self.bwdir = QtWidgets.QComboBox()

        self.bwdir_browse_button = QtWidgets.QPushButton(_("Browse"))
        self.bwdir_remove_button = QtWidgets.QPushButton(_("Remove"))
        self.update_combobox(self.bwdir, ab_settings.custom_bw_dir)
        self.restore_defaults_button = QtWidgets.QPushButton(_("Restore defaults"))
        self.bwdir_name = QtWidgets.QLineEdit(self.bwdir.currentText())
        self.registerField("current_bw_dir", self.bwdir_name)

        # startup project
        self.startup_project_combobox = QtWidgets.QComboBox()
        self.update_project_combo()

        self.registerField(
            "startup_project", self.startup_project_combobox, "currentText"
        )

        # light/dark theme
        self.theme_combo = QtWidgets.QComboBox()
        for theme_code in ("Light theme", "Dark theme compatibility"):
            self.theme_combo.addItem(_(theme_code), theme_code)
        theme_index = self.theme_combo.findData(ab_settings.theme)
        self.theme_combo.setCurrentIndex(max(theme_index, 0))

        # UI labels are translated, while itemData contains the stable codes
        # written to ABsettings.json.
        self.language_combo = QtWidgets.QComboBox()
        self.language_combo.setObjectName("language_combo")
        for language_code, display_name in language_choices():
            self.language_combo.addItem(display_name, language_code)
        language_index = self.language_combo.findData(ab_settings.language)
        self.language_combo.setCurrentIndex(max(language_index, 0))

        # Startup options
        self.startup_groupbox = QtWidgets.QGroupBox(_("Startup Options"))
        self.startup_layout = QtWidgets.QGridLayout()
        self.startup_layout.addWidget(QtWidgets.QLabel(_("Brightway Dir: ")), 0, 0)
        self.startup_layout.addWidget(self.bwdir, 0, 1)
        self.startup_layout.addWidget(self.bwdir_browse_button, 0, 2)
        self.startup_layout.addWidget(self.bwdir_remove_button, 0, 3)
        self.startup_layout.addWidget(QtWidgets.QLabel(_("Startup Project: ")), 1, 0)
        self.startup_layout.addWidget(self.startup_project_combobox, 1, 1)
        self.startup_layout.addWidget(QtWidgets.QLabel(_("Theme: ")), 2, 0)
        self.startup_layout.addWidget(self.theme_combo, 2, 1)
        self.startup_layout.addWidget(QtWidgets.QLabel(_("(Requires restart)")), 2, 2)
        self.startup_layout.addWidget(QtWidgets.QLabel(_("Language: ")), 3, 0)
        self.startup_layout.addWidget(self.language_combo, 3, 1)
        self.startup_layout.addWidget(QtWidgets.QLabel(_("(Requires restart)")), 3, 2)

        self.startup_groupbox.setLayout(self.startup_layout)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.startup_groupbox)
        self.layout.addStretch()
        self.layout.addWidget(self.restore_defaults_button)
        self.setLayout(self.layout)
        self.setFinalPage(True)
        self.setButtonText(QtWidgets.QWizard.FinishButton, _("Save"))

        # signals
        self.startup_project_combobox.currentIndexChanged.connect(self.changed)
        self.bwdir_browse_button.clicked.connect(self.bwdir_browse)
        self.bwdir_remove_button.clicked.connect(self.bwdir_remove)
        self.bwdir.currentTextChanged.connect(self.bwdir_change)
        self.theme_combo.currentIndexChanged.connect(self.theme_change)
        self.language_combo.currentIndexChanged.connect(self.changed)
        self.restore_defaults_button.clicked.connect(self.restore_defaults)

    def bw_projects(self, path: str):
        """Finds the bw_projects from the brightway2 environment provided by path"""
        # open the project database
        db = SqliteDatabase(os.path.join(path, "projects.db"))

        # find all project names using sql query and return
        cursor = db.execute_sql('SELECT "name" FROM "projectdataset"')
        return [i[0] for i in cursor.fetchall()]

    def restore_defaults(self):
        self.change_bw_dir(ab_settings.get_default_directory())
        self.startup_project_combobox.setCurrentText(
            ab_settings.get_default_project_name()
        )
        language_index = self.language_combo.findData(
            ab_settings.get_default_settings()["language"]
        )
        self.language_combo.setCurrentIndex(language_index)

    def bwdir_remove(self):
        """
        Removes the project from the AB settings, has additional possiblity of removing data
        contained on 'disk'. Provides a warning before execution.
        """
        hard_deletion = QtWidgets.QMessageBox.question(
            self,
            _("Delete Brightway2 directory?"),
            _(
                "This action will remove the local information only, click"
                "'Yes' to remove\nthe projects. Data on the \"disk\" will remain"
                " untouched and needs to be removed manually"
            ),
            QtWidgets.QMessageBox.Yes,
            QtWidgets.QMessageBox.Cancel,
        )
        if hard_deletion == QtWidgets.QMessageBox.Cancel:
            return

        #        self.registerField('custom_bw_dir', self.bwdir, '')
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
            SettingsPage class - can create new environments and bw.projects (exceptions are permitted), will update
                contents of the Project QComboBox
            settings::ABSettings - uses but doesn't set bw2 variables, sets variables in the settings file
        """
        self.change_bw_dir(path)

    def theme_change(self, index: int):
        """Change the theme."""
        theme = self.theme_combo.itemData(index)
        if ab_settings.theme != theme:
            ab_settings.theme = theme
            self.changed()

    def bwdir_browse(self):
        """
        Executes on emission of a signal from the browse button
        Scope: Limited to
            SettingsPage class - provides a file path as a string to the QComboBox holding
                bw2 environments
        """
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, _("Select a brightway2 database folder")
        )
        if path:
            self.change_bw_dir(os.path.normpath(path))

    def change_bw_dir(self, path):
        """Set startup brightway directory.
        Switch to this directory if user wishes (this will update the "projects" combobox correctly).
        """

        # if no projects exist in this directory: ask user if he wants to set up a new brightway data directory here
        if not os.path.isfile(os.path.join(path, "projects.db")):
            create_new_directory = QtWidgets.QMessageBox.question(
                self,
                _("New brightway data directory?"),
                _(
                    "This directory does not contain any projects. \n Would you like "
                    "to setup a new brightway data directory here? \n This will close "
                    'the current project and create a "default" project in the new directory.'
                ),
                QtWidgets.QMessageBox.Yes,
                QtWidgets.QMessageBox.Cancel,
            )
            if create_new_directory == QtWidgets.QMessageBox.Cancel:
                return
            else:
                self.bwdir_name.setText(path)
                self.registerField("current_bw_dir", self.bwdir_name)
                self.combobox_add_dir(self.bwdir, path)
                #                ab_settings.current_bw_dir = path
                ab_settings.startup_project = ""
                self.bwdir.blockSignals(True)
                self.bwdir.setCurrentText(self.bwdir_name.text())
                self.bwdir.blockSignals(False)
                self.update_project_combo(path=self.bwdir_name.text())
                self.changed()
        else:  # a project already exists in this directory
            # ask user if to switch directory (which will update the project combobox correctly)
            reply = QtWidgets.QMessageBox.question(
                self,
                _("Continue?"),
                _(
                    "Would you like to switch to this directory now? \nThis will close "
                    'your currently opened project. \nClick "Yes" to be able to choose '
                    "the startup project."
                ),
                QtWidgets.QMessageBox.Yes,
                QtWidgets.QMessageBox.No,
            )
            if path not in self.bwdir_variables:
                self.combobox_add_dir(self.bwdir, path)
            if reply == QtWidgets.QMessageBox.Yes:
                self.bwdir_name.setText(path)
                self.registerField("current_bw_dir", self.bwdir_name)
                #                ab_settings.current_bw_dir = path
                self.update_project_combo(path=self.bwdir_name.text())
            else:
                prev_env_index = self.bwdir.findText(
                    self.bwdir_name.text(), QtCore.Qt.MatchFixedString
                )
                self.bwdir.blockSignals(True)
                self.bwdir.setCurrentIndex(prev_env_index)
                self.bwdir.blockSignals(False)
                self.changed()

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
            ab_settings.startup_project = ""
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
            _("Discrepancy in the ABsettings.json file"),
            _(
                "The value provided for the current brightway directory does not exist\n"
                "in the available list of directories. Please check the settings file."
            ),
            QtWidgets.QMessageBox.Ok,
        )

    def changed(self):
        self.wizard.button(QtWidgets.QWizard.BackButton).hide()
        self.complete = True
        self.completeChanged.emit()

    def isComplete(self):
        return self.complete
