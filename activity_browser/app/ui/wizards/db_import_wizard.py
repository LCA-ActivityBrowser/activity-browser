# -*- coding: utf-8 -*-
import os
import io
import subprocess
import tempfile
import warnings
import zipfile

import eidl
import requests
import brightway2 as bw
from bw2data.errors import InvalidExchange, UnknownObject
from bw2io import SingleOutputEcospold2Importer
from bw2io.errors import InvalidPackage, StrategyError
from bw2io.extractors import Ecospold2DataExtractor
from bw2data.backends import SQLiteBackend
from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Signal, Slot

from ...bwutils.commontasks import is_technosphere_db
from ...bwutils.strategies import relink_exchanges_bw2package
from ...bwutils.importers import ABExcelImporter
from ...signals import signals
from ..widgets import DatabaseRelinkDialog

# TODO: Rework the entire import wizard, the amount of different classes
#  and interwoven connections makes the entire thing nearly incomprehensible.


class DatabaseImportWizard(QtWidgets.QWizard):
    IMPORT_TYPE = 1
    EI_LOGIN = 2
    EI_VERSION = 3
    ARCHIVE = 4
    DIR = 5
    LOCAL = 6
    EXCEL = 7
    DB_NAME = 8
    CONFIRM = 9
    IMPORT = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self.downloader = ABEcoinventDownloader()
        self.setWindowTitle('Database Import Wizard')
        self.import_type_page = ImportTypePage(self)
        self.choose_dir_page = ChooseDirPage(self)
        self.db_name_page = DBNamePage(self)
        self.confirmation_page = ConfirmationPage(self)
        self.import_page = ImportPage(self)
        self.archive_page = Choose7zArchivePage(self)
        self.ecoinvent_login_page = EcoinventLoginPage(self)
        self.ecoinvent_version_page = EcoinventVersionPage(self)
        self.local_import_page = LocalDatabaseImportPage(self)
        self.excel_import_page = ExcelDatabaseImport(self)
        self.setPage(self.IMPORT_TYPE, self.import_type_page)
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
        self.show()

        # with this line, finish behaves like cancel and the wizard can be reused
        # db import is done when finish button becomes active
        self.button(QtWidgets.QWizard.FinishButton).clicked.connect(self.cleanup)

        # thread management
        self.button(QtWidgets.QWizard.CancelButton).clicked.connect(self.cancel_thread)
        self.button(QtWidgets.QWizard.CancelButton).clicked.connect(self.cancel_extraction)

        import_signals.connection_problem.connect(self.show_info)
        import_signals.import_failure.connect(self.show_info)

    @property
    def version(self):
        return self.ecoinvent_version_page.version_combobox.currentText()

    @property
    def system_model(self):
        return self.ecoinvent_version_page.system_model_combobox.currentText()

    def update_downloader(self):
        self.downloader.version = self.version
        self.downloader.system_model = self.system_model

    def closeEvent(self, event):
        """ Close event now behaves similarly to cancel, because of self.reject.

        This allows the import wizard to be reused, ie starts from the beginning
        """
        self.cancel_thread()
        self.cancel_extraction()
        event.accept()

    def cancel_thread(self):
        print('\nDatabase import interrupted!')
        import_signals.cancel_sentinel = True
        self.cleanup()

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

    def show_info(self, info):
        title, message = info
        QtWidgets.QMessageBox.information(self, title, message)


class ImportTypePage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = parent
        self.options = [
            ("Ecoinvent: download (login required)", "homepage"),
            ("Ecoinvent: local 7z-archive or previously downloaded database", "archive", DatabaseImportWizard.ARCHIVE),
            ("Ecoinvent: local directory with ecospold2 files", "directory", DatabaseImportWizard.DIR),
            ("Forwast: download", "forwast", DatabaseImportWizard.DB_NAME),
            ("Local Excel file", "local", DatabaseImportWizard.EXCEL),
            ("Local brightway database file", "local", DatabaseImportWizard.LOCAL),
        ]
        self.radio_buttons = [QtWidgets.QRadioButton(o[0]) for o in self.options]
        self.option_box = QtWidgets.QGroupBox('Choose type of database import')
        box_layout = QtWidgets.QVBoxLayout()
        for i, button in enumerate(self.radio_buttons):
            box_layout.addWidget(button)
            if i == 0:
                button.setChecked(True)
        self.option_box.setLayout(box_layout)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.option_box)
        self.setLayout(self.layout)

    def nextId(self):
        option_id = [b.isChecked() for b in self.radio_buttons].index(True)
        self.wizard.import_type = self.options[option_id][1]
        if option_id == 0:
            if hasattr(self.wizard.ecoinvent_login_page, 'valid_pw'):
                return DatabaseImportWizard.EI_VERSION
            else:
                return DatabaseImportWizard.EI_LOGIN
        else:
            return self.options[option_id][2]


class ChooseDirPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.path_edit = QtWidgets.QLineEdit()
        self.registerField('dirpath*', self.path_edit)
        self.browse_button = QtWidgets.QPushButton('Browse')
        self.browse_button.clicked.connect(self.get_directory)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel(
            'Choose location of existing ecospold2 directory:'))
        layout.addWidget(self.path_edit)
        browse_lay = QtWidgets.QHBoxLayout()
        browse_lay.addWidget(self.browse_button)
        browse_lay.addStretch(1)
        layout.addLayout(browse_lay)
        self.setLayout(layout)

    def get_directory(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Select directory with ecospold2 files')
        self.path_edit.setText(path)

    def validatePage(self):
        dir_path = self.field('dirpath')
        if not os.path.isdir(dir_path):
            warning = 'Not a directory:<br>{}'.format(dir_path)
            QtWidgets.QMessageBox.warning(self, 'Not a directory!', warning)
            return False
        else:
            spold_files = [f for f in os.listdir(dir_path) if f.endswith('.spold')]
            if not spold_files:
                warning = 'No ecospold files found in this directory:<br>{}'.format(dir_path)
                QtWidgets.QMessageBox.warning(self, 'No ecospold files!', warning)
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
        self.registerField('archive_path*', self.path_edit)
        self.browse_button = QtWidgets.QPushButton('Browse')
        self.browse_button.clicked.connect(self.get_archive)
        self.stored_combobox = QtWidgets.QComboBox()
        self.stored_combobox.activated.connect(self.update_stored)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel(
            'Choose location of 7z archive:'))
        layout.addWidget(self.path_edit)
        browse_lay = QtWidgets.QHBoxLayout()
        browse_lay.addWidget(self.browse_button)
        browse_lay.addStretch(1)
        layout.addLayout(browse_lay)
        layout.addWidget(QtWidgets.QLabel('Previous downloads:'))
        layout.addWidget(self.stored_combobox)
        self.setLayout(layout)

    def initializePage(self):
        self.stored_dbs = eidl.eidlstorage.stored_dbs
        self.stored_combobox.clear()
        self.stored_combobox.addItems(sorted(self.stored_dbs.keys()))

    def update_stored(self, index):
        self.path_edit.setText(self.stored_dbs[self.stored_combobox.currentText()])

    def get_archive(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Select 7z archive')
        if path:
            self.path_edit.setText(path)

    def validatePage(self):
        path = self.field('archive_path')
        if os.path.isfile(path):
            if path.lower().endswith('.7z'):
                return True
            else:
                warning = ('Unexpected filetype: <b>{}</b><br>Import might not work.' +
                           'Continue anyway?').format(os.path.split(path)[-1])
                answer = QtWidgets.QMessageBox.question(self, 'Not a 7zip archive!', warning)
                return answer == QtWidgets.QMessageBox.Yes
        else:
            warning = 'File not found:<br>{}'.format(path)
            QtWidgets.QMessageBox.warning(self, 'File not found!', warning)
            return False

    def nextId(self):
        return DatabaseImportWizard.DB_NAME


class DBNamePage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = parent
        self.name_edit = QtWidgets.QLineEdit()
        self.registerField('db_name*', self.name_edit)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel(
            'Name of the new database:'))
        layout.addWidget(self.name_edit)
        self.setLayout(layout)

    def initializePage(self):
        if self.wizard.import_type == 'homepage':
            version = self.wizard.version
            sys_mod = self.wizard.system_model
            self.name_edit.setText(sys_mod + version.replace('.', ''))
        elif self.wizard.import_type == 'forwast':
            self.name_edit.setText('Forwast')
        elif self.wizard.import_type == "local":
            filename = os.path.basename(self.field("archive_path"))
            if "." in filename:
                self.name_edit.setText(filename.split(".")[0])
            else:
                self.name_edit.setText(filename)

    def validatePage(self):
        db_name = self.name_edit.text()
        if db_name in bw.databases:
            warning = 'Database <b>{}</b> already exists in project <b>{}</b>!'.format(
                db_name, bw.projects.current)
            QtWidgets.QMessageBox.warning(self, 'Database exists!', warning)
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
        self.setButtonText(QtWidgets.QWizard.CommitButton, 'Import Database')
        self.current_project_label = QtWidgets.QLabel('empty')
        self.db_name_label = QtWidgets.QLabel('empty')
        self.path_label = QtWidgets.QLabel('empty')
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.current_project_label)
        layout.addWidget(self.db_name_label)
        layout.addWidget(self.path_label)
        self.setLayout(layout)

    def initializePage(self):
        self.current_project_label.setText(
            'Current Project: <b>{}</b>'.format(bw.projects.current))
        self.db_name_label.setText(
            'Name of the new database: <b>{}</b>'.format(self.field('db_name')))
        if self.wizard.import_type == 'directory':
            self.path_label.setText(
                'Path to directory with ecospold files:<br><b>{}</b>'.format(
                    self.field('dirpath')))
        elif self.wizard.import_type == 'archive':
            self.path_label.setText(
                'Path to 7z archive:<br><b>{}</b>'.format(
                    self.field('archive_path')))
        elif self.wizard.import_type == 'forwast':
            self.path_label.setOpenExternalLinks(True)
            self.path_label.setText(
                'Download forwast from <a href="https://lca-net.com/projects/show/forwast/">' +
                'https://lca-net.com/projects/show/forwast/</a>'
            )
        elif self.wizard.import_type == "local":
            self.path_label.setText("Path to local file:<br><b>{}</b>".format(
                self.field("archive_path")
            ))
        else:
            self.path_label.setText(
                'Ecoinvent version: <b>{}</b><br>Ecoinvent system model: <b>{}</b>'.format(
                    self.wizard.version, self.wizard.system_model))

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
        self.extraction_label = QtWidgets.QLabel('Extracting XML data from ecospold files:')
        self.extraction_progressbar = QtWidgets.QProgressBar()
        self.strategy_label = QtWidgets.QLabel('Applying brightway2 strategies:')
        self.strategy_progressbar = QtWidgets.QProgressBar()
        db_label = QtWidgets.QLabel('Writing datasets to SQLite database:')
        self.db_progressbar = QtWidgets.QProgressBar()
        finalizing_label = QtWidgets.QLabel('Finalizing:')
        self.finalizing_progressbar = QtWidgets.QProgressBar()
        self.finished_label = QtWidgets.QLabel('')

        layout = QtWidgets.QVBoxLayout()
        self.download_label = QtWidgets.QLabel('Downloading data from ecoinvent homepage:')
        self.download_label.setVisible(False)
        self.download_progressbar = QtWidgets.QProgressBar()
        self.unarchive_label = QtWidgets.QLabel('Decompressing the 7z archive:')
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

        # Threads
        self.main_worker_thread = MainWorkerThread(self.wizard.downloader, self)

    def reset_progressbars(self) -> None:
        for pb in [self.extraction_progressbar, self.strategy_progressbar,
                   self.db_progressbar, self.finalizing_progressbar,
                   self.download_progressbar, self.unarchive_progressbar]:
            pb.reset()
        self.finished_label.setText('')

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
        elif self.wizard.import_type == 'archive':
            self.unarchive_progressbar.setRange(0, 0)

    def initializePage(self):
        self.reset_progressbars()
        self.init_progressbars()
        self.wizard.update_downloader()
        if self.wizard.import_type == 'directory':
            self.main_worker_thread.update(db_name=self.field('db_name'),
                                           datasets_path=self.field('dirpath'))
        elif self.wizard.import_type == 'archive':
            self.main_worker_thread.update(db_name=self.field('db_name'),
                                           archive_path=self.field('archive_path'))
        elif self.wizard.import_type == 'forwast':
            self.main_worker_thread.update(db_name=self.field('db_name'), use_forwast=True)
        elif self.wizard.import_type == "local":
            kwargs = {
                "db_name": self.field("db_name"),
                "archive_path": self.field("archive_path"),
                "use_local": True,
                "relink": self.relink_data,
                "overwrite": self.field("overwrite_db"),
                "purge": self.field("purge_params"),
                "linker": self.field("link_db") if self.field("do_link") else None,
            }
            self.main_worker_thread.update(**kwargs)
        else:
            self.main_worker_thread.update(db_name=self.field('db_name'))
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
        self.finished_label.setText('<b>Finished!</b>')
        self.complete = True
        self.completeChanged.emit()
        signals.databases_changed.emit()

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
        """
        self.main_worker_thread.exit(1)

        # Iterate through the missing databases, asking user input.
        self.relink_data = {}
        for db in missing:
            linker = DatabaseRelinkDialog.start_relink(
                self, db, bw.databases.list
            )
            if linker.exec_() == DatabaseRelinkDialog.Accepted:
                self.relink_data[db] = linker.new_db
        # If the user at any point did not accept their choice, fail.
        if len(self.relink_data) != len(missing):
            import_signals.import_failure.emit(
                ("Missing databases",
                 "Package data links to database names that do not exist: {}".format(missing))
            )
            return
        # Restart the page
        self.initializePage()


class MainWorkerThread(QtCore.QThread):
    def __init__(self, downloader, parent=None):
        super().__init__(parent)
        self.downloader = downloader
        self.forwast_url = 'https://lca-net.com/wp-content/uploads/forwast.bw2package.zip'
        self.db_name = None
        self.archive_path = None
        self.datasets_path = None
        self.use_forwast = None
        self.use_local = None
        self.relink = {}
        self.kwargs = {}

    def update(self, db_name: str, archive_path=None, datasets_path=None,
               use_forwast=False, use_local=False, relink=None, **kwargs) -> None:
        self.db_name = db_name
        self.archive_path = archive_path
        self.datasets_path = datasets_path
        self.use_forwast = use_forwast
        self.use_local = use_local
        self.relink = relink or {}
        self.kwargs = kwargs

    def run(self):
        if self.use_forwast:
            self.run_forwast()
        elif self.use_local:
            self.run_local_import()
        else:
            self.run_ecoinvent()

    def run_ecoinvent(self):
        import_signals.cancel_sentinel = False
        with tempfile.TemporaryDirectory() as tempdir:
            dataset_dir = self.datasets_path or os.path.join(tempdir, "datasets")
            if not os.path.isdir(dataset_dir):
                if self.archive_path is None:
                    self.downloader.outdir = eidl.eidlstorage.eidl_dir
                    if self.downloader.check_stored():
                        import_signals.download_complete.emit()
                    else:
                        self.run_download()
                else:
                    self.downloader.out_path = self.archive_path
                if not import_signals.cancel_sentinel:
                    self.run_extract(tempdir)
            if not import_signals.cancel_sentinel:
                self.run_import(dataset_dir)

    def run_forwast(self):
        """
        adapted from pjamesjoyce/lcopt
        """
        import_signals.cancel_sentinel = False
        response = requests.get(self.forwast_url)
        forwast_zip = zipfile.ZipFile(io.BytesIO(response.content))
        import_signals.download_complete.emit()
        with tempfile.TemporaryDirectory() as tempdir:
            if not import_signals.cancel_sentinel:
                forwast_zip.extractall(tempdir)
                import_signals.unarchive_finished.emit()
            if not import_signals.cancel_sentinel:
                import_signals.extraction_progress.emit(0, 0)
                import_signals.strategy_progress.emit(0, 0)
                import_signals.db_progress.emit(0, 0)
                bw.BW2Package.import_file(os.path.join(tempdir, 'forwast.bw2package'))
            if self.db_name != 'forwast':
                bw.Database('forwast').rename(self.db_name)
            if not import_signals.cancel_sentinel:
                import_signals.extraction_progress.emit(1, 1)
                import_signals.strategy_progress.emit(1, 1)
                import_signals.db_progress.emit(1, 1)
                import_signals.finished.emit()
            else:
                self.delete_canceled_db()

    def run_download(self):
        self.downloader.download()
        import_signals.download_complete.emit()

    def run_extract(self, temp_dir):
        self.downloader.extract(target_dir=temp_dir)
        import_signals.unarchive_finished.emit()

    def run_import(self, import_dir):
        try:
            importer = SingleOutputEcospold2Importer(
                import_dir,
                self.db_name,
                extractor=ActivityBrowserExtractor,
                signal=import_signals.strategy_progress
            )
            importer.apply_strategies()
            importer.write_database(backend='activitybrowser')
            if not import_signals.cancel_sentinel:
                import_signals.finished.emit()
            else:
                self.delete_canceled_db()
        except ImportCanceledError:
            self.delete_canceled_db()
        except InvalidExchange:
            # Likely caused by new version of ecoinvent not finding required
            # biosphere flows.
            self.delete_canceled_db()
            import_signals.import_failure.emit(
                ("Missing exchanges", "The import failed as required biosphere"
                 " exchanges are missing from the biosphere3 database. Please"
                 " update the biosphere by using 'File' -> 'Update biosphere...'")
            )

    def run_local_import(self):
        """Perform an import on a local file.

        This method supports both BW2Package files and excel files.
        """
        try:
            import_signals.db_progress.emit(0, 0)
            if os.path.splitext(self.archive_path)[1] in {".xlsx", ".xls"}:
                result = ABExcelImporter.simple_automated_import(
                    self.archive_path, **self.kwargs
                )
            else:
                result = ABPackage.import_file(self.archive_path, relink=self.relink)
            if not import_signals.cancel_sentinel:
                db = next(iter(result))
                if db.name != self.db_name:
                    db.rename(self.db_name)
                import_signals.db_progress.emit(1, 1)
                import_signals.finished.emit()
            else:
                self.delete_canceled_db()
        except InvalidPackage as e:
            # Try and fix the issue through relinking.
            self.delete_canceled_db()
            import_signals.missing_dbs.emit(e.args[1])
        except ImportCanceledError:
            self.delete_canceled_db()
        except InvalidExchange:
            self.delete_canceled_db()
            import_signals.import_failure.emit(
                ("Missing exchanges", "The import has failed, likely due missing exchanges.")
            )
        except UnknownObject as e:
            self.delete_canceled_db()
            import_signals.import_failure.emit(
                ("Unknown object", str(e))
            )
        except StrategyError as e:
            self.delete_canceled_db()
            import_signals.import_failure.emit(
                ("Could not link exchanges", "One or more exchanges could not be linked.")
            )

    def delete_canceled_db(self):
        if self.db_name in bw.databases:
            del bw.databases[self.db_name]
            print(f'Database {self.db_name} deleted!')


class EcoinventLoginPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = parent
        self.complete = False
        self.description_label = QtWidgets.QLabel('Login to the ecoinvent homepage:')
        self.username_edit = QtWidgets.QLineEdit()
        self.username_edit.setPlaceholderText('ecoinvent username')
        self.password_edit = QtWidgets.QLineEdit()
        self.password_edit.setPlaceholderText('ecoinvent password'),
        self.password_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.login_button = QtWidgets.QPushButton('login')
        self.login_button.clicked.connect(self.login)
        self.login_button.setCheckable(True)
        self.password_edit.returnPressed.connect(self.login_button.click)
        self.success_label = QtWidgets.QLabel()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.description_label)
        layout.addWidget(self.username_edit)
        layout.addWidget(self.password_edit)
        hlay = QtWidgets.QHBoxLayout()
        hlay.addWidget(self.login_button)
        hlay.addStretch(1)
        layout.addLayout(hlay)
        layout.addWidget(self.success_label)
        self.setLayout(layout)

        self.login_thread = LoginThread(self.wizard.downloader)
        import_signals.login_success.connect(self.login_response)

    @property
    def username(self):
        if hasattr(self, 'valid_un'):
            return self.valid_un
        else:
            return self.username_edit.text()

    @property
    def password(self):
        if hasattr(self, 'valid_pw'):
            return self.valid_pw
        else:
            return self.password_edit.text()

    def isComplete(self):
        return self.complete

    def login(self):
        self.success_label.setText('Trying to login ...')
        self.login_thread.update(self.username, self.password)
        self.login_thread.start()

    @Slot(bool, name="handleLoginResponse")
    def login_response(self, success: bool):
        if not success:
            self.success_label.setText('Login failed!')
            self.complete = False
            self.completeChanged.emit()
            self.login_button.setChecked(False)
        else:
            self.username_edit.setEnabled(False)
            self.password_edit.setEnabled(False)
            self.login_button.setEnabled(False)
            self.valid_un = self.username
            self.valid_pw = self.password
            self.success_label.setText('Login successful!')
            self.complete = True
            self.completeChanged.emit()
            self.login_button.setChecked(False)
            self.wizard.next()

    def nextId(self):
        return DatabaseImportWizard.EI_VERSION


class LoginThread(QtCore.QThread):
    def __init__(self, downloader):
        super().__init__()
        self.downloader = downloader

    def update(self, username, password):
        self.downloader.username = username
        self.downloader.password = password

    def run(self):
        self.downloader.login()


class EcoinventVersionPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = self.parent()
        self.description_label = QtWidgets.QLabel('Choose ecoinvent version and system model:')
        self.db_dict = None
        self.system_models = {}
        self.version_combobox = QtWidgets.QComboBox()
        self.version_combobox.currentTextChanged.connect(self.update_system_model_combobox)
        self.system_model_combobox = QtWidgets.QComboBox()

        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.description_label, 0, 0, 1, 3)
        layout.addWidget(QtWidgets.QLabel('Version: '), 1, 0)
        layout.addWidget(self.version_combobox, 1, 1, 1, 2)
        layout.addWidget(QtWidgets.QLabel('System model: '), 2, 0)
        layout.addWidget(self.system_model_combobox, 2, 1, 1, 2)
        self.setLayout(layout)

    def initializePage(self):
        if self.db_dict is None:
            self.wizard.downloader.db_dict = self.wizard.downloader.get_available_files()
            self.db_dict = self.wizard.downloader.db_dict
        self.system_models = {
            version: sorted({k[1] for k in self.db_dict.keys() if k[0] == version}, reverse=True)
            for version in sorted({k[0] for k in self.db_dict.keys()}, reverse=True)
        }
        # Catch for incorrect 'universal' key presence
        # (introduced in version 3.6 of ecoinvent)
        if "universal" in self.system_models:
            del self.system_models["universal"]
        self.version_combobox.clear()
        self.system_model_combobox.clear()
        self.version_combobox.addItems(list(self.system_models.keys()))
        if bool(self.version_combobox.count()):
            # Adding the items will cause system_model_combobox to update
            # and show the correct list, this is just to be sure.
            self.update_system_model_combobox(self.version_combobox.currentText())
        else:
            # Raise an error if the version_combobox is empty
            import_signals.connection_problem.emit((
                "Cannot find files",
                "Cannot find any valid data with the given login credentials"
            ))
            self.wizard.back()

    def nextId(self):
        return DatabaseImportWizard.DB_NAME

    @Slot(str)
    def update_system_model_combobox(self, version: str) -> None:
        """ Updates the `system_model_combobox` whenever the user selects a
        different ecoinvent version.
        """
        self.system_model_combobox.clear()
        self.system_model_combobox.addItems(self.system_models[version])


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

        option_box = QtWidgets.QGroupBox("Import local database file:")
        grid_layout = QtWidgets.QGridLayout()
        layout = QtWidgets.QVBoxLayout()
        grid_layout.addWidget(QtWidgets.QLabel("Path to file*"), 0, 0, 1, 1)
        grid_layout.addWidget(self.path, 0, 1, 1, 2)
        grid_layout.addWidget(self.path_btn, 0, 3, 1, 1)
        option_box.setLayout(grid_layout)
        layout.addWidget(option_box)
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
        exists = True if os.path.isfile(self.path.text()) else False
        valid = False
        if exists:
            base, ext = os.path.splitext(self.path.text())
            valid = True if ext.lower() == ".bw2package" else False
            if not valid:
                import_signals.import_failure.emit(
                    ("Invalid extension", "Expecting 'local' import database file to have '.bw2package' extension")
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
        self.overwrite_db = QtWidgets.QCheckBox("Overwrite database.")
        self.overwrite_db.setToolTip("Will overwrite existing databases with the same name.")
        self.overwrite_db.setChecked(True)
        self.purge_params = QtWidgets.QCheckBox("Remove existing parameters from project.")
        self.purge_params.setToolTip("Will only remove parameters of the type found in the file.")
        self.purge_params.setChecked(False)
        self.link_option = QtWidgets.QCheckBox("Link against existing technosphere.")
        self.link_option.setToolTip("Attempts to find unlinked exchanges in the selected database.")
        self.link_option.setChecked(False)
        self.link_choice = QtWidgets.QComboBox()
        self.link_choice.addItems([db for db in bw.databases if is_technosphere_db(db)])
        self.link_choice.setHidden(True)
        self.link_option.toggled.connect(self.toggle_dropdown)
        self.complete = False

        option_box = QtWidgets.QGroupBox("Import excel database file:")
        grid_layout = QtWidgets.QGridLayout()
        layout = QtWidgets.QVBoxLayout()
        grid_layout.addWidget(QtWidgets.QLabel("Path to file*"), 0, 0, 1, 1)
        grid_layout.addWidget(self.path, 0, 1, 1, 2)
        grid_layout.addWidget(self.path_btn, 0, 3, 1, 1)
        grid_layout.addWidget(self.overwrite_db, 1, 0, 1, 3)
        grid_layout.addWidget(self.purge_params, 2, 0, 1, 3)
        grid_layout.addWidget(self.link_option, 3, 0, 1, 2)
        grid_layout.addWidget(self.link_choice, 3, 2, 1, 2)
        option_box.setLayout(grid_layout)
        layout.addWidget(option_box)
        self.setLayout(layout)

        # Register field to ensure user cannot advance without selecting file.
        self.registerField("excel_path*", self.path)
        self.registerField("overwrite_db", self.overwrite_db)
        self.registerField("purge_params", self.purge_params)
        self.registerField("do_link", self.link_option)
        self.registerField("link_db", self.link_choice)

    def initializePage(self):
        self.path.clear()
        self.overwrite_db.setChecked(True)
        self.purge_params.setChecked(False)
        self.link_option.setChecked(False)

    def nextId(self):
        self.wizard.setField("archive_path", self.path.text())
        return DatabaseImportWizard.DB_NAME

    @Slot(name="browseFile")
    def browse(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self, caption="Select an excel database file",
            filter="Excel (*.xlsx);; All Files (*.*)"
        )
        if path:
            self.path.setText(path)

    @Slot(name="pathChanged")
    def changed(self) -> None:
        exists = True if os.path.isfile(self.path.text()) else False
        valid = False
        if exists:
            base, ext = os.path.splitext(self.path.text())
            valid = True if ext.lower() in {".xlsx", ".xls"} else False
            if not valid:
                import_signals.import_failure.emit(
                    ("Invalid extension", "Expecting excel file to have '.xls' or '.xlsx' extension")
                )
        self.complete = all([exists, valid])
        self.completeChanged.emit()

    @Slot(bool, name="toggleDropdown")
    def toggle_dropdown(self, toggle: bool) -> None:
        self.link_choice.setHidden(not toggle)

    def isComplete(self):
        return self.complete


class ActivityBrowserExtractor(Ecospold2DataExtractor):
    """
    - modified from bw2io
    - qt and python multiprocessing don't like each other on windows
    - need to display progress in gui
    """
    @classmethod
    def extract(cls, dirpath, db_name, *args, **kwargs):
        assert os.path.exists(dirpath), dirpath
        if os.path.isdir(dirpath):
            filelist = [filename for filename in os.listdir(dirpath)
                        if os.path.isfile(os.path.join(dirpath, filename))
                        and filename.split(".")[-1].lower() == "spold"
                        ]
        elif os.path.isfile(dirpath):
            filelist = [dirpath]
        else:
            raise OSError("Can't understand path {}".format(dirpath))

        data = []
        total = len(filelist)
        for i, filename in enumerate(filelist, start=1):
            if import_signals.cancel_sentinel:
                print(f'Extraction canceled at position {i}!')
                raise ImportCanceledError

            data.append(cls.extract_activity(dirpath, filename, db_name))
            import_signals.extraction_progress.emit(i, total)

        return data


class ActivityBrowserBackend(SQLiteBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _efficient_write_many_data(self, *args, **kwargs):
        data = args[0]
        self.total = len(data)
        super()._efficient_write_many_data(*args, **kwargs)

    def _efficient_write_dataset(self, *args, **kwargs):
        index = args[0]
        if import_signals.cancel_sentinel:
            print(f'\nWriting canceled at position {index}!')
            raise ImportCanceledError
        import_signals.db_progress.emit(index+1, self.total)
        return super()._efficient_write_dataset(*args, **kwargs)


bw.config.backends['activitybrowser'] = ActivityBrowserBackend


class ImportCanceledError(Exception):
    pass


class ImportSignals(QtCore.QObject):
    extraction_progress = Signal(int, int)
    strategy_progress = Signal(int, int)
    db_progress = Signal(int, int)
    finalizing = Signal()
    finished = Signal()
    unarchive_finished = Signal()
    download_complete = Signal()
    biosphere_finished = Signal()
    import_failure = Signal(tuple)
    cancel_sentinel = False
    login_success = Signal(bool)
    connection_problem = Signal(tuple)
    # Allow transmission of missing databases
    missing_dbs = Signal(object)


import_signals = ImportSignals()


class DefaultBiosphereDialog(QtWidgets.QProgressDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Biosphere and impact categories')
        self.setLabelText(
            'Adding default biosphere and impact categories to project <b>{}</b>:'.format(
                bw.projects.current)
        )
        self.setRange(0, 0)
        self.show()

        self.biosphere_thread = DefaultBiosphereThread()
        import_signals.biosphere_finished.connect(self.finished)
        import_signals.biosphere_finished.connect(self.biosphere_thread.exit)
        self.biosphere_thread.start()

    def finished(self):
        self.setMaximum(1)
        self.setValue(1)


class DefaultBiosphereThread(QtCore.QThread):
    def run(self):
        bw.create_default_biosphere3()
        if not len(bw.methods):
            bw.create_default_lcia_methods()
        if not len(bw.migrations):
            bw.create_core_migrations()
        import_signals.biosphere_finished.emit()
        signals.change_project.emit(bw.projects.current)
        signals.project_selected.emit()


class ABEcoinventDownloader(eidl.EcoinventDownloader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extraction_process = None

    def login_success(self, success):
        import_signals.login_success.emit(success)

    def extract(self, target_dir):
        """ Override extract method to redirect the stdout to dev null.
        """
        extract_cmd = '7za x {} -o{}'.format(self.out_path, target_dir)
        self.extraction_process = subprocess.Popen(extract_cmd.split(), stdout=subprocess.DEVNULL)
        self.extraction_process.wait()

    def handle_connection_timeout(self):
        msg = "The request timed out, please check your internet connection!"
        if eidl.eidlstorage.stored_dbs:
            msg += ("\n\nIf you work offline you can use your previously downloaded databases" +
                    " via the archive option of the import wizard.")
        import_signals.connection_problem.emit(('Connection problem', msg))


class ABPackage(bw.BW2Package):
    """ Inherits from brightway2 `BW2Package` and handles importing BW2Packages.

    This implementation is done to raise exceptions and show errors on imports
    much faster.
    """
    @classmethod
    def evaluate_metadata(cls, metadata: dict, ignore_dbs: set):
        """ Take the given metadata dictionary and test it against realities
        of the current brightway project.
        """
        if "depends" in metadata:
            missing = set(metadata["depends"]).difference(bw.databases)
            # Remove any databases present in ignore_dbs (these will be relinked)
            missing = missing.difference(ignore_dbs)
            if missing:
                raise InvalidPackage(
                    "Package data links to database names that do not exist: {}".format(missing),
                    missing
                )

    @classmethod
    def load_file(cls, filepath, whitelist=True, relink: dict = None):
        """Similar to how the base class loads the data, but also perform
        a number of evaluations on the metadata.

        Also, if given a 'relink' dictionary, perform relinking of exchanges.
        """
        data = super().load_file(filepath, whitelist)
        relinking = set(relink.keys()) if relink else set([])
        if isinstance(data, dict):
            if "metadata" in data:
                cls.evaluate_metadata(data["metadata"], relinking)
            if relink:
                data["data"] = relink_exchanges_bw2package(data["data"], relink)
        else:
            for obj in data:
                if "metadata" in obj:
                    cls.evaluate_metadata(obj["metadata"], relinking)
                if relink:
                    obj["data"] = relink_exchanges_bw2package(obj["data"], relink)
        return data

    @classmethod
    def import_file(cls, filepath, whitelist=True, relink: dict = None):
        """Import bw2package file, and create the loaded objects, including registering, writing, and processing the created objects.

        Args:
            * *filepath* (str): Path of file to import
            * *whitelist* (bool): Apply whitelist to allowed types. Default is ``True``.
        Kwargs:
            * *relink* (dict): A dictionary of keys with which to relink exchanges
              within the imported package file.

        Returns:
            Created object or list of created objects.

        """
        loaded = cls.load_file(filepath, whitelist, relink)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if isinstance(loaded, dict):
                return cls._create_obj(loaded)
            else:
                return [cls._create_obj(o) for o in loaded]
