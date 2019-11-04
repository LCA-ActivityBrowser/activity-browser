# -*- coding: utf-8 -*-
import brightway2 as bw
from PySide2 import QtWidgets, QtGui
import os

from activity_browser.app.signals import signals
from activity_browser.app.settings import ab_settings


class SettingsWizard(QtWidgets.QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_project = bw.projects.current
        self.last_bwdir = bw.projects._base_data_dir

        self.setWindowTitle('Activity Browser Settings')
        self.settings_page = SettingsPage(self)
        self.addPage(self.settings_page)
        self.show()
        self.button(QtWidgets.QWizard.BackButton).hide()
        self.button(QtWidgets.QWizard.FinishButton).clicked.connect(self.save_settings)
        self.button(QtWidgets.QWizard.CancelButton).clicked.connect(self.cancel)

    def save_settings(self):
        # directory
        current_bw_dir = ab_settings.custom_bw_dir
        if self.field('custom_bw_dir') and self.field('custom_bw_dir') != current_bw_dir:
            custom_bw_dir = self.field('custom_bw_dir')
            ab_settings.custom_bw_dir = custom_bw_dir
            print("Saved startup brightway directory as: ", custom_bw_dir)

        # project
        current_startup_project = ab_settings.startup_project
        if self.field('startup_project') != current_startup_project:
            new_startup_project = self.field('startup_project')
            ab_settings.startup_project = new_startup_project
            print("Saved startup project as: ", new_startup_project)

        ab_settings.write_settings()

    def cancel(self):
        print("Going back to before settings were changed.")
        if bw.projects._base_data_dir != self.last_bwdir:
            signals.switch_bw2_dir_path.emit(self.last_bwdir)
            signals.change_project.emit(self.last_project)  # project changes only if directory is changed


class SettingsPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = parent
        self.complete = False

        self.startup_project_combobox = QtWidgets.QComboBox()
        self.update_project_combo()

        self.registerField('startup_project', self.startup_project_combobox, 'currentText')

        self.bwdir_edit = QtWidgets.QLineEdit()
        self.bwdir_edit.setPlaceholderText(ab_settings.custom_bw_dir)
        self.bwdir_edit.setReadOnly(True)
        self.registerField('custom_bw_dir', self.bwdir_edit)
        self.bwdir_browse_button = QtWidgets.QPushButton('Browse')

        self.restore_defaults_button = QtWidgets.QPushButton('Restore defaults')

        # Startup options
        self.startup_groupbox = QtWidgets.QGroupBox('Startup Options')
        self.startup_layout = QtWidgets.QGridLayout()
        self.startup_layout.addWidget(QtWidgets.QLabel('Brightway Dir: '), 0, 0)
        self.startup_layout.addWidget(self.bwdir_edit, 0, 1)
        self.startup_layout.addWidget(self.bwdir_browse_button, 0, 2)
        self.startup_layout.addWidget(QtWidgets.QLabel('Startup Project: '), 1, 0)
        self.startup_layout.addWidget(self.startup_project_combobox, 1, 1)

        self.startup_groupbox.setLayout(self.startup_layout)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.startup_groupbox)
        self.layout.addStretch()
        self.layout.addWidget(self.restore_defaults_button)
        self.setLayout(self.layout)

        self.setFinalPage(True)
        self.setButtonText(QtWidgets.QWizard.FinishButton, 'Save')

        # signals
        self.startup_project_combobox.currentIndexChanged.connect(self.changed)
        self.bwdir_browse_button.clicked.connect(self.bwdir_browse)
        self.bwdir_edit.textChanged.connect(self.changed)
        self.restore_defaults_button.clicked.connect(self.restore_defaults)

    def restore_defaults(self):
        self.change_bw_dir(ab_settings.get_default_directory())
        self.startup_project_combobox.setCurrentText(ab_settings.get_default_project_name())

    def bwdir_browse(self):
        path = QtWidgets.QFileDialog().getExistingDirectory(
            None, "Select a brightway2 database folder"
        )
        if path:
            self.change_bw_dir(os.path.normpath(path))

    def change_bw_dir(self, path):
        """Set startup brightway directory.
        Switch to this directory if user wishes (this will update the "projects" combobox correctly).
        """

        # if no projects exist in this directory: ask user if he wants to set up a new brightway data directory here
        if not os.path.isfile(os.path.join(path, "projects.db")):
            print("No projects found in this directory.")
            create_new_directory = QtWidgets.QMessageBox.question(self,
                                                   'New brightway data directory?',
                                                   'This directory does not contain any projects. \n Would you like to setup a new brightway data directory here? \n This will close the current project and create a "default" project in the new directory.' ,
                                                   QtWidgets.QMessageBox.Ok,
                                                   QtWidgets.QMessageBox.Cancel)
            if create_new_directory == QtWidgets.QMessageBox.Cancel:
                return
            else:
                self.bwdir_edit.setText(path)
                signals.switch_bw2_dir_path.emit(path)
                bw.projects.set_current("default")
                self.update_project_combo()
        else:  # a project already exists in this directory
            self.bwdir_edit.setText(path)

            # ask user if to switch directory (which will update the project combobox correctly)
            reply = QtWidgets.QMessageBox.question(self,
                                                   'Continue?',
                                                   'Would you like to switch to this directory now? \nThis will close your currently opened project. \nClick "Yes" to be able to choose the startup project.',
                                                   QtWidgets.QMessageBox.Yes,
                                                   QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.Yes:
                signals.switch_bw2_dir_path.emit(path)
                self.update_project_combo()
            else:
                self.update_project_combo(set_to_default=True)

    def update_project_combo(self, set_to_default=False):
        self.startup_project_combobox.clear()
        if not set_to_default:  # normal behaviour
            default_project = ab_settings.startup_project
            if default_project:
                self.project_names = sorted([project.name for project in bw.projects])
                self.startup_project_combobox.addItems(self.project_names)
                index = self.project_names.index(default_project)
                self.startup_project_combobox.setCurrentIndex(index)
            else:
                print("Warning: No projects found in this directory.")
        else:  # set project to "default" when project list cannot be obtained as user is in different directory
            self.startup_project_combobox.addItems(["default"])
            self.startup_project_combobox.setCurrentIndex(0)

    def changed(self):
        self.wizard.button(QtWidgets.QWizard.BackButton).hide()
        self.complete = True
        self.completeChanged.emit()

    def isComplete(self):
        return self.complete


