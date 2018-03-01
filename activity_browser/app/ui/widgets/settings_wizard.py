# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5 import QtWidgets

from ...signals import signals
from ...settings import ab_settings


class SettingsWizard(QtWidgets.QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Actvitiy Browser Settings')
        self.settings_page = SettingsPage(self)
        self.addPage(self.settings_page)
        self.show()
        self.button(QtWidgets.QWizard.BackButton).hide()
        self.button(QtWidgets.QWizard.FinishButton).clicked.connect(self.save_settings)

    def save_settings(self):
        current_startup_project = self.settings_page.get_current_startup_project()
        if self.field('startup_project') != current_startup_project:
            new_startup_project = self.field('startup_project')
            ab_settings.settings['startup_project'] = new_startup_project
            bw.projects.set_current(new_startup_project)
            signals.project_selected.emit()
        current_bw_dir = self.settings_page.get_current_bw_dir()
        if self.field('custom_bw_dir') and self.field('custom_bw_dir') != current_bw_dir:
            custom_bw_dir = self.field('custom_bw_dir')
            ab_settings.settings['custom_bw_dir'] = custom_bw_dir
            signals.switch_bw2_dir_path.emit(custom_bw_dir)

        ab_settings.write_settings()


class SettingsPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = parent
        self.complete = False

        self.startup_project_combobox = QtWidgets.QComboBox()
        self.project_names = sorted([project.name for project in bw.projects])
        self.startup_project_combobox.addItems(self.project_names)
        index = self.project_names.index(self.get_current_startup_project())
        self.startup_project_combobox.setCurrentIndex(index)

        self.registerField('startup_project', self.startup_project_combobox, 'currentText')

        self.bwdir_edit = QtWidgets.QLineEdit()
        self.bwdir_edit.setPlaceholderText(self.get_current_bw_dir())
        self.bwdir_edit.setReadOnly(True)
        self.registerField('custom_bw_dir', self.bwdir_edit)
        self.bwdir_browse_button = QtWidgets.QPushButton('Browse')

        self.restore_defaults_button = QtWidgets.QPushButton('Restore defaults')

        # Startup options
        self.startup_groupbox = QtWidgets.QGroupBox('Startup Options')
        self.startup_layout = QtWidgets.QGridLayout()
        self.startup_layout.addWidget(QtWidgets.QLabel('Startup Project: '), 0, 0)
        self.startup_layout.addWidget(self.startup_project_combobox, 0, 1)
        self.startup_layout.addWidget(QtWidgets.QLabel('Brightway Dir: '), 1, 0)
        self.startup_layout.addWidget(self.bwdir_edit, 1, 1)
        self.startup_layout.addWidget(self.bwdir_browse_button, 1, 2)

        self.startup_groupbox.setLayout(self.startup_layout)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.startup_groupbox)
        self.layout.addStretch()
        self.layout.addWidget(self.restore_defaults_button)
        self.setLayout(self.layout)

        self.setFinalPage(True)
        self.setButtonText(3, 'Save')

        # signals
        self.startup_project_combobox.currentIndexChanged.connect(self.changed)
        self.bwdir_browse_button.clicked.connect(self.bwdir_browse)
        self.bwdir_edit.textChanged.connect(self.changed)
        self.restore_defaults_button.clicked.connect(self.restore_defaults)

    def restore_defaults(self):
        if 'default' in self.project_names:
            self.startup_project_combobox.setCurrentText('default')
        else:
            self.startup_project_combobox.setCurrentIndex(0)

        self.bwdir_edit.setText(bw.projects._get_base_directories()[0])

    def bwdir_browse(self):
        path = QtWidgets.QFileDialog().getExistingDirectory(
            None, "Select a brightway2 database folder"
        )
        self.bwdir_edit.setText(path)

    def changed(self):
        self.wizard.button(QtWidgets.QWizard.BackButton).hide()
        self.complete = True
        self.completeChanged.emit()

    def isComplete(self):
        return self.complete

    def get_current_startup_project(self):
        startup_proj = ab_settings.settings.get('startup_project')
        if startup_proj is not None and startup_proj in bw.projects:
            return ab_settings.settings['startup_project']
        elif 'default' in bw.projects:
            return 'default'
        else:
            return sorted([project.name for project in bw.projects])[0]

    def get_current_bw_dir(self):
        if ab_settings.settings.get('custom_bw_dir') is not None:
            return ab_settings.settings['custom_bw_dir']
        else:
            return bw.projects._get_base_directories()[0]
