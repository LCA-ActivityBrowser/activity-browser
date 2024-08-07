# -*- coding: utf-8 -*-
import io
import os.path
import shutil
import typing
from functools import lru_cache
import tempfile
import zipfile
from pathlib import Path

import bw2data.errors
import ecoinvent_interface as ei
import requests
from bw2io import BW2Package, SingleOutputEcospold2Importer
from bw2io.extractors import Ecospold2DataExtractor
from PySide2 import QtCore, QtWidgets
from PySide2.QtCore import Signal, Slot
from py7zr import py7zr

from activity_browser import log
from activity_browser.bwutils import errors
from activity_browser.mod import bw2data as bd

from ...bwutils.importers import ABExcelImporter, ABPackage
from ...utils import sort_semantic_versions
from ..style import style_group_box
from ..threading import ABThread
from ..widgets import DatabaseLinkingDialog


class DatabaseImportWizard(QtWidgets.QWizard):
    IMPORT_TYPE = 1
    REMOTE_TYPE = 2
    LOCAL_TYPE = 3
    EI_LOGIN = 4
    EI_VERSION = 5
    DB_BIOSPHERE_CREATION = 6
    ARCHIVE = 7
    DIR = 8
    LOCAL = 9
    EXCEL = 10
    DB_NAME = 11
    CONFIRM = 12
    IMPORT = 13

    def __init__(self, parent=None):
        super().__init__(parent)
        self.downloader = ABEcoinventDownloader()
        self.setWindowTitle("Database Import Wizard")
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(QtCore.Qt.Sheet)
        self.setOption(self.NoCancelButton, False)

        # Construct and bind pages.
        self.import_type_page = ImportTypePage(self)
        self.remote_page = RemoteImportPage(self)
        self.local_page = LocalImportPage(self)
        self.ecoinvent_login_page = EcoinventLoginPage(self)
        self.ecoinvent_version_page = EcoinventVersionPage(self)
        self.archive_page = Choose7zArchivePage(self)
        self.choose_dir_page = ChooseDirPage(self)
        self.local_import_page = LocalDatabaseImportPage(self)
        self.excel_import_page = ExcelDatabaseImport(self)
        self.db_name_page = DBNamePage(self)
        self.confirmation_page = ConfirmationPage(self)
        self.import_page = ImportPage(self)
        self.setPage(self.IMPORT_TYPE, self.import_type_page)
        self.setPage(self.REMOTE_TYPE, self.remote_page)
        self.setPage(self.LOCAL_TYPE, self.local_page)
        self.setPage(self.EI_LOGIN, self.ecoinvent_login_page)
        self.setPage(self.EI_VERSION, self.ecoinvent_version_page)
        self.setPage(self.ARCHIVE, self.archive_page)
        self.setPage(self.DIR, self.choose_dir_page)
        self.setPage(self.LOCAL, self.local_import_page)
        self.setPage(self.EXCEL, self.excel_import_page)
        self.setPage(self.DB_NAME, self.db_name_page)
        self.setPage(self.CONFIRM, self.confirmation_page)
        self.setPage(self.IMPORT, self.import_page)
        self.setStartId(self.IMPORT_TYPE)

        # with this line, finish behaves like cancel and the wizard can be reused
        # db import is done when finish button becomes active
        self.button(QtWidgets.QWizard.FinishButton).clicked.connect(self.cleanup)

        import_signals.connection_problem.connect(self.show_info)
        import_signals.import_failure.connect(self.show_info)
        import_signals.import_failure_detailed.connect(self.show_detailed)

    @property
    def version(self):
        return self.ecoinvent_version_page.version_combobox.currentText()

    @property
    def system_model(self):
        return self.ecoinvent_version_page.system_model_combobox.currentText()

    @property
    def release_type(self):
        return ei.ReleaseType.ecospold

    def update_downloader(self):
        self.downloader.version = self.version
        self.downloader.system_model = self.system_model
        self.downloader.release_type = self.release_type

    def done(self, result: int):
        """
        Reimplementation of the QWizard.done method which is called when the wizard is done
        or when the user cancels.
        """
        # indicate to the user that the click was succesful
        self.button(QtWidgets.QWizard.CancelButton).setDisabled(True)

        # cancel any running tasks
        self.cancel_extraction()
        self.cancel_thread()

        # else just call done on super()
        super().done(result)

    def closeEvent(self, event):
        """Close event now behaves similarly to cancel, because of self.reject.

        This allows the import wizard to be reused, ie starts from the beginning
        """
        self.cancel_extraction()
        self.cancel_thread()
        event.accept()

    def cancel_thread(self):
        """Cancels the worker thread initiated by the import page"""
        thread = self.import_page.main_worker_thread
        dispatcher = self.thread().eventDispatcher()

        # show the user we're working on something within the wizard
        self.setCursor(QtCore.Qt.WaitCursor)

        if thread.isRunning():
            # flag an abort through the sentinel
            import_signals.cancel_sentinel = True
            # make sure the import page doesn't receive any last signals by the thread
            import_signals.disconnect(self.import_page)
            # signal the thread to exit when it can do so safely
            thread.exit(1)

        # block while the thread is still running
        while thread.isRunning():
            # make sure we stay responsive
            dispatcher.processEvents(QtCore.QEventLoop.AllEvents)

        # return to normal
        self.setCursor(QtCore.Qt.ArrowCursor)

    def cancel_extraction(self):
        process = getattr(self.downloader, "extraction_process", None)
        if process is not None:
            process.kill()
            process.communicate()

    def cleanup(self):
        if self.import_page.main_worker_thread.isRunning():
            self.import_page.main_worker_thread.exit(1)
        self.import_page.complete = False
        self.reject()

    def has_existing_remote_credentials(self) -> bool:
        return (
            self.downloader.username is not None
            and self.downloader.password is not None
        )

    @Slot(tuple, name="showMessage")
    def show_info(self, info: tuple) -> None:
        title, message = info
        QtWidgets.QMessageBox.information(self, title, message)

    @Slot(object, tuple, name="showDetailedMessage")
    def show_detailed(self, icon: QtWidgets.QMessageBox.Icon, data: tuple) -> None:
        title, message, *other = data
        msg = QtWidgets.QMessageBox(
            icon, title, message, QtWidgets.QMessageBox.Ok, self
        )
        if other:
            other = other[0] if len(other) == 1 else other
            msg.setDetailedText("\n\n".join(str(e) for e in other))
        msg.exec_()


class ImportTypePage(QtWidgets.QWizardPage):
    OPTIONS = (
        ("Import remote data (download)", DatabaseImportWizard.REMOTE_TYPE),
        ("Import local data", DatabaseImportWizard.LOCAL_TYPE),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = parent
        self.radio_buttons = [QtWidgets.QRadioButton(o[0]) for o in self.OPTIONS]
        self.radio_buttons[0].setChecked(True)

        layout = QtWidgets.QVBoxLayout()
        box = QtWidgets.QGroupBox("Type of data import:")
        box_layout = QtWidgets.QVBoxLayout()
        for i, button in enumerate(self.radio_buttons):
            box_layout.addWidget(button)
        box.setLayout(box_layout)
        box.setStyleSheet(style_group_box.border_title)
        layout.addWidget(box)
        self.setLayout(layout)

    def nextId(self):
        option_id = [b.isChecked() for b in self.radio_buttons].index(True)
        return self.OPTIONS[option_id][1]


class RemoteImportPage(QtWidgets.QWizardPage):
    """Contains all the options for remote importing of data."""

    OPTIONS = (
        ("ecoinvent (requires login)", "homepage", DatabaseImportWizard.EI_LOGIN),
        ("Forwast", "forwast", DatabaseImportWizard.DB_NAME),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = parent
        self.radio_buttons = [QtWidgets.QRadioButton(o[0]) for o in self.OPTIONS]
        self.radio_buttons[0].setChecked(True)
        self.has_valid_remote_creds = False

        layout = QtWidgets.QVBoxLayout()
        box = QtWidgets.QGroupBox("Data source:")
        box_layout = QtWidgets.QVBoxLayout()
        for i, button in enumerate(self.radio_buttons):
            box_layout.addWidget(button)
        box.setLayout(box_layout)
        box.setStyleSheet(style_group_box.border_title)
        layout.addWidget(box)
        self.setLayout(layout)

    def nextId(self):
        option_id = [b.isChecked() for b in self.radio_buttons].index(True)
        self.wizard.import_type = self.OPTIONS[option_id][1]
        next_id = self.OPTIONS[option_id][2]
        return next_id


class LocalImportPage(QtWidgets.QWizardPage):
    """Contains all the options for the local importing of data."""

    OPTIONS = (
        (
            "Local 7z-archive of ecospold2 files",
            "archive",
            DatabaseImportWizard.ARCHIVE,
        ),
        ("Local directory with ecospold2 files", "directory", DatabaseImportWizard.DIR),
        ("Local Excel file", "local", DatabaseImportWizard.EXCEL),
        ("Local brightway database file", "local", DatabaseImportWizard.LOCAL),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = parent
        self.radio_buttons = [QtWidgets.QRadioButton(o[0]) for o in self.OPTIONS]
        self.radio_buttons[0].setChecked(True)

        layout = QtWidgets.QVBoxLayout()
        box = QtWidgets.QGroupBox("Data source:")
        box_layout = QtWidgets.QVBoxLayout()
        for i, button in enumerate(self.radio_buttons):
            box_layout.addWidget(button)
        box.setLayout(box_layout)
        box.setStyleSheet(style_group_box.border_title)
        layout.addWidget(box)
        self.setLayout(layout)

    def nextId(self):
        option_id = [b.isChecked() for b in self.radio_buttons].index(True)
        self.wizard.import_type = self.OPTIONS[option_id][1]
        return self.OPTIONS[option_id][2]


class ChooseDirPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.path_edit = QtWidgets.QLineEdit()
        self.registerField("dirpath*", self.path_edit)
        self.browse_button = QtWidgets.QPushButton("Browse")
        self.browse_button.clicked.connect(self.get_directory)

        layout = QtWidgets.QVBoxLayout()
        box = QtWidgets.QGroupBox("Choose location of existing ecospold2 directory:")
        box_layout = QtWidgets.QVBoxLayout()
        box_layout.addWidget(self.path_edit)
        browse_lay = QtWidgets.QHBoxLayout()
        browse_lay.addWidget(self.browse_button)
        browse_lay.addStretch(1)
        box_layout.addLayout(browse_lay)
        box.setLayout(box_layout)
        box.setStyleSheet(style_group_box.border_title)
        layout.addWidget(box)
        self.setLayout(layout)

    @Slot(name="getDirectory")
    def get_directory(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select directory with ecospold2 files"
        )
        self.path_edit.setText(path)

    def validatePage(self):
        dir_path = Path(self.field("dirpath") or "")
        if not dir_path.is_dir():
            warning = "Not a directory:<br>{}".format(dir_path)
            QtWidgets.QMessageBox.warning(self, "Not a directory!", warning)
            return False
        else:
            count = sum(1 for _ in dir_path.glob("*.spold"))
            if not count:
                warning = "No ecospold files found in this directory:<br>{}".format(
                    dir_path
                )
                QtWidgets.QMessageBox.warning(self, "No ecospold files!", warning)
                return False
            else:
                return True

    def nextId(self):
        return DatabaseImportWizard.DB_NAME


class Choose7zArchivePage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = parent
        self.path_edit = QtWidgets.QLineEdit()
        self.registerField("archive_path*", self.path_edit)
        self.browse_button = QtWidgets.QPushButton("Browse")
        self.browse_button.clicked.connect(self.get_archive)
        self.stored_dbs = {}
        self.stored_combobox = QtWidgets.QComboBox()
        self.stored_combobox.activated.connect(self.update_stored)

        layout = QtWidgets.QVBoxLayout()
        box = QtWidgets.QGroupBox("Choose location of 7z archive:")
        box_layout = QtWidgets.QVBoxLayout()
        box_layout.addWidget(self.path_edit)
        browse_lay = QtWidgets.QHBoxLayout()
        browse_lay.addWidget(self.browse_button)
        browse_lay.addStretch(1)
        box_layout.addLayout(browse_lay)
        box_layout.addWidget(QtWidgets.QLabel("Previous downloads:"))
        box_layout.addWidget(self.stored_combobox)
        box.setLayout(box_layout)
        box.setStyleSheet(style_group_box.border_title)
        layout.addWidget(box)
        self.setLayout(layout)

    def initializePage(self):
        self.stored_dbs = ei.CachedStorage()
        self.stored_combobox.clear()
        self.stored_combobox.addItems(
            sorted(
                [
                    key
                    for key, value in self.stored_dbs.catalogue.items()
                    if value["extracted"] == False
                    and value["kind"] == "release"
                    and key.partition(value["system_model"])[2] == "_ecoSpold02.7z"
                ]
            )
        )

    @Slot(int, name="updateSelectedIndex")
    def update_stored(self, index: int) -> None:
        self.path_edit.setText(
            self.stored_dbs.catalogue[self.stored_combobox.currentText()]["path"]
        )

    @Slot(name="getArchiveFile")
    def get_archive(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select 7z archive")
        if path:
            self.path_edit.setText(path)

    def validatePage(self):
        path = Path(self.field("archive_path") or "")
        if path.is_file():
            if path.suffix == ".7z":
                return True
            else:
                warning = (
                    "Unexpected filetype: <b>{}</b><br>Import might not work."
                    + "Continue anyway?"
                ).format(path.suffix)
                answer = QtWidgets.QMessageBox.question(
                    self, "Not a 7zip archive!", warning
                )
                return answer == QtWidgets.QMessageBox.Yes
        else:
            warning = "File not found:<br>{}".format(path)
            QtWidgets.QMessageBox.warning(self, "File not found!", warning)
            return False

    def nextId(self):
        return DatabaseImportWizard.DB_NAME


class DBNamePage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = parent
        self.name_edit = QtWidgets.QLineEdit()
        self.registerField("db_name*", self.name_edit)

        layout = QtWidgets.QVBoxLayout()
        box = QtWidgets.QGroupBox("Name of the new database:")
        box_layout = QtWidgets.QVBoxLayout()
        box_layout.addWidget(self.name_edit)
        box.setLayout(box_layout)
        box.setStyleSheet(style_group_box.border_title)
        layout.addWidget(box)
        self.setLayout(layout)

    def initializePage(self):
        if self.wizard.import_type == "homepage":
            version = self.wizard.version
            sys_mod = self.wizard.system_model
            self.name_edit.setText(sys_mod + version.replace(".", ""))
        elif self.wizard.import_type == "forwast":
            self.name_edit.setText("Forwast")
        elif self.wizard.import_type == "local":
            filename = Path(self.field("archive_path")).name
            if "." in filename:
                self.name_edit.setText(filename.split(".")[0])
            else:
                self.name_edit.setText(filename)

    def validatePage(self):
        db_name = self.name_edit.text()
        if db_name in bd.databases:
            warning = "Database <b>{}</b> already exists in project <b>{}</b>!".format(
                db_name, bd.projects.current
            )
            QtWidgets.QMessageBox.warning(self, "Database exists!", warning)
            return False
        else:
            return True

    def nextId(self):
        return DatabaseImportWizard.CONFIRM


class ConfirmationPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = parent
        self.setCommitPage(True)
        self.setButtonText(QtWidgets.QWizard.CommitButton, "Import Database")
        self.current_project_label = QtWidgets.QLabel("empty")
        self.db_name_label = QtWidgets.QLabel("empty")
        self.path_label = QtWidgets.QLabel("empty")

        layout = QtWidgets.QVBoxLayout()
        box = QtWidgets.QGroupBox("Import Summary:")
        box_layout = QtWidgets.QVBoxLayout()
        box_layout.addWidget(self.current_project_label)
        box_layout.addWidget(self.db_name_label)
        box_layout.addWidget(self.path_label)
        box.setLayout(box_layout)
        box.setStyleSheet(style_group_box.border_title)
        layout.addWidget(box)
        self.setLayout(layout)

    def initializePage(self):
        self.current_project_label.setText(
            "Current Project: <b>{}</b>".format(bd.projects.current)
        )
        self.db_name_label.setText(
            "Name of the new database: <b>{}</b>".format(self.field("db_name"))
        )
        if self.wizard.import_type == "directory":
            self.path_label.setText(
                "Path to directory with ecospold files:<br><b>{}</b>".format(
                    self.field("dirpath")
                )
            )
        elif self.wizard.import_type == "archive":
            self.path_label.setText(
                "Path to 7z archive:<br><b>{}</b>".format(self.field("archive_path"))
            )
        elif self.wizard.import_type == "forwast":
            self.path_label.setOpenExternalLinks(True)
            self.path_label.setText(
                'Download forwast from <a href="https://lca-net.com/projects/show/forwast/">'
                + "https://lca-net.com/projects/show/forwast/</a>"
            )
        elif self.wizard.import_type == "local":
            self.path_label.setText(
                "Path to local file:<br><b>{}</b>".format(self.field("archive_path"))
            )
        else:
            self.path_label.setText(
                "Ecoinvent version: <b>{}</b><br>"
                "Ecoinvent system model: <b>{}</b><br>"
                "Dependent Database: <b>{}</b>".format(
                    self.wizard.version,
                    self.wizard.system_model,
                    bd.config.biosphere,
                )
            )

    def validatePage(self):
        """
        while a worker thread is running, it's not possible to proceed to the import page.
        this is required because there is only one sentinel value for canceled imports
        """
        running = self.wizard.import_page.main_worker_thread.isRunning()
        return not running

    def nextId(self):
        return DatabaseImportWizard.IMPORT


class ImportPage(QtWidgets.QWizardPage):
    NO_DOWNLOAD = {"directory", "archive", "local"}
    NO_UNPACK = {"directory", "local"}
    NO_EXTRACT = {"forwast", "local"}
    NO_STRATEGY = {"forwast", "local"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFinalPage(True)
        self.wizard = parent
        self.complete = False
        self.relink_data = {}
        self.extraction_label = QtWidgets.QLabel(
            "Extracting XML data from ecospold files:"
        )
        self.extraction_progressbar = QtWidgets.QProgressBar()
        self.strategy_label = QtWidgets.QLabel("Applying brightway2 strategies:")
        self.strategy_progressbar = QtWidgets.QProgressBar()
        db_label = QtWidgets.QLabel("Writing datasets to SQLite database:")
        self.db_progressbar = QtWidgets.QProgressBar()
        finalizing_label = QtWidgets.QLabel("Finalizing:")
        self.finalizing_progressbar = QtWidgets.QProgressBar()
        self.finished_label = QtWidgets.QLabel("")

        layout = QtWidgets.QVBoxLayout()
        self.download_label = QtWidgets.QLabel(
            "Downloading data from ecoinvent homepage:"
        )
        self.download_label.setVisible(False)
        self.download_progressbar = QtWidgets.QProgressBar()
        self.unarchive_label = QtWidgets.QLabel("Decompressing the 7z archive:")
        self.unarchive_progressbar = QtWidgets.QProgressBar()
        layout.addWidget(self.download_label)
        layout.addWidget(self.download_progressbar)
        layout.addWidget(self.unarchive_label)
        layout.addWidget(self.unarchive_progressbar)

        layout.addWidget(self.extraction_label)
        layout.addWidget(self.extraction_progressbar)
        layout.addWidget(self.strategy_label)
        layout.addWidget(self.strategy_progressbar)
        layout.addWidget(db_label)
        layout.addWidget(self.db_progressbar)
        layout.addWidget(finalizing_label)
        layout.addWidget(self.finalizing_progressbar)
        layout.addStretch(1)
        layout.addWidget(self.finished_label)
        layout.addStretch(1)

        self.setLayout(layout)

        # progress signals
        import_signals.extraction_progress.connect(self.update_extraction_progress)
        import_signals.strategy_progress.connect(self.update_strategy_progress)
        import_signals.db_progress.connect(self.update_db_progress)
        import_signals.finalizing.connect(self.update_finalizing)
        import_signals.finished.connect(self.update_finished)
        import_signals.download_complete.connect(self.update_download)
        import_signals.unarchive_finished.connect(self.update_unarchive)
        import_signals.missing_dbs.connect(self.fix_db_import)
        import_signals.links_required.connect(self.fix_excel_import)
        import_signals.unarchive_failed.connect(self.report_failed_unarchive)

        # Threads
        self.main_worker_thread = MainWorkerThread(self.wizard.downloader, self)

    def reset_progressbars(self) -> None:
        for pb in [
            self.extraction_progressbar,
            self.strategy_progressbar,
            self.db_progressbar,
            self.finalizing_progressbar,
            self.download_progressbar,
            self.unarchive_progressbar,
        ]:
            pb.reset()
        self.finished_label.setText("")

    def isComplete(self):
        return self.complete

    def init_progressbars(self) -> None:
        show_download = self.wizard.import_type not in self.NO_DOWNLOAD
        self.download_label.setVisible(show_download)
        self.download_progressbar.setVisible(show_download)
        show_unarchive = self.wizard.import_type not in self.NO_UNPACK
        self.unarchive_label.setVisible(show_unarchive)
        self.unarchive_progressbar.setVisible(show_unarchive)
        show_extract = self.wizard.import_type not in self.NO_EXTRACT
        self.extraction_label.setVisible(show_extract)
        self.extraction_progressbar.setVisible(show_extract)
        show_strategies = self.wizard.import_type not in self.NO_STRATEGY
        self.strategy_label.setVisible(show_strategies)
        self.strategy_progressbar.setVisible(show_strategies)
        if show_download:
            self.download_progressbar.setRange(0, 0)
        elif self.wizard.import_type == "archive":
            self.unarchive_progressbar.setRange(0, 0)

    def initializePage(self):
        self.reset_progressbars()
        self.init_progressbars()
        self.wizard.update_downloader()
        if self.wizard.import_type == "directory":
            self.main_worker_thread.update(
                db_name=self.field("db_name"), datasets_path=self.field("dirpath")
            )
        elif self.wizard.import_type == "archive":
            self.main_worker_thread.update(
                db_name=self.field("db_name"), archive_path=self.field("archive_path")
            )
        elif self.wizard.import_type == "forwast":
            self.main_worker_thread.update(
                db_name=self.field("db_name"), use_forwast=True
            )
        elif self.wizard.import_type == "local":
            kwargs = {
                "db_name": self.field("db_name"),
                "archive_path": self.field("archive_path"),
                "use_local": True,
                "relink": self.relink_data,
            }
            self.main_worker_thread.update(**kwargs)
        else:
            self.main_worker_thread.update(db_name=self.field("db_name"))
        self.main_worker_thread.start()

    @Slot(int, int)
    def update_extraction_progress(self, i, tot) -> None:
        self.extraction_progressbar.setMaximum(tot)
        self.extraction_progressbar.setValue(i)

    @Slot(int, int)
    def update_strategy_progress(self, i, tot) -> None:
        self.strategy_progressbar.setMaximum(tot)
        self.strategy_progressbar.setValue(i)

    @Slot(int, int)
    def update_db_progress(self, i, tot) -> None:
        self.db_progressbar.setMaximum(tot)
        self.db_progressbar.setValue(i)
        if i == tot and tot != 0:
            import_signals.finalizing.emit()

    @Slot()
    def update_finalizing(self) -> None:
        self.finalizing_progressbar.setRange(0, 0)

    @Slot()
    def update_finished(self) -> None:
        """Databse import was successful, quit the thread and the wizard."""
        if self.main_worker_thread.isRunning():
            self.main_worker_thread.quit()
        self.finalizing_progressbar.setMaximum(1)
        self.finalizing_progressbar.setValue(1)
        self.finished_label.setText("<b>Finished!</b>")
        self.complete = True
        self.completeChanged.emit()

    @Slot()
    def update_unarchive(self) -> None:
        self.unarchive_progressbar.setMaximum(1)
        self.unarchive_progressbar.setValue(1)

    @Slot()
    def update_download(self) -> None:
        self.download_progressbar.setMaximum(1)
        self.download_progressbar.setValue(1)
        self.unarchive_progressbar.setMaximum(0)
        self.unarchive_progressbar.setValue(0)

    @Slot(object, name="fixDbImport")
    def fix_db_import(self, missing: set) -> None:
        """Halt and delete the importing thread, ask the user for input
        and restart the worker thread with the new information.

        Customized for ABPackage problems
        """
        self.main_worker_thread.exit(1)

        options = [(db, list(bd.databases)) for db in missing]
        linker = DatabaseLinkingDialog.relink_bw2package(options, self)
        if linker.exec_() == DatabaseLinkingDialog.Accepted:
            self.relink_data = linker.links
        else:
            # If the user at any point did not accept their choice, fail.
            import_signals.import_failure.emit(
                (
                    "Missing databases",
                    "Package data links to database names that do not exist: {}".format(
                        missing
                    ),
                )
            )
            return
        # Restart the page
        self.initializePage()

    @Slot(object, object, name="fixExcelImport")
    def fix_excel_import(self, exchanges: list, missing: set) -> None:
        """Halt and delete the importing thread, ask the user for input
        and restart the worker thread with the new information.

        Customized for ABExcelImporter problems
        """
        self.main_worker_thread.exit(1)

        # Iterate through the missing databases, asking user input.
        options = [(db, list(bd.databases)) for db in missing]
        linker = DatabaseLinkingDialog.relink_excel(options, self)
        if linker.exec_() == DatabaseLinkingDialog.Accepted:
            self.relink_data = linker.links
        else:
            error = (
                "Unlinked exchanges",
                "Excel data contains exchanges that could not be linked.",
                exchanges,
            )
            import_signals.import_failure_detailed.emit(
                QtWidgets.QMessageBox.Warning, error
            )
            return
        # Restart the page
        self.initializePage()

    @Slot(str, name="handleUnzipFailed")
    def report_failed_unarchive(self, file: str) -> None:
        """Handle the issue where the 7z file for ecoinvent/spold files is
        in some way corrupted.
        """
        self.main_worker_thread.exit(1)

        error = (
            "Corrupted (.7z) archive",
            "The archive '{}' is corrupted, please remove and re-download it.".format(
                file
            ),
        )
        import_signals.import_failure_detailed.emit(
            QtWidgets.QMessageBox.Warning, error
        )
        return


class MainWorkerThread(ABThread):
    def __init__(self, downloader: "ABEcoinventDownloader", parent=None):
        super().__init__(parent)
        self.downloader = downloader
        self.forwast_url = (
            "https://lca-net.com/wp-content/uploads/forwast.bw2package.zip"
        )
        self.db_name = None
        self.archive_path = None
        self.datasets_path = None
        self.use_forwast = None
        self.use_local = None
        self.relink = {}

    def update(
        self,
        db_name: str,
        archive_path=None,
        datasets_path=None,
        use_forwast=False,
        use_local=False,
        relink=None,
    ) -> None:
        self.db_name = db_name
        self.archive_path = archive_path
        if datasets_path:
            self.datasets_path = Path(datasets_path)
        self.use_forwast = use_forwast
        self.use_local = use_local
        self.relink = relink or {}

    def run_safely(self):
        # Set the cancel sentinal to false whenever the thread (re-)starts
        import_signals.cancel_sentinel = False
        if self.use_forwast:
            self.run_forwast()
        elif self.use_local:  # excel or bw2package
            self.run_local_import()
        elif self.datasets_path:  # ecospold2 files
            self.run_import(self.datasets_path)
        elif self.archive_path:  # 7zip file
            self.run_extract_import()
        else:
            self.run_ecoinvent()

    def run_ecoinvent(self) -> None:
        """Run the ecoinvent downloader from start to finish."""
        archive_file = self.run_download()

        if os.path.isdir(archive_file):
            import_signals.unarchive_finished.emit()
            self.run_import(archive_file.joinpath("datasets"))
        else:
            with tempfile.TemporaryDirectory() as tempdir:
                temp_dir = Path(tempdir)
                if not import_signals.cancel_sentinel:
                    self.run_extract(archive_file, temp_dir)
                if not import_signals.cancel_sentinel:
                    dataset_dir = temp_dir.joinpath("datasets")
                    self.run_import(dataset_dir)

    def run_forwast(self) -> None:
        """Adapted from pjamesjoyce/lcopt."""
        response = requests.get(self.forwast_url)
        forwast_zip = zipfile.ZipFile(io.BytesIO(response.content))
        import_signals.download_complete.emit()
        with tempfile.TemporaryDirectory() as tempdir:
            temp_dir = Path(tempdir)
            if not import_signals.cancel_sentinel:
                forwast_zip.extractall(tempdir)
                import_signals.unarchive_finished.emit()
            if not import_signals.cancel_sentinel:
                import_signals.extraction_progress.emit(0, 0)
                import_signals.strategy_progress.emit(0, 0)
                import_signals.db_progress.emit(0, 0)
                BW2Package.import_file(str(temp_dir.joinpath("forwast.bw2package")))
            if self.db_name.lower() != "forwast":
                bd.Database("forwast").rename(self.db_name)
            if not import_signals.cancel_sentinel:
                import_signals.extraction_progress.emit(1, 1)
                import_signals.strategy_progress.emit(1, 1)
                import_signals.db_progress.emit(1, 1)
                import_signals.finished.emit()
            else:
                self.delete_canceled_db()

    def run_download(self) -> Path:
        """Use the connected ecoinvent downloader."""
        filepath = self.downloader.download()
        import_signals.download_complete.emit()
        return filepath

    def run_extract(self, archive_file: Path, temp_dir: Path) -> None:
        """Use the connected ecoinvent downloader to extract the downloaded
        7zip file.
        """
        try:
            self.downloader.extract(archive_file, temp_dir)
        except Exception:
            import_signals.cancel_sentinel = True
            import_signals.unarchive_failed.emit(temp_dir)
        else:
            import_signals.unarchive_finished.emit()

    def run_extract_import(self) -> None:
        """Combine the extract and import steps when beginning from a selected
        7zip archive.

        By default, look in the 'datasets' folder because this is how ecoinvent
        7zip archives are structured. If this folder is not found, fall back
        to using the temporary directory instead.
        """
        self.downloader.out_path = self.archive_path
        with tempfile.TemporaryDirectory() as tempdir:
            temp_dir = Path(tempdir)
            self.run_extract(Path(self.archive_path), temp_dir)
            if not import_signals.cancel_sentinel:
                # Working with ecoinvent 7z file? look for 'datasets' dir
                eco_dir = temp_dir.joinpath("datasets")
                if eco_dir.exists() and eco_dir.is_dir():
                    self.run_import(eco_dir)
                else:
                    # Use the temp dir itself instead.
                    self.run_import(temp_dir)

    def run_import(self, import_dir: Path) -> None:
        """Use the given dataset path to import the ecospold2 files."""
        try:
            importer = SingleOutputEcospold2Importer(
                str(import_dir),
                self.db_name,
                extractor=ActivityBrowserExtractor,
                signal=import_signals.strategy_progress,
            )
            importer.apply_strategies()
            # backend is a custom implementation that wraps sqlite database
            importer.write_database(backend="activitybrowser")
            if not import_signals.cancel_sentinel:
                import_signals.finished.emit()
            else:
                self.delete_canceled_db()
        except errors.ImportCanceledError:
            self.delete_canceled_db()
        except bw2data.errors.InvalidExchange:
            # Likely caused by new version of ecoinvent not finding required
            # biosphere flows.
            self.delete_canceled_db()
            import_signals.import_failure.emit(
                (
                    "Missing exchanges",
                    "The import failed because the biosphere3 database of this project is incompatible with the "
                    "version of ecoinvent that you're trying to install",
                )
            )

    def run_local_import(self):
        """Perform an import on a local file.

        This method supports both BW2Package files and excel files.
        """
        try:
            import_signals.db_progress.emit(0, 0)
            archive = Path(self.archive_path)
            if archive.suffix in {".xlsx", ".xls"}:
                result = ABExcelImporter.simple_automated_import(
                    self.archive_path, self.db_name, self.relink
                )
                # signals.parameters_changed.emit()
            else:
                result = ABPackage.import_file(
                    self.archive_path, relink=self.relink, rename=self.db_name
                )
            if not import_signals.cancel_sentinel:
                db = next(iter(result))
                # With the changes to the ABExcelImporter and ABPackage classes
                # this should not really trigger for data exported from AB.
                if db.name != self.db_name:
                    log.warning(
                        "renaming database '{}' to '{}', parameters lost.".format(
                            db.name, self.db_name
                        )
                    )
                    db.rename(self.db_name)
                import_signals.db_progress.emit(1, 1)
                import_signals.finished.emit()
            else:
                self.delete_canceled_db()
        except errors.InvalidPackage as e:
            # BW2package import failed, required databases are missing
            self.delete_canceled_db()
            import_signals.missing_dbs.emit(e.args[1])
        except errors.ImportCanceledError:
            self.delete_canceled_db()
        except errors.InvalidExchange:
            self.delete_canceled_db()
            import_signals.import_failure.emit(
                (
                    "Missing exchanges",
                    "The import has failed, likely due missing exchanges.",
                )
            )
        except errors.UnknownObject as e:
            # BW2Package import failed because the object was not understood
            self.delete_canceled_db()
            import_signals.import_failure.emit(("Unknown object", str(e)))
        except errors.StrategyError as e:
            # Excel import failed because extra databases were found, relink
            log.error(
                "Could not link exchanges, here are 10 examples.:"
            )  # THREAD UNSAFE FUNCTIONS
            self.delete_canceled_db()
            import_signals.links_required.emit(e.args[0], e.args[1])
        except errors.LinkingFailed as e:
            # Excel import failed after asking user to relink.
            error = (
                "Unlinked exchanges",
                "Some exchanges could not be linked in databases: '[{}]'".format(
                    ", ".join(e.args[1])
                ),
                e.args[0],
            )
            import_signals.import_failure_detailed.emit(
                QtWidgets.QMessageBox.Critical, error
            )
        except ValueError as e:
            # Relinking of BW2Package strategy has failed.
            import_signals.import_failure.emit(("Relinking failed", e.args[0]))

    def delete_canceled_db(self):
        if self.db_name in bd.databases:
            del bd.databases[self.db_name]
            log.info(f"Database {self.db_name} deleted!")


class EcoinventLoginPage(QtWidgets.QWizardPage):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Login")
        self.setSubTitle("Login with your ecoinvent credentials to authorize the download")

        # create username field
        self.username = QtWidgets.QLineEdit()
        self.username.setPlaceholderText('ecoinvent username')
        self.registerField("username*", self.username)

        # create password field and set hidden
        self.password = QtWidgets.QLineEdit()
        self.password.setPlaceholderText('ecoinvent password'),
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.registerField("password*", self.password)

        # empty message for now, will be used in case of wrong password or other error
        self.message = QtWidgets.QLabel()

        # set layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.username)
        layout.addWidget(self.password)
        layout.addWidget(self.message)

        self.setLayout(layout)

    def initializePage(self):
        # on initialization set stored username & password
        settings = ei.Settings()
        self.username.setText(settings.username)
        self.password.setText(settings.password)

    def validatePage(self):
        # set waitcursor because we're making http requests which take long
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        # set the provided settings and check if we can get a version list (i.e. logon was succesful)
        try:
            settings = ei.Settings(username=self.username.text(), password=self.password.text())
            release = ei.EcoinventRelease(settings)
            release.list_versions()

        # logon was unsuccesful
        except requests.exceptions.HTTPError as e:
            QtWidgets.QApplication.restoreOverrideCursor()

            # in case of 401: Unauthorized, we prompt for a retry of logon
            if e.response.status_code == 401:
                self.message.setText("Invalid username and/or password, please try again.")
                return False
            # else, other HTTPError, try again later maybe? Raise exception for logging
            else:
                self.message.setText("Unknown connection error, try again later.")
                raise e

        # in case of success, set the settings for permanent use
        ei.permanent_setting("username", self.username.text())
        ei.permanent_setting("password", self.password.text())
        return True

    def nextId(self):
        return DatabaseImportWizard.EI_VERSION


class LoginThread(QtCore.QThread):
    def __init__(self, downloader: "ABEcoinventDownloader", parent=None):
        super().__init__(parent)
        self.downloader = downloader

    def update(self, username: str, password: str) -> None:
        self.downloader.username = username
        self.downloader.password = password

    def run(self):
        error_message = None
        try:
            login_success, error_message = self.downloader.login()
        except Exception as e:
            log.error(str(e), exc_info=True)
            import_signals.login_success.emit(False)
            msg = str(e)
            cs = ei.CachedStorage()
            if len(cs.catalogue) > 0:
                msg += (
                    "\n\nIf you work offline you can use your previously downloaded databases"
                    + " via the archive option of the import wizard."
                )
            import_signals.connection_problem.emit(("Unexpected error", msg))
        else:
            import_signals.login_success.emit(login_success)
        finally:
            if error_message:
                import_signals.connection_problem.emit(error_message)


class EcoinventVersionPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard: "DatabaseImportWizard" = self.parent()
        self.description_label = QtWidgets.QLabel(
            "Choose ecoinvent version and system model:"
        )
        self.db_dict = None
        self.requires_database_creation = False
        self.version_combobox = QtWidgets.QComboBox()
        self.version_combobox.currentTextChanged.connect(
            self.update_system_model_combobox
        )
        self.system_model_combobox = QtWidgets.QComboBox()

        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.description_label, 0, 0, 1, 3)
        layout.addWidget(QtWidgets.QLabel("Version: "), 1, 0)
        layout.addWidget(self.version_combobox, 1, 1, 1, 2)
        layout.addWidget(QtWidgets.QLabel("System model: "), 2, 0)
        layout.addWidget(self.system_model_combobox, 2, 1, 1, 2)
        self.setLayout(layout)

    def initializePage(self):
        available_versions = self.wizard.downloader.list_versions()
        QtWidgets.QApplication.restoreOverrideCursor()
        shown_versions = {version for version in available_versions}
        # Catch for incorrect 'universal' key presence
        # (introduced in version 3.6 of ecoinvent)
        if "universal" in shown_versions:
            shown_versions.remove("universal")
        self.version_combobox.clear()
        self.system_model_combobox.clear()
        versions = sort_semantic_versions(shown_versions)
        self.version_combobox.addItems(versions)
        if bool(self.version_combobox.count()):
            # Adding the items will cause system_model_combobox to update
            # and show the correct list, this is just to be sure.
            self.update_system_model_combobox(self.version_combobox.currentText())
        else:
            # Raise an error if the version_combobox is empty
            import_signals.connection_problem.emit(
                (
                    "Cannot find files",
                    "Cannot find any valid data with the given login credentials",
                )
            )
            self.wizard.back()

    def validatePage(self):
        # version = self.version_combobox.currentText()
        # bd.preferences["biosphere_database"] = "ecoinvent-{}-biosphere".format(version)
        # bd.preferences.flush()
        # if bd.preferences["biosphere_database"] not in databases:
        #     self.requires_database_creation = True
        return True

    def nextId(self):
        # if self.requires_database_creation:
        #     return DatabaseImportWizard.DB_BIOSPHERE_CREATION
        return DatabaseImportWizard.DB_NAME

    @Slot(str)
    def update_system_model_combobox(self, version: str) -> None:
        """Updates the `system_model_combobox` whenever the user selects a
        different ecoinvent version.
        """
        self.system_model_combobox.clear()
        items = self.wizard.downloader.list_system_models(version)
        items = sorted(items, reverse=True)
        self.system_model_combobox.addItems(items)


class LocalDatabaseImportPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.wizard: QtWidgets.QWizard = parent
        self.path = QtWidgets.QLineEdit()
        self.path.setReadOnly(True)
        self.path.textChanged.connect(self.changed)
        self.path_btn = QtWidgets.QPushButton("Browse")
        self.path_btn.clicked.connect(self.browse)
        self.complete = False

        box = QtWidgets.QGroupBox("Import local database file:")
        grid_layout = QtWidgets.QGridLayout()
        layout = QtWidgets.QVBoxLayout()
        grid_layout.addWidget(QtWidgets.QLabel("Path to file*"), 0, 0, 1, 1)
        grid_layout.addWidget(self.path, 0, 1, 1, 2)
        grid_layout.addWidget(self.path_btn, 0, 3, 1, 1)
        box.setLayout(grid_layout)
        box.setStyleSheet(style_group_box.border_title)
        layout.addWidget(box)
        self.setLayout(layout)

        # Register field to ensure user cannot advance without selecting file.
        self.registerField("import_path*", self.path)

    def initializePage(self):
        self.path.clear()

    def nextId(self):
        self.wizard.setField("archive_path", self.path.text())
        return DatabaseImportWizard.DB_NAME

    def browse(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self, caption="Select a valid BW2Package file"
        )
        if path:
            self.path.setText(path)

    def changed(self):
        path = Path(self.path.text())
        exists = path.is_file()
        valid = path.suffix.lower() == ".bw2package"
        if exists and not valid:
            import_signals.import_failure.emit(
                (
                    "Invalid extension",
                    "Expecting 'local' import database file to have '.bw2package' extension",
                )
            )
        self.complete = all([exists, valid])
        self.completeChanged.emit()

    def isComplete(self):
        return self.complete


class ExcelDatabaseImport(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.wizard: QtWidgets.QWizard = parent
        self.path = QtWidgets.QLineEdit()
        self.path.setReadOnly(True)
        self.path.textChanged.connect(self.changed)
        self.path_btn = QtWidgets.QPushButton("Browse")
        self.path_btn.clicked.connect(self.browse)
        self.complete = False

        option_box = QtWidgets.QGroupBox("Import excel database file:")
        grid_layout = QtWidgets.QGridLayout()
        layout = QtWidgets.QVBoxLayout()
        grid_layout.addWidget(QtWidgets.QLabel("Path to file*"), 0, 0, 1, 1)
        grid_layout.addWidget(self.path, 0, 1, 1, 2)
        grid_layout.addWidget(self.path_btn, 0, 3, 1, 1)
        option_box.setLayout(grid_layout)
        option_box.setStyleSheet(style_group_box.border_title)
        layout.addWidget(option_box)
        self.setLayout(layout)

        # Register field to ensure user cannot advance without selecting file.
        self.registerField("excel_path*", self.path)

    def initializePage(self):
        self.path.clear()

    def nextId(self):
        self.wizard.setField("archive_path", self.path.text())
        return DatabaseImportWizard.DB_NAME

    @Slot(name="browseFile")
    def browse(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self,
            caption="Select an excel database file",
            filter="Excel (*.xlsx);; All Files (*.*)",
        )
        if path:
            self.path.setText(path)

    @Slot(name="pathChanged")
    def changed(self) -> None:
        path = Path(self.path.text())
        exists = path.is_file()
        valid = path.suffix.lower() in {".xlsx", ".xls"}
        if exists and not valid:
            import_signals.import_failure.emit(
                (
                    "Invalid extension",
                    "Expecting excel file to have '.xls' or '.xlsx' extension",
                )
            )
        self.complete = all([exists, valid])
        self.completeChanged.emit()

    def isComplete(self):
        return self.complete


class ActivityBrowserExtractor(Ecospold2DataExtractor):
    """
    - modified from bw2io
    - qt and python multiprocessing don't like each other on windows
    - need to display progress in gui
    """

    @classmethod
    def extract(cls, dirpath: str, db_name: str, *args, **kwargs):
        dir_path = Path(dirpath)
        assert dir_path.exists(), "Given path {} does not exist.".format(dir_path)
        if dir_path.is_dir():
            file_list = [fn.name for fn in dir_path.glob("*.spold")]
        elif dir_path.is_file():
            file_list = [dir_path.name]
        else:
            raise OSError("Can't understand path {}".format(dirpath))

        data = []
        total = len(file_list)
        dir_path = str(dir_path)
        for i, filename in enumerate(file_list, start=1):
            if import_signals.cancel_sentinel:
                log.info(f"Extraction canceled at position {i}!")
                raise errors.ImportCanceledError

            data.append(cls.extract_activity(dir_path, filename, db_name))
            import_signals.extraction_progress.emit(i, total)

        return data


class ActivityBrowserBackend(bd.backends.SQLiteBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ab_current_index = 0
        self._ab_total = 0

    def _efficient_write_many_data(self, *args, **kwargs):
        data = args[0]
        self._ab_total = len(data)
        super()._efficient_write_many_data(*args, **kwargs)

    def _efficient_write_dataset(self, *args, **kwargs):
        if import_signals.cancel_sentinel:
            log.info(f"\nWriting canceled at position {self._ab_current_index}!")
            raise errors.ImportCanceledError
        self._ab_current_index += 1
        import_signals.db_progress.emit(self._ab_current_index, self._ab_total)
        return super()._efficient_write_dataset(*args, **kwargs)


bd.config.backends["activitybrowser"] = ActivityBrowserBackend

class ImportSignals(QtCore.QObject):
    extraction_progress = Signal(int, int)
    strategy_progress = Signal(int, int)
    db_progress = Signal(int, int)
    finalizing = Signal()
    finished = Signal()
    unarchive_finished = Signal()
    unarchive_failed = Signal(str)
    download_complete = Signal()
    import_failure = Signal(tuple)
    import_failure_detailed = Signal(object, tuple)
    cancel_sentinel = False
    login_success = Signal(bool)
    connection_problem = Signal(tuple)
    # Allow transmission of missing databases
    missing_dbs = Signal(object)
    links_required = Signal(object, object)


import_signals = ImportSignals()


class ABEcoinventDownloader:
    def __init__(
        self,
        version: typing.Optional[str] = None,
        system_model: typing.Optional[str] = None,
        release_type: typing.Optional[ei.ReleaseType] = None,
    ):
        self.version = version
        self.system_model = system_model
        self._release_type = release_type
        self._settings = ei.Settings()
        self.update_ecoinvent_release()

    def update_ecoinvent_release(self):
        try:
            self._release = ei.EcoinventRelease(self._settings)
        except ValueError:
            self._release = None

    @property
    def release(self) -> ei.EcoinventRelease:
        if self._release is None:
            raise ValueError("ecoinvent release has not been initialized properly")
        return self._release

    @property
    def username(self) -> typing.Optional[str]:
        return self._settings.username

    @username.setter
    def username(self, value: str):
        self._settings.username = value
        self.update_ecoinvent_release()

    @property
    def password(self) -> typing.Optional[str]:
        return self._settings.password

    @password.setter
    def password(self, value: str):
        self._settings.password = value
        self.update_ecoinvent_release()

    @property
    def release_type(self):
        return self._release_type

    @release_type.setter
    def release_type(self, value: typing.Union[str, ei.ReleaseType]):
        if isinstance(value, ei.ReleaseType):
            self._release_type = value
            return

        if isinstance(value, str):
            self._release_type = ei.ReleaseType[value]
            return

        raise ValueError("invalid value provided for release_type")

    def login(self) -> (bool, typing.Optional[typing.Tuple[str, str]]):
        release = ei.EcoinventRelease(self._settings)
        error_message = None
        try:
            release.login()
            login_success = True
        except (
            requests.ConnectTimeout,
            requests.ReadTimeout,
            requests.ConnectionError,
        ) as e:
            login_success = False
            error_message = (
                "Connection Problem",
                "The request timed out, please check your internet connection!",
            )
        except requests.exceptions.HTTPError as e:
            login_success = False
            error_message = None
            if e.response.status_code != 401:
                log.error(
                    "Unexpected status code (%d) received when trying to list ecoinvent_versions, response: %s",
                    e.response.status_code,
                    e.response.text,
                )
                error_message = (
                    "Unexpected Problem",
                    "An unexpected error occurred, please try again status code %d"
                    % e.response.status_code,
                )

        return login_success, error_message

    @lru_cache(maxsize=1)
    def list_versions(self):
        return self._release.list_versions()

    @lru_cache(maxsize=100)
    def list_system_models(self, version: str):
        if version == "":
            return []
        return self._release.list_system_models(version)

    def download(self) -> Path:
        return self.release.get_release(
            version=self.version,
            system_model=self.system_model,
            release_type=self.release_type,
            extract=True,
        )

    @staticmethod
    def extract(filepath: Path, out_dir: Path = None):
        """
        Extract archive
        """
        if filepath.suffix.lower() == ".7z":
            with py7zr.SevenZipFile(filepath, "r") as archive:
                directory = out_dir or (filepath.parent / filepath.stem)
                if directory.exists():
                    shutil.rmtree(directory)
                archive.extractall(path=directory)
        else:
            raise ValueError("Unsupported archive format")
