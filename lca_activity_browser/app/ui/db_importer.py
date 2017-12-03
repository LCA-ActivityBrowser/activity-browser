# -*- coding: utf-8 -*-
import os
import brightway2 as bw
from bw2io.extractors import Ecospold2DataExtractor
from bw2io.importers.base_lci import LCIImporter
from bw2io import strategies
from bw2data import config
from bw2data.backends import SQLiteBackend
from bw2data.backends.peewee import (
    sqlite3_lci_db, ActivityDataset, ExchangeDataset)
from bw2data.backends.peewee.utils import (
    dict_as_exchangedataset, dict_as_activitydataset
)
from bw2data.errors import InvalidExchange, UntypedExchange
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
        self.addPage(self.import_type_page)
        self.addPage(self.choose_dir_page)
        self.addPage(self.db_name_page)
        self.addPage(self.confirmation_page)
        self.addPage(self.import_page)
        self.show()


class ImportTypePage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        options = ['ecoinvent homepage',
                   'local 7z-archive',
                   'local directory with ecospold2 files']
        self.radio_buttons = [QtWidgets.QRadioButton(o) for o in options]
        self.option_box = QtWidgets.QGroupBox('Choose type of database import')
        box_layout = QtWidgets.QVBoxLayout()
        for i, button in enumerate(self.radio_buttons):
            box_layout.addWidget(button)
            if i == 2:
                button.setChecked(True)
            else:
                button.setEnabled(False)
        self.option_box.setLayout(box_layout)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.option_box)
        self.setLayout(self.layout)


class ChooseDirPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = self.parent()
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
        self.path = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Select directory with ecospold2 files')
        if os.path.isdir(self.path):
            self.path_edit.setText(self.path)
        else:
            # TODO warning to page
            print('invalid path')


class DBNamePage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.name_edit = QtWidgets.QLineEdit()
        self.registerField('db_name*', self.name_edit)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel(
            'Name of the new database:'))
        layout.addWidget(self.name_edit)
        self.setLayout(layout)

        # TODO check that name doesn't exist yet


class ConfirmationPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCommitPage(True)
        self.setButtonText(2, 'Import Database')
        self.wizard = self.parent()
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
        self.path_label.setText(
            'Path to directory with ecospold files:<br><b>{}</b>'.format(
                self.field('dirpath')))


class ImportPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = self.parent()
        self.complete = False
        extraction_label = QtWidgets.QLabel('Extracting XML data:')
        self.extraction_progressbar = QtWidgets.QProgressBar()
        strategy_label = QtWidgets.QLabel('Applying brightway2 strategies:')
        self.strategy_progressbar = QtWidgets.QProgressBar()
        db_label = QtWidgets.QLabel('Writing datasets to SQLite database:')
        self.db_progressbar = QtWidgets.QProgressBar()
        finalizing_label = QtWidgets.QLabel('Finalizing:')
        self.finalizing_progressbar = QtWidgets.QProgressBar()
        self.finished_label = QtWidgets.QLabel('')

        layout = QtWidgets.QVBoxLayout()
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

    def isComplete(self):
        return self.complete

    def initializePage(self):
        print('starting import')
        self.import_db()

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

    def import_db(self):
        db_name = self.field('db_name')
        dirpath = self.field('dirpath')
        self.worker_thread = ImportWorkerThread(dirpath, db_name)
        self.worker_thread.start()


class ImportWorkerThread(QtCore.QThread):
    def __init__(self, dirpath, db_name):
        super().__init__()
        self.dirpath = dirpath
        self.db_name = db_name

    def run(self):
        importer = ActivityBrowserImporter(self.dirpath, self.db_name)
        importer.apply_strategies()
        print(importer.statistics())
        importer.write_database(backend='activitybrowser')
        print('done')
        import_signals.finished.emit()


class ActivityBrowserExtractor(Ecospold2DataExtractor):
    """
    - modified from bw2io
    - qt and python multiprocessing don't like each other on windows
    - need to display progress in gui
    """
    @classmethod
    def extract(cls, dirpath, db_name):
        assert os.path.exists(dirpath)
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
    def _efficient_write_many_data(self, data, indices=True):
        be_complicated = len(data) >= 100 and indices
        if be_complicated:
            self._drop_indices()
        sqlite3_lci_db.autocommit = False
        try:
            sqlite3_lci_db.begin()
            self.delete(keep_params=True)
            exchanges, activities = [], []

            total = len(data)
            for index, (key, ds) in enumerate(data.items()):
                for exchange in ds.get('exchanges', []):
                    if 'input' not in exchange or 'amount' not in exchange:
                        raise InvalidExchange
                    if 'type' not in exchange:
                        raise UntypedExchange
                    exchange['output'] = key
                    exchanges.append(dict_as_exchangedataset(exchange))

                    if len(exchanges) > 125:
                        ExchangeDataset.insert_many(exchanges).execute()
                        exchanges = []

                ds = {k: v for k, v in ds.items() if k != "exchanges"}
                ds["database"] = key[0]
                ds["code"] = key[1]

                activities.append(dict_as_activitydataset(ds))

                if len(activities) > 125:
                    ActivityDataset.insert_many(activities).execute()
                    activities = []

                import_signals.db_progress.emit(index+1, total)

            if activities:
                ActivityDataset.insert_many(activities).execute()
            if exchanges:
                ExchangeDataset.insert_many(exchanges).execute()
            sqlite3_lci_db.commit()
        except:
            sqlite3_lci_db.rollback()
            raise
        finally:
            sqlite3_lci_db.autocommit = True
            if be_complicated:
                self._add_indices()


config.backends['activitybrowser'] = ActivityBrowserBackend


class ImportSignals(QtCore.QObject):
    extraction_progress = QtCore.pyqtSignal(int, int)
    strategy_progress = QtCore.pyqtSignal(int, int)
    db_progress = QtCore.pyqtSignal(int, int)
    finalizing = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()


import_signals = ImportSignals()
