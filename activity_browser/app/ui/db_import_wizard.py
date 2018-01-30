# -*- coding: utf-8 -*-
import os
import sys
import tempfile

import bs4
import requests
import patoolib
import brightway2 as bw
from bw2io.extractors import Ecospold2DataExtractor
from bw2io.importers.base_lci import LCIImporter
from bw2io import strategies
from bw2data import config
from bw2data.backends import SQLiteBackend
from PyQt5 import QtWidgets, QtCore

from ..signals import signals


class DatabaseImportWizard(QtWidgets.QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Database Import Wizard')
        self.import_type_page = ImportTypePage(self)
        self.choose_dir_page = ChooseDirPage(self)
        self.db_name_page = DBNamePage(self)
        self.confirmation_page = ConfirmationPage(self)
        self.import_page = ImportPage(self)
        self.archive_page = Choose7zArchivePage(self)
        self.ecoinvent_login_page = EcoinventLoginPage(self)
        self.ecoinvent_version_page = EcoinventVersionPage(self)
        self.pages = [
            self.import_type_page,
            self.ecoinvent_login_page,
            self.ecoinvent_version_page,
            self.archive_page,
            self.choose_dir_page,
            self.db_name_page,
            self.confirmation_page,
            self.import_page,
        ]
        for page in self.pages:
            self.addPage(page)
        self.show()

        # with this line, finish behaves like cancel and the wizard can be reused
        # db import is done when finish button becomes active
        self.button(QtWidgets.QWizard.FinishButton).clicked.connect(self.cleanup)

        # thread management
        self.button(QtWidgets.QWizard.CancelButton).clicked.connect(self.cancel_thread)

    @property
    def version(self):
        return self.ecoinvent_version_page.version_combobox.currentText()

    @property
    def system_model(self):
        return self.ecoinvent_version_page.system_model_combobox.currentText()

    @property
    def db_url(self):
        url = 'https://v33.ecoquery.ecoinvent.org'
        db_key = (self.version, self.system_model)
        return url + self.ecoinvent_version_page.db_dict[db_key]

    def closeEvent(self, event):
        '''
        close event now behaves similarly to cancel, because of self.reject
        like this the db wizard can be reused, ie starts from the beginning
        '''
        self.cancel_thread()
        event.accept()

    def cancel_thread(self):
        import_signals.import_canceled.emit()
        self.cleanup()

    def cleanup(self):
        self.reject()
        self.import_page.complete = False
        self.import_page.reset_progressbars()


class ImportTypePage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = self.parent()
        options = ['ecoinvent homepage',
                   'local 7z-archive',
                   'local directory with ecospold2 files']
        self.radio_buttons = [QtWidgets.QRadioButton(o) for o in options]
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
        if option_id == 2:
            self.wizard.import_type = 'directory'
            return self.wizard.pages.index(self.wizard.choose_dir_page)
        elif option_id == 1:
            self.wizard.import_type = 'archive'
            return self.wizard.pages.index(self.wizard.archive_page)
        else:
            self.wizard.import_type = 'homepage'
            if hasattr(self.wizard.ecoinvent_login_page, 'valid_pw'):
                return self.wizard.pages.index(self.wizard.ecoinvent_version_page)
            else:
                return self.wizard.pages.index(self.wizard.ecoinvent_login_page)


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


class Choose7zArchivePage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = self.parent()
        self.path_edit = QtWidgets.QLineEdit()
        self.registerField('archivepath*', self.path_edit)
        self.browse_button = QtWidgets.QPushButton('Browse')
        self.browse_button.clicked.connect(self.get_archive)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel(
            'Choose location of 7z archive:'))
        layout.addWidget(self.path_edit)
        browse_lay = QtWidgets.QHBoxLayout()
        browse_lay.addWidget(self.browse_button)
        browse_lay.addStretch(1)
        layout.addLayout(browse_lay)
        self.setLayout(layout)

    def get_archive(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Select 7z archive')
        if path:
            self.path_edit.setText(path)

    def validatePage(self):
        path = self.field('archivepath')
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

    def initializePage(self):
        warning = check_7z()
        if warning:
            QtWidgets.QMessageBox.warning(self, '7zip required!', warning)

    def nextId(self):
        return self.wizard.pages.index(self.wizard.db_name_page)


def check_7z():
    try:
        patoolib.find_archive_program('7z', 'extract')
    except patoolib.util.PatoolError as e:
        warning = ('This step requires a working installation of the 7zip program. <br>' +
                   'Please install 7zip on your system before continuing.<br>')
        if sys.platform == 'win32':
            warning += 'You can download it from <a href="http://www.7zip.org">www.7zip.org</a>.'
        elif sys.platform == 'darwin':
            warning += ('You can install 7zip with <a href="https://brew.sh">homebrew</a>.<br>' +
                        'brew install p7zip')
        elif sys.platform.startswith('linux'):
            warning += ("Use your linux distribtion's package manager for the installation.<br>" +
                        'eg: sudo apt install p7zip-full')
        else:
            warning += 'More infos here: <a href="http://www.7zip.org">www.7zip.org</a>'

        return warning
    return ''


class DBNamePage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = self.parent()
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

    def validatePage(self):
        db_name = self.name_edit.text()
        if db_name in bw.databases:
            warning = 'Database <b>{}</b> already exists in project <b>{}</b>!'.format(
                db_name, bw.projects.current)
            QtWidgets.QMessageBox.warning(self, 'Database exists!', warning)
            return False
        else:
            return True


class ConfirmationPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = self.parent()
        self.setCommitPage(True)
        self.setButtonText(2, 'Import Database')
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
            'Current Projcet: <b>{}</b>'.format(bw.projects.current))
        self.db_name_label.setText(
            'Name of the new database: <b>{}</b>'.format(self.field('db_name')))
        if self.wizard.import_type == 'directory':
            self.path_label.setText(
                'Path to directory with ecospold files:<br><b>{}</b>'.format(
                    self.field('dirpath')))
        elif self.wizard.import_type == 'archive':
            self.path_label.setText(
                'Path to 7z archive:<br><b>{}</b>'.format(
                    self.field('archivepath')))
        else:
            self.path_label.setText(
                'Ecoinvent version: <b>{}</b><br>Ecoinvent system model: <b>{}</b>'.format(
                    self.wizard.version, self.wizard.system_model))


class ImportPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFinalPage(True)
        self.wizard = self.parent()
        self.complete = False
        extraction_label = QtWidgets.QLabel('Extracting XML data from ecospold files:')
        self.extraction_progressbar = QtWidgets.QProgressBar()
        strategy_label = QtWidgets.QLabel('Applying brightway2 strategies:')
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
        self.download_progressbar.setVisible(False)
        self.unarchive_label = QtWidgets.QLabel('Decompressing the 7z archive:')
        self.unarchive_progressbar = QtWidgets.QProgressBar()
        layout.addWidget(self.download_label)
        layout.addWidget(self.download_progressbar)
        layout.addWidget(self.unarchive_label)
        layout.addWidget(self.unarchive_progressbar)

        layout.addWidget(extraction_label)
        layout.addWidget(self.extraction_progressbar)
        layout.addWidget(strategy_label)
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

        import_signals.unarchive_finished.connect(self.unarchive_finished_check)
        import_signals.download_complete.connect(self.unarchive)

        # Threads
        self.download_thread = DownloadWorkerThread()
        self.unarchive_thread_list = []
        self.import_thread = ImportWorkerThread()

    @QtCore.pyqtSlot(str)
    def unarchive_finished_check(self, extract_tempdir):
        if self.tempdir.name == extract_tempdir:
            self.update_unarchive()
            self.import_dir()

    def reset_progressbars(self):
        for pb in [self.extraction_progressbar, self.strategy_progressbar,
                   self.db_progressbar, self.finalizing_progressbar,
                   self.download_progressbar, self.unarchive_progressbar]:
            pb.reset()
        self.finished_label.setText('')

    def isComplete(self):
        return self.complete

    def initializePage(self):
        self.reset_progressbars()
        if self.wizard.import_type == 'directory':
            self.import_dir()
            self.unarchive_label.hide()
            self.unarchive_progressbar.hide()
        elif self.wizard.import_type == 'archive':
            self.archivepath = self.field('archivepath')
            self.unarchive()
        else:
            self.download_label.setVisible(True)
            self.download_progressbar.setVisible(True)
            self.unarchive_progressbar.setMaximum(1)
            self.download_tempdir = tempfile.TemporaryDirectory()
            self.archivepath = os.path.join(self.download_tempdir.name, 'db.7z')
            self.download_thread.update(
                self.wizard.ecoinvent_login_page.username,
                self.wizard.ecoinvent_login_page.password,
                self.wizard.db_url,
                self.download_tempdir.name
            )
            self.download_progressbar.setMaximum(0)
            self.download_progressbar.setMinimum(0)
            self.download_thread.start()

    def unarchive(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.unarchive_thread_list.append(UnarchiveWorkerThread())
        self.unarchive_thread_list[-1].update(self.archivepath, self.tempdir)
        self.unarchive_thread_list[-1].start()

    @QtCore.pyqtSlot(int, int)
    def update_extraction_progress(self, i, tot):
        self.extraction_progressbar.setMaximum(tot)
        self.extraction_progressbar.setValue(i)

    @QtCore.pyqtSlot(int, int)
    def update_strategy_progress(self, i, tot):
        self.strategy_progressbar.setMaximum(tot)
        self.strategy_progressbar.setValue(i)

    @QtCore.pyqtSlot(int, int)
    def update_db_progress(self, i, tot):
        self.db_progressbar.setMaximum(tot)
        self.db_progressbar.setValue(i)
        if i == tot:
            import_signals.finalizing.emit()

    def update_finalizing(self):
        self.finalizing_progressbar.setMinimum(0)
        self.finalizing_progressbar.setMaximum(0)

    def update_finished(self):
        self.finalizing_progressbar.setMaximum(1)
        self.finalizing_progressbar.setValue(1)
        self.finished_label.setText('<b>Finished!</b>')
        self.complete = True
        self.completeChanged.emit()
        signals.databases_changed.emit()
        if hasattr(self, 'tempdir'):
            self.tempdir.cleanup()

    def update_unarchive(self):
        self.unarchive_progressbar.setMaximum(1)
        self.unarchive_progressbar.setValue(1)

    def update_download(self):
        self.download_progressbar.setMaximum(1)
        self.download_progressbar.setValue(1)
        self.unarchive_progressbar.setMaximum(0)
        self.unarchive_progressbar.setValue(0)

    def import_dir(self):
        db_name = self.field('db_name')
        if self.wizard.import_type == 'directory':
            dirpath = self.field('dirpath')
        else:
            dirpath = os.path.join(self.tempdir.name, 'datasets')
        self.import_thread.update(dirpath, db_name)
        self.import_thread.start()


class DownloadWorkerThread(QtCore.QThread):
    def __init__(self):
        super().__init__()
        import_signals.import_canceled.connect(self.cancel)

    def update(self, username, password, db_url, tempdir):
        self.username = username
        self.password = password
        self.db_url = db_url
        self.tempdir = tempdir
        self.canceled = False

    def cancel(self):
        self.canceled = True

    def run(self):
        session = requests.Session()
        logon_url = 'https://v33.ecoquery.ecoinvent.org/Account/LogOn'
        post_data = {'UserName': self.username,
                     'Password': self.password,
                     'IsEncrypted': 'false',
                     'ReturnUrl': '/'}
        session.post(logon_url, post_data)
        if not len(session.cookies):
            # TODO: implement retry
            print('Login somehow failed!')
        file_content = session.get(self.db_url).content
        with open(os.path.join(self.tempdir, 'db.7z'), 'wb') as outfile:
            outfile.write(file_content)
        if not self.canceled:
            import_signals.download_complete.emit()


class UnarchiveWorkerThread(QtCore.QThread):
    def __init__(self):
        super().__init__()
        import_signals.import_canceled.connect(self.cancel)

    def update(self, archivepath, tempdir):
        self.archivepath = archivepath
        self.tempdir = tempdir
        self.canceled = False

    def cancel(self):
        self.canceled = True

    def run(self):
        patoolib.extract_archive(self.archivepath, outdir=self.tempdir.name)
        if not self.canceled:
            import_signals.unarchive_finished.emit(self.tempdir.name)


class ImportWorkerThread(QtCore.QThread):
    def __init__(self):
        super().__init__()
        import_signals.import_canceled.connect(self.cancel)

    def update(self, dirpath, db_name):
        self.dirpath = dirpath
        self.db_name = db_name
        self.canceled = False

    def cancel(self):
        self.canceled = True
        import_signals.cancel_sentinel = True

    def run(self):
        import_signals.cancel_sentinel = False
        try:
            importer = ActivityBrowserImporter(self.dirpath, self.db_name)
            if not self.canceled:
                importer.apply_strategies()
            if not self.canceled:
                importer.write_database(backend='activitybrowser')
            if not self.canceled:
                import_signals.finished.emit()
            else:
                self.delete_canceled_db()
        except ImportCanceledError:
            self.delete_canceled_db()

    def delete_canceled_db(self):
        if self.db_name in bw.databases:
            del bw.databases[self.db_name]
            print(f'Database {self.db_name} deleted!')


class EcoinventLoginPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = self.parent()
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
        self.success_label = QtWidgets.QLabel('')
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

        self.login_thread = LoginThread()

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
        self.session = requests.Session()
        self.login_thread.update(self.session, self.username, self.password)
        import_signals.login_success.connect(self.login_response)
        self.login_thread.start()

    @QtCore.pyqtSlot(bool)
    def login_response(self, success):
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


class LoginThread(QtCore.QThread):
    def __init__(self):
        super().__init__()
        self.logon_url = 'https://v33.ecoquery.ecoinvent.org/Account/LogOn'

    def update(self, session, username, password):
        self.session = session
        self.post_data = {'UserName': username,
                          'Password': password,
                          'IsEncrypted': 'false',
                          'ReturnUrl': '/'}

    def run(self):
        self.session.post(self.logon_url, self.post_data)
        success = bool(len(self.session.cookies))
        import_signals.login_success.emit(success)


class EcoinventVersionPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = self.parent()
        self.description_label = QtWidgets.QLabel('Choose ecoinvent version and system model:')
        self.version_combobox = QtWidgets.QComboBox()
        self.system_model_combobox = QtWidgets.QComboBox()

        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.description_label, 0, 0, 1, 3)
        layout.addWidget(QtWidgets.QLabel('Version: '), 1, 0)
        layout.addWidget(self.version_combobox, 1, 1, 1, 2)
        layout.addWidget(QtWidgets.QLabel('System model: '), 2, 0)
        layout.addWidget(self.system_model_combobox, 2, 1, 1, 2)
        self.setLayout(layout)

    def initializePage(self):
        if not hasattr(self, 'db_dict'):
            self.get_available_files()
        self.versions = sorted({k[0] for k in self.db_dict.keys()}, reverse=True)
        self.system_models = sorted({k[1] for k in self.db_dict.keys()}, reverse=True)
        self.version_combobox.clear()
        self.system_model_combobox.clear()
        self.version_combobox.addItems(self.versions)
        self.system_model_combobox.addItems(self.system_models)

    def get_available_files(self):
        files_url = 'https://v33.ecoquery.ecoinvent.org/File/Files'
        files_res = self.wizard.ecoinvent_login_page.session.get(files_url)
        soup = bs4.BeautifulSoup(files_res.text, 'html.parser')
        file_list = [l for l in soup.find_all('a', href=True) if
                     l['href'].startswith('/File/File?')]
        link_dict = {f.contents[0]: f['href'] for f in file_list}
        self.db_dict = {
            tuple(k.replace('ecoinvent ', '').split('_')[:2:]): v for k, v in
            link_dict.items() if k.endswith('.7z') and 'lc' not in k.lower()}

    def nextId(self):
        return self.wizard.pages.index(self.wizard.db_name_page)


class ActivityBrowserExtractor(Ecospold2DataExtractor):
    """
    - modified from bw2io
    - qt and python multiprocessing don't like each other on windows
    - need to display progress in gui
    """
    @classmethod
    def extract(cls, dirpath, db_name):
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


class ActivityBrowserImporter(LCIImporter):
    def __init__(self, dirpath, db_name):
        self.dirpath = dirpath
        self.db_name = db_name
        self.strategies = [
            strategies.normalize_units,
            strategies.remove_zero_amount_coproducts,
            strategies.remove_zero_amount_inputs_with_no_activity,
            strategies.remove_unnamed_parameters,
            strategies.es2_assign_only_product_with_amount_as_reference_product,
            strategies.assign_single_product_as_activity,
            strategies.create_composite_code,
            strategies.drop_unspecified_subcategories,
            strategies.link_biosphere_by_flow_uuid,
            strategies.link_internal_technosphere_by_composite_code,
            strategies.delete_exchanges_missing_activity,
            strategies.delete_ghost_exchanges,
            strategies.remove_uncertainty_from_negative_loss_exchanges,
            strategies.fix_unreasonably_high_lognormal_uncertainties,
            strategies.set_lognormal_loc_value
        ]
        self.data = ActivityBrowserExtractor.extract(self.dirpath, self.db_name)

    def apply_strategies(self):
        total = len(self.strategies)
        for i, strategy in enumerate(self.strategies, start=1):
            self.apply_strategy(strategy, False)
            import_signals.strategy_progress.emit(i, total)


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


config.backends['activitybrowser'] = ActivityBrowserBackend


class ImportCanceledError(Exception):
    pass


class ImportSignals(QtCore.QObject):
    extraction_progress = QtCore.pyqtSignal(int, int)
    strategy_progress = QtCore.pyqtSignal(int, int)
    db_progress = QtCore.pyqtSignal(int, int)
    finalizing = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()
    unarchive_finished = QtCore.pyqtSignal(str)
    download_complete = QtCore.pyqtSignal()
    biosphere_finished = QtCore.pyqtSignal()
    copydb_finished = QtCore.pyqtSignal()
    import_canceled = QtCore.pyqtSignal()
    cancel_sentinel = False
    login_success = QtCore.pyqtSignal(bool)


import_signals = ImportSignals()


class DefaultBiosphereDialog(QtWidgets.QProgressDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Biosphere and LCIA methods')
        self.setLabelText(
            'Adding default biosphere and LCIA methods to project <b>{}</b>:'.format(
                bw.projects.current)
        )
        self.setMinimum(0)
        self.setMaximum(0)
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


class CopyDatabaseDialog(QtWidgets.QProgressDialog):
    def __init__(self, copy_from, copy_to):
        super().__init__()
        self.setWindowTitle('Copying database')
        self.setLabelText(
            'Copying existing database <b>{}</b> to new database <b>{}</b>:'.format(
                copy_from, copy_to)
        )
        self.setMinimum(0)
        self.setMaximum(0)
        self.show()

        self.copydb_thread = CopyDatabaseThread(copy_from, copy_to)
        import_signals.copydb_finished.connect(self.finished)
        import_signals.copydb_finished.connect(self.copydb_thread.exit)
        self.copydb_thread.start()

    def finished(self):
        self.setMaximum(1)
        self.setValue(1)


class CopyDatabaseThread(QtCore.QThread):
    def __init__(self, copy_from, copy_to):
        super().__init__()
        self.copy_from = copy_from
        self.copy_to = copy_to

    def run(self):
        bw.Database(self.copy_from).copy(self.copy_to)
        import_signals.copydb_finished.emit()
        signals.databases_changed.emit()
