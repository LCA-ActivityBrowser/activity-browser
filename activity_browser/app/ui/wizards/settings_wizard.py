# -*- coding: utf-8 -*-
import os

import brightway2 as bw
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtWidgets import (QComboBox, QDialog, QFileDialog, QGridLayout,
                             QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QVBoxLayout, QWizard,
                             QWizardPage)

from activity_browser.app.settings import ab_settings, project_settings
from activity_browser.app.signals import signals


class SettingsWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_project = bw.projects.current
        self.last_bwdir = bw.projects._base_data_dir
        self.last_biosphere_types = project_settings.biosphere_types
        self.next_page = None

        self.choice_page = self.addPage(ChoiceSettingsPage(self))
        self.ab_page = self.addPage(ABSettingsPage(self))
        self.project_page = self.addPage(ProjectSettingsPage(self))
        self.setStartId(self.choice_page)

        self.setOptions(QWizard.NoBackButtonOnStartPage)
        self.setButtonText(QWizard.FinishButton, 'Save')
        self.setButtonText(QWizard.CancelButton, 'Close')
        self.setButtonLayout([
            QWizard.Stretch, QWizard.BackButton, QWizard.CancelButton
        ])
        self._connect_signals()
        self.show()

    def _connect_signals(self):
        self.button(QWizard.FinishButton).clicked.connect(self.save_settings)
        self.button(QWizard.CancelButton).clicked.connect(self.close)

    @pyqtSlot()
    def save_settings(self) -> None:
        """ Handles saving the settings for all of the wizard pages.
        """
        # Custom brightway directory
        if (self.field('custom_bw_dir') and
                self.field('custom_bw_dir') != ab_settings.custom_bw_dir):
            custom_bw_dir = self.field('custom_bw_dir')
            ab_settings.custom_bw_dir = custom_bw_dir
            print("Saved startup brightway directory as: ", custom_bw_dir)

        # Startup project
        if self.field("startup_project") != ab_settings.startup_project:
            new_startup_project = self.field("startup_project")
            ab_settings.startup_project = new_startup_project
            print("Saved startup project as: ", new_startup_project)

        ab_settings.write_settings()

        # Biosphere fields
        if self.field("biosphere_types") != project_settings.biosphere_types:
            types = self.field("biosphere_types")
            new_types = [
                field.strip() for field in types.split(",")
            ] if types != "" else []
            project_settings.biosphere_types = new_types
            print(
                "Saved these types as biosphere: '{}' for project '{}'".format(
                    types, bw.projects.current
                )
            )

        project_settings.write_settings()

    @pyqtSlot()
    def close(self) -> None:
        print("Closing settings.")

    @pyqtSlot(int)
    def goto_page(self, page_nr: int) -> None:
        if page_nr in [self.ab_page, self.project_page]:
            self.setButtonLayout([
                QWizard.Stretch, QWizard.BackButton, QWizard.FinishButton
            ])
        self.next_page = page_nr
        self.nextId()
        self.next()

    def nextId(self) -> int:
        """ Override the default wizardpage ordering.
        """
        if self.next_page in [self.ab_page, self.project_page]:
            return self.next_page
        return -1

    @pyqtSlot()
    def accept(self) -> None:
        """ Override what happens when the user clicks save.

        Basically, stop the window from closing immediately.
        """
        self.setButtonLayout([
            QWizard.Stretch, QWizard.BackButton, QWizard.CancelButton
        ])
        self.setResult(QDialog.Accepted)
        self.accepted.emit()

    @pyqtSlot()
    def back(self) -> None:
        """ If a user presses the back button, remove the 'save' button
        from the layout.
        """
        self.setButtonLayout([QWizard.Stretch, QWizard.CancelButton])
        super().back()


class ChoiceSettingsPage(QWizardPage):
    """ Basically the first 'settings' page shown to the user, each button
    redirects the wizard to its own wizard page.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.wizard = parent
        self._construct_layout()
        self._connect_signals()
        self.setFinalPage(False)
        self.setTitle("Settings")

    def _construct_layout(self):
        """"""
        self.ab_settings_btn = QPushButton("Activity Browser Settings")
        self.project_settings_btn = QPushButton("Project-specific Settings")

        btn_layout = QVBoxLayout()
        btn_layout.addWidget(self.ab_settings_btn)
        btn_layout.addWidget(self.project_settings_btn)
        groupbox = QGroupBox()
        groupbox.setLayout(btn_layout)
        layout = QVBoxLayout()
        layout.addWidget(groupbox)
        self.setLayout(layout)

    def _connect_signals(self):
        self.ab_settings_btn.clicked.connect(
            lambda: self.wizard.goto_page(self.wizard.ab_page)
        )
        self.project_settings_btn.clicked.connect(
            lambda: self.wizard.goto_page(self.wizard.project_page)
        )


class ABSettingsPage(QWizardPage):
    def __init__(self, parent):
        super().__init__(parent)
        self.wizard = parent
        self.complete = False

        self._construct_layout()
        self._connect_signals()

        self.registerField(
            "startup_project", self.startup_project_combobox, "currentText"
        )
        self.registerField("custom_bw_dir", self.bwdir_edit)
        self.setFinalPage(True)
        self.setTitle("Activity Browser Settings")

    def _construct_layout(self):
        # Create widgets
        self.startup_project_combobox = QComboBox()
        self.update_project_combo()
        self.bwdir_edit = QLineEdit()
        self.bwdir_edit.setPlaceholderText(ab_settings.custom_bw_dir)
        self.bwdir_edit.setReadOnly(True)
        self.bwdir_browse_btn = QPushButton('Browse')
        self.restore_defaults_btn = QPushButton('Restore defaults')

        # Construct layout
        startup_groupbox = QGroupBox('Startup Options')
        startup_layout = QGridLayout()
        startup_layout.addWidget(QLabel('Brightway Dir: '), 0, 0)
        startup_layout.addWidget(self.bwdir_edit, 0, 1)
        startup_layout.addWidget(self.bwdir_browse_btn, 0, 2)
        startup_layout.addWidget(QLabel('Startup Project: '), 1, 0)
        startup_layout.addWidget(self.startup_project_combobox, 1, 1)
        startup_groupbox.setLayout(startup_layout)
        layout = QVBoxLayout()
        layout.addWidget(startup_groupbox)
        layout.addStretch()
        layout.addWidget(self.restore_defaults_btn)
        self.setLayout(layout)

    def _connect_signals(self):
        self.startup_project_combobox.currentIndexChanged.connect(self.changed)
        self.bwdir_browse_btn.clicked.connect(self.bwdir_browse)
        self.bwdir_edit.textChanged.connect(self.changed)
        self.restore_defaults_btn.clicked.connect(self.restore_defaults)

    def restore_defaults(self) -> None:
        self.change_bw_dir(ab_settings.get_default_directory())
        self.startup_project_combobox.setCurrentText(ab_settings.get_default_project_name())

    def initializePage(self) -> None:
        """ Ensure values shown are up to date with settings
        """
        self.bwdir_edit.setPlaceholderText(ab_settings.custom_bw_dir)
        self.update_project_combo()

    def bwdir_browse(self) -> None:
        path = QFileDialog().getExistingDirectory(
            None, "Select a brightway2 database folder"
        )
        if path:
            self.change_bw_dir(os.path.normpath(path))

    def change_bw_dir(self, path: str) -> None:
        """ Set startup brightway directory.

        Switch to this directory if user wishes (this will update the
        "projects" combobox correctly).
        """
        # if no projects exist in this directory: ask user if they want
        # to set up a new brightway data directory here
        if not os.path.isfile(os.path.join(path, "projects.db")):
            print("No projects found in this directory.")
            create_new_directory = QMessageBox.question(
                self,
                "New brightway data directory?",
                ("This directory does not contain any projects."
                 "\nWould you like to setup a new brightway data directory"
                 " here?\nThis will close the current project and create a "
                 "\"default\" project in the new directory."),
                QMessageBox.Ok,
                QMessageBox.Cancel,
            )
            if create_new_directory == QMessageBox.Cancel:
                return
            else:
                self.bwdir_edit.setText(path)
                signals.switch_bw2_dir_path.emit(path)
                bw.projects.set_current("default")
                self.update_project_combo()
        else:  # a project already exists in this directory
            self.bwdir_edit.setText(path)

            # ask user if to switch directory (which will update the project combobox correctly)
            reply = QMessageBox.question(
                self,
                "Continue?",
                ("Would you like to switch to this directory now?"
                 "\nThis will close your currently opened project."
                 "\nClick \"Yes\" to be able to choose the startup project."),
                QMessageBox.Yes,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                signals.switch_bw2_dir_path.emit(path)
                self.update_project_combo()
            else:
                self.update_project_combo(set_to_default=True)

    def update_project_combo(self, set_to_default=False) -> None:
        """ Build and update the combobox with brightway projects
        """
        self.startup_project_combobox.clear()
        if not set_to_default:  # normal behaviour
            default_project = ab_settings.startup_project
            if default_project:
                project_names = sorted([project.name for project in bw.projects])
                self.startup_project_combobox.addItems(project_names)
                index = project_names.index(default_project)
                self.startup_project_combobox.setCurrentIndex(index)
            else:
                print("Warning: No projects found in this directory.")
        else:  # set project to "default" when project list cannot be obtained as user is in different directory
            self.startup_project_combobox.addItems(["default"])
            self.startup_project_combobox.setCurrentIndex(0)

    def changed(self) -> None:
        self.complete = True
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return self.complete


class ProjectSettingsPage(QWizardPage):
    """ Contains settings specific to the currently selected project
    """
    valid_change = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self.wizard = parent
        self.complete = False
        self.title = "Project '{}' Settings"

        self._construct_layout()
        self._connect_signals()

        self.registerField("biosphere_types", self.biospheres_field)
        self.setFinalPage(True)

    def _construct_layout(self):
        # Build input fields
        self.biospheres_field = QLineEdit()
        self.biospheres_field.setText(
            ", ".join(project_settings.biosphere_types)
        )
        self.biospheres_valid_btn = QPushButton("Validate fields")
        self.biospheres_valid_btn.setEnabled(False)
        self.restore_defaults_btn = QPushButton("Restore defaults")

        # Construct the layout
        groupbox = QGroupBox()
        biospheres_layout = QVBoxLayout()
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.biospheres_field)
        input_layout.addWidget(self.biospheres_valid_btn)
        biospheres_layout.addWidget(QLabel("Accepted biosphere types:"))
        biospheres_layout.addLayout(input_layout)
        groupbox.setLayout(biospheres_layout)
        layout = QVBoxLayout()
        layout.addWidget(groupbox)
        layout.addStretch()
        layout.addWidget(self.restore_defaults_btn)
        self.setLayout(layout)

    def _connect_signals(self):
        self.biospheres_field.textChanged.connect(
            lambda: self.biospheres_valid_btn.setEnabled(True)
        )
        self.biospheres_valid_btn.clicked.connect(self.validate_biospheres)
        self.biospheres_valid_btn.clicked.connect(
            lambda: self.biospheres_valid_btn.setEnabled(False)
        )
        self.valid_change.connect(self.changed)
        self.restore_defaults_btn.clicked.connect(self.restore_defaults)

    def restore_defaults(self) -> None:
        """ Discard user settings and fill in the defaults
        """
        self.biospheres_field.setText(
            ", ".join(project_settings.get_default_biosphere_types())
        )

    def initializePage(self) -> None:
        """ Ensure values shown are up to date
        """
        self.setTitle(self.title.format(bw.projects.current))
        self.biospheres_field.setText(
            ", ".join(project_settings.biosphere_types)
        )

    @pyqtSlot()
    def validate_biospheres(self) -> None:
        """ Take the text in the biospheres field and check against all
        possible types in the databases
        """
        QTimer.singleShot(
            5000, lambda: self.biospheres_valid_btn.setEnabled(True)
        )
        fields = self.biospheres_field.text().split(",")
        testable_fields = [field.strip() for field in fields]

        unknown_types = project_settings.valid_biospheres(testable_fields)

        if not unknown_types:
            self.valid_change.emit()
        else:
            reply = QMessageBox()
            reply.setIcon(QMessageBox.Warning)
            reply.setText("Invalid input")
            reply.setInformativeText(
                "One or more of the given biosphere types are not accepted"
            )
            reply.setDetailedText(
                "Invalid types: {}".format(", ".join(unknown_types))
            )
            reply.setStandardButtons(QMessageBox.Ok)
            reply.setDefaultButton(QMessageBox.Ok)
            reply.exec()

    @pyqtSlot()
    def changed(self) -> None:
        """ Triggered if the user changes any of the settings on the page
        """
        self.complete = True
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return self.complete
