# -*- coding: utf-8 -*-
import importlib
import traceback
import sys
import os
import tempfile
from pathlib import Path
from shutil import copytree, rmtree

import brightway2 as bw
import py7zr
from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Signal, Slot

from ...signals import signals
from ..style import style_group_box
from ...settings import ab_settings


class PluginImportWizard(QtWidgets.QWizard):
    LOCATE = 1
    IMPORT = 2
    CONFIRM = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plugin Import Wizard")
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.plugin = None

        # Construct and bind pages.
        self.locate_page = LocatePage(self)
        self.import_page = ImportPage(self)
        self.confirmation_page = ConfirmationPage(self)

        self.setPage(self.LOCATE, self.locate_page)
        self.setPage(self.IMPORT, self.import_page)
        self.setPage(self.CONFIRM, self.confirmation_page)
        self.setStartId(self.LOCATE)

        # with this line, finish behaves like cancel and the wizard can be reused
        # db import is done when finish button becomes active
        self.button(QtWidgets.QWizard.FinishButton).clicked.connect(self.cleanup)

        # thread management
        self.button(QtWidgets.QWizard.CancelButton).clicked.connect(self.cancel_thread)

        import_signals.import_failure.connect(self.show_info)

    def closeEvent(self, event):
        """ Close event now behaves similarly to cancel, because of self.reject.
        This allows the import wizard to be reused, ie starts from the beginning
        """
        self.cancel_thread()
        event.accept()

    def cancel_thread(self):
        print('\nPlugin import interrupted!')
        import_signals.cancel_sentinel = True
        self.cleanup()

    def cleanup(self):
        if self.import_page.main_worker_thread.isRunning():
            self.import_page.main_worker_thread.exit(1)
        self.import_page.complete = False
        self.reject()

    @Slot(tuple, name="showMessage")
    def show_info(self, info: tuple) -> None:
        title, message = info
        QtWidgets.QMessageBox.information(self, title, message)


class LocatePage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.wizard: QtWidgets.QWizard = parent
        self.path = QtWidgets.QLineEdit()
        self.registerField("plugin_path*", self.path)
        self.path.setReadOnly(True)
        self.path.textChanged.connect(self.changed)
        self.path_btn = QtWidgets.QPushButton("Browse")
        self.path_btn.clicked.connect(self.browse)
        self.complete = False

        option_box = QtWidgets.QGroupBox("Import plugin file:")
        grid_layout = QtWidgets.QGridLayout()
        layout = QtWidgets.QVBoxLayout()
        grid_layout.addWidget(QtWidgets.QLabel("Path to file"), 0, 0, 1, 1)
        grid_layout.addWidget(self.path, 0, 1, 1, 2)
        grid_layout.addWidget(self.path_btn, 0, 3, 1, 1)
        option_box.setLayout(grid_layout)
        option_box.setStyleSheet(style_group_box.border_title)
        layout.addWidget(option_box)
        self.setLayout(layout)

        # Register field to ensure user cannot advance without selecting file.
        self.registerField("import_path*", self.path)

    def initializePage(self):
        self.path.clear()

    def nextId(self):
        self.setField("plugin_path", self.path.text())
        return PluginImportWizard.IMPORT

    @Slot(name="browseFile")
    def browse(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self, caption="Select a valid .plugin file",
            filter="Plugin (*.plugin);; All Files (*.*)"
        )
        if path:
            self.path.setText(path)

    @Slot(name="pathChanged")
    def changed(self) -> None:
        path = Path(self.path.text())
        exists = path.is_file()
        valid = path.suffix.lower() in {".plugin"}
        if exists and not valid:
            import_signals.import_failure.emit(
                ("Invalid extension", "Expecting plugin file to have '.plugin' extension")
            )
        self.complete = all([exists, valid])
        self.completeChanged.emit()

    def isComplete(self):
        return self.complete


class ImportPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = parent
        self.complete = False
        self.relink_data = {}

        layout = QtWidgets.QVBoxLayout()

        self.unarchive_label = QtWidgets.QLabel('Decompressing the 7z archive:')
        self.unarchive_progressbar = QtWidgets.QProgressBar()
        self.loading_label = QtWidgets.QLabel('Loading plugin content:')
        self.loading_progressbar = QtWidgets.QProgressBar()
        self.finished_label = QtWidgets.QLabel('')

        layout.addWidget(self.unarchive_label)
        layout.addWidget(self.unarchive_progressbar)
        layout.addWidget(self.loading_label)
        layout.addWidget(self.loading_progressbar)
        layout.addStretch(1)
        layout.addWidget(self.finished_label)
        layout.addStretch(1)

        self.setLayout(layout)

        # progress signals
        import_signals.unarchive_finished.connect(self.update_unarchive)
        import_signals.unarchive_failed.connect(self.report_failed_unarchive)
        import_signals.loading.connect(self.update_loading)
        import_signals.loading_failed.connect(self.report_failed_loading)
        import_signals.import_finished.connect(self.update_finished)

        # Threads
        self.main_worker_thread = MainWorkerThread(self)

    def reset_progressbars(self) -> None:
        self.loading_progressbar.reset()
        self.unarchive_progressbar.reset()
        self.finished_label.setText('')

    def isComplete(self):
        return self.complete

    def init_progressbars(self) -> None:
        self.unarchive_label.setVisible(1)
        self.unarchive_progressbar.setVisible(1)
        self.unarchive_progressbar.setRange(0, 0)

    def initializePage(self):
        self.reset_progressbars()
        self.init_progressbars()
        self.main_worker_thread.update(plugin_path=self.field('plugin_path'))
        self.main_worker_thread.start()

    @Slot()
    def update_unarchive(self) -> None:
        self.unarchive_progressbar.setMaximum(1)
        self.unarchive_progressbar.setValue(1)

    @Slot()
    def update_loading(self) -> None:
        self.loading_progressbar.setRange(0, 0)

    @Slot()
    def update_finished(self, plugin) -> None:
        """Plugin import was successful, quit the thread."""
        if self.main_worker_thread.isRunning():
            self.main_worker_thread.quit()
        self.loading_progressbar.setMaximum(1)
        self.loading_progressbar.setValue(1)
        self.finished_label.setText('<b>Ready ton import !</b>')
        self.complete = True
        self.completeChanged.emit()
        self.wizard.plugin = plugin

    @Slot(str, name="handleUnzipFailed")
    def report_failed_unarchive(self, file: str) -> None:
        """Handle the issue where the 7z file is in some way corrupted.
        """
        self.main_worker_thread.exit(1)

        error = (
            "Corrupted (.7z) archive",
            "The archive '{}' is corrupted, please remove and re-download it.".format(file),
        )
        import_signals.import_failure.emit(error)
        return

    @Slot(str, name="handleLoadingFailed")
    def report_failed_loading(self) -> None:
        """Handle the issue where the plugin contain errors.
        """
        self.main_worker_thread.exit(1)

        error = (
            "Broken plugin code",
            "An error occured while loading plugin code",
        )
        import_signals.import_failure.emit(error)
        return  

    def nextId(self):
        return PluginImportWizard.CONFIRM


class ConfirmationPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFinalPage(True)
        self.wizard = parent
        self.setCommitPage(True)
        self.setButtonText(QtWidgets.QWizard.CommitButton, 'Import Plugin')
        self.current_project_label = QtWidgets.QLabel('empty')
        self.plugin_infos_label = QtWidgets.QLabel('empty')
        layout = QtWidgets.QVBoxLayout()
        box = QtWidgets.QGroupBox("Plugin Summary:")
        box_layout = QtWidgets.QVBoxLayout()
        box_layout.addWidget(self.current_project_label)
        box_layout.addWidget(self.plugin_infos_label)
        box.setLayout(box_layout)
        box.setStyleSheet(style_group_box.border_title)
        layout.addWidget(box)
        self.setLayout(layout)

    def initializePage(self):
        self.current_project_label.setText(
            'Current Project: <b>{}</b>'.format(bw.projects.current))
        infos = ""
        for key, value in self.wizard.plugin.infos.items():
            infos = infos + ("<br><i>{}:</i> {}".format(key,value))
        self.plugin_infos_label.setText(infos)

    def validatePage(self):
        signals.plugin_imported.emit(self.wizard.plugin, self.wizard.plugin.infos['name'])
        return True


class MainWorkerThread(QtCore.QThread):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.plugin_path = None
        self.plugin = None

    def update(self, plugin_path=None, relink=None) -> None:
        self.plugin_path = plugin_path

    def run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_extract(self.plugin_path, temp_dir)
            try:
                # Import code of plugin
                sys.path.append(temp_dir)
                metadata = importlib.import_module("metadata", temp_dir)
                importlib.reload(metadata)
                plugin_name = metadata.infos['name']
                # create plugins folder if necessary
                target_dir = "{}/{}".format(ab_settings.plugins_dir,plugin_name)
                if not os.path.isdir(target_dir):
                    os.makedirs(target_dir, exist_ok=True)
                # empty plugin directory
                rmtree(target_dir)
                # copy plugin content into folder
                copytree(temp_dir, target_dir+"/")
                # setup plugin
                plugin_lib = importlib.import_module(plugin_name, ab_settings.plugins_dir)
                self.plugin = plugin_lib.Plugin()
            except:
                import_signals.loading_failed.emit()
                import_signals.cancel_sentinel = True
                print(traceback.format_exc())

        if not import_signals.cancel_sentinel:
            import_signals.import_finished.emit(self.plugin)
    
    def run_extract(self, plugin_path, target_dir) -> None:
        """Extract the given .7z archive."""
        archive = py7zr.SevenZipFile(plugin_path, mode='r')
        archive.extractall(path=target_dir)
        archive.close()
        import_signals.unarchive_finished.emit()


class ImportSignals(QtCore.QObject):
    extraction_progress = Signal(int, int)
    unarchive_finished = Signal()
    unarchive_failed = Signal(str)
    loading = Signal()
    loading_failed = Signal()
    import_finished = Signal(object)
    import_failure = Signal(tuple)
    cancel_sentinel = False


import_signals = ImportSignals()