# -*- coding: utf-8 -*-
import datetime
import itertools

import arrow
import brightway2 as bw
import collections
from PyQt5 import QtGui, QtWidgets, QtCore
from bw2data.utils import natural_sort
from fuzzywuzzy import process

from activity_browser.app.settings import project_settings
from .table import ABTableWidget, ABTableItem
from .dataframe_table import ABDataFrameTable
from ..icons import icons
from ...signals import signals
from ...bwutils.metadata import AB_metadata
from ...bwutils.commontasks import is_technosphere_db


class DatabasesTable(ABTableWidget):
    """Displays metadata for the databases found within the selected project
    Dbs can be read-only or writable, with users preference persisted in settings file
    User double-clicks to see the activities and flows within a db
    A context menu (right click) provides further functionality"""
    # Column 4 header options: Size / Entries / Flows / Activities / Count / Activity Count..
    # ... 'Records' seems reasonable for a "database", and is quite short
    HEADERS = ["Name", "Records", "Read-only", "Depends", "Modified", ]
    # HEADERS = {
    #     "Name": 0,
    #     "Depends": 1,
    #     "Modified": 2,
    #     "Records": 3,
    #     "Read-only": 4,
    # }

    def __init__(self):
        super(DatabasesTable, self).__init__()
        self.name = "undefined"
        self.setColumnCount(len(self.HEADERS))
        self.connect_signals()
        self.setup_context_menu()

    def setup_context_menu(self):
        # delete database
        self.delete_database_action = QtWidgets.QAction(
            QtGui.QIcon(icons.delete), "Delete database", None
        )
        self.addAction(self.delete_database_action)
        self.delete_database_action.triggered.connect(
            lambda x: signals.delete_database.emit(
                self.currentItem().db_name
            )
        )

        # copy database
        self.copy_database_action = QtWidgets.QAction(
            QtGui.QIcon(icons.duplicate), "Copy database", None
        )
        self.addAction(self.copy_database_action)
        self.copy_database_action.triggered.connect(
            lambda x: signals.copy_database.emit(
                self.currentItem().db_name
            )
        )
        # add activity (important for empty databases)
        self.add_activity_action = QtWidgets.QAction(
            QtGui.QIcon(icons.add), "Add new activity", None
        )
        self.addAction(self.add_activity_action)
        self.add_activity_action.triggered.connect(
            lambda x: signals.new_activity.emit(
                self.currentItem().db_name
            )
        )

    def connect_signals(self):
        signals.project_selected.connect(self.sync)
        signals.databases_changed.connect(self.sync)
        self.itemDoubleClicked.connect(self.select_database)

    def select_database(self, item):
        signals.database_selected.emit(item.db_name)

    def read_only_changed(self, read_only, db):
        """User has clicked to update a db to either read-only or not"""
        project_settings.settings['read-only-databases'][db] = read_only
        project_settings.write_settings()
        signals.database_read_only_changed.emit(db, read_only)


    @ABTableWidget.decorated_sync
    def sync(self):
        self.setRowCount(len(bw.databases))
        self.setHorizontalHeaderLabels(self.HEADERS)
        # self.setHorizontalHeaderLabels(sorted(self.HEADERS.items(), key=lambda kv: kv[1]))

        databases_read_only_settings = project_settings.settings.get('read-only-databases', {})

        for row, name in enumerate(natural_sort(bw.databases)):
            self.setItem(row, self.HEADERS.index("Name"), ABTableItem(name, db_name=name))
            depends = bw.databases[name].get('depends', [])
            self.setItem(row, self.HEADERS.index("Depends"), ABTableItem(", ".join(depends), db_name=name))
            dt = bw.databases[name].get('modified', '')
            # code below is based on the assumption that bw uses utc timestamps
            tz = datetime.datetime.now(datetime.timezone.utc).astimezone()
            time_shift = - tz.utcoffset().total_seconds()
            if dt:
                dt = arrow.get(dt).shift(seconds=time_shift).humanize()
            self.setItem(row, self.HEADERS.index("Modified"), ABTableItem(dt, db_name=name))
            self.setItem(
                row, self.HEADERS.index("Records"), ABTableItem(str(len(bw.Database(name))), db_name=name)
            )
            # final column includes interactive checkbox which shows read-only state of db
            database_read_only = databases_read_only_settings.get(name, True)

            ch = QtWidgets.QCheckBox(parent=self)
            ch.clicked.connect(lambda checked, db=name: self.read_only_changed(checked, db))
            ch.setChecked(database_read_only)
            self.setCellWidget(row, self.HEADERS.index("Read-only"), ch)


class BiosphereFlowsTable(ABTableWidget):
    MAX_LENGTH = 100
    COLUMNS = {
        0: "name",
        2: "unit"
    }
    HEADERS = ["Name", "Categories", "Unit"]

    def __init__(self):
        super(BiosphereFlowsTable, self).__init__()
        self.database_name = None
        self.setDragEnabled(True)
        self.setColumnCount(len(self.HEADERS))
        self.connect_signals()

    def connect_signals(self):
        signals.database_selected.connect(self.sync)

    @ABTableWidget.decorated_sync
    def sync(self, name, data=None):
        self.database_name = name
        self.setHorizontalHeaderLabels(self.HEADERS)
        if not data:
            self.database = bw.Database(name)
            self.database.order_by = 'name'
            self.database.filters = {'type': 'emission'}
            self.setRowCount(min(len(self.database), self.MAX_LENGTH))
            data = itertools.islice(self.database, 0, self.MAX_LENGTH)
        for row, ds in enumerate(data):
            for col, value in self.COLUMNS.items():
                self.setItem(row, col, ABTableItem(ds.get(value, ''), key=ds.key, color=value))
            self.setItem(row, 1, ABTableItem(", ".join(ds.get('categories', [])), key=ds.key))

    def reset_search(self):
        self.sync(self.database.name)

    def search(self, search_term):
        search_result = self.database.search(search_term, limit=self.MAX_LENGTH)
        self.setRowCount(len(search_result))
        if search_result or search_term == '':
            self.sync(self.database.name, search_result)


class ActivitiesTable(ABTableWidget):
    MAX_LENGTH = 500
    COLUMNS = {
        0: "reference product",
        1: "name",
        2: "location",
        3: "unit",
        4: "key",
    }
    HEADERS = ["Product", "Activity", "Location", "Unit", "Key"]

    def __init__(self, parent=None):
        super(ActivitiesTable, self).__init__(parent)
        self.database_name = None
        self.setDragEnabled(True)
        self.setColumnCount(len(self.HEADERS))
        self.db_read_only = project_settings.settings.get('read-only-databases', {}).get(self.database_name, True)
        self.setup_context_menu()
        self.connect_signals()
        self.fuzzy_search_index = (None, None)

    def setup_context_menu(self):
        # context menu items are enabled/disabled elsewhere, in update_activity_table_read_only()
        self.open_activity_action = QtWidgets.QAction(
            QtGui.QIcon(icons.left), "Open activity", None)

        self.open_graph_action = QtWidgets.QAction(
            QtGui.QIcon(icons.graph_explorer), "Open in Graph Explorer", None)

        self.new_activity_action = QtWidgets.QAction(
            QtGui.QIcon(icons.add), "Add new activity", None
        )
        self.duplicate_activity_action = QtWidgets.QAction(
            QtGui.QIcon(icons.copy), "Duplicate activity", None
        )
        self.delete_activity_action = QtWidgets.QAction(
            QtGui.QIcon(icons.delete), "Delete activity", None
        )
        self.duplicate_activity_to_db_action = QtWidgets.QAction(
            QtGui.QIcon(icons.add_db), 'Duplicate to other database', None
        )

        self.addAction(self.open_activity_action)
        self.addAction(self.open_graph_action)
        self.addAction(self.new_activity_action)
        self.addAction(self.duplicate_activity_action)
        self.addAction(self.delete_activity_action)
        self.addAction(self.duplicate_activity_to_db_action)

        self.open_activity_action.triggered.connect(
            lambda x: signals.open_activity_tab.emit(self.currentItem().key)
        )
        self.open_graph_action.triggered.connect(
            lambda x: signals.open_activity_graph_tab.emit(self.currentItem().key)
        )
        self.new_activity_action.triggered.connect(
            lambda: signals.new_activity.emit(self.database.name)
        )
        self.duplicate_activity_action.triggered.connect(
            lambda x: signals.duplicate_activity.emit(self.currentItem().key)
        )
        self.delete_activity_action.triggered.connect(
            lambda x: signals.delete_activity.emit(self.currentItem().key)
        )
        self.duplicate_activity_to_db_action.triggered.connect(
            lambda: signals.show_duplicate_to_db_interface.emit(self.currentItem().key)
        )

    def update_activity_table_read_only(self, db, db_read_only):
        """[new, duplicate & delete] actions can only be selected for databases that are not read-only
                user can change state of dbs other than the open one: so check first"""
        if self.database_name == db:
            self.db_read_only = db_read_only
            self.new_activity_action.setEnabled(not self.db_read_only)
            self.duplicate_activity_action.setEnabled(not self.db_read_only)
            self.delete_activity_action.setEnabled(not self.db_read_only)

    def connect_signals(self):
        signals.database_selected.connect(
            lambda name, limit_width="ActivitiesTable": self.sync(name, limit_width=limit_width)
        )
        signals.database_changed.connect(self.filter_database_changed)
        signals.database_read_only_changed.connect(self.update_activity_table_read_only)

        self.itemDoubleClicked.connect(
            lambda x: signals.open_activity_tab.emit(x.key)
        )
        self.itemDoubleClicked.connect(
            lambda x: signals.add_activity_to_history.emit(x.key)
        )

    def update_search_index(self):
        if self.database is not self.fuzzy_search_index[0]:
            activity_data = [obj['data'] for obj in self.database._get_queryset().dicts()]
            name_activity_dict = collections.defaultdict(list)
            for act in activity_data:
                name_activity_dict[act['name']].append(self.database.get(act['code']))
            self.fuzzy_search_index = (self.database, name_activity_dict)

    @ABTableWidget.decorated_sync
    def sync(self, name, data=None, **kwargs):
        # fills activity table with data contained in selected database
        self.database_name = name
        if not data:
            self.database = bw.Database(name)
            self.database.order_by = 'name'
            self.database.filters = {'type': 'process'}
            data = itertools.islice(self.database, 0, self.MAX_LENGTH)
            self.setRowCount(min(len(self.database), self.MAX_LENGTH))
        self.setHorizontalHeaderLabels(self.HEADERS)
        for row, ds in enumerate(data):
            for col, value in self.COLUMNS.items():
                if value == "key":
                    self.setItem(row, col, ABTableItem(str(ds.key), key=ds.key, color=value))
                elif value == "location":
                    self.setItem(row, col, ABTableItem(str(ds.get(value, '')), key=ds.key, color=value))
                else:
                    self.setItem(row, col, ABTableItem(ds.get(value, ''), key=ds.key, color=value))

        self.db_read_only = project_settings.settings.get('read-only-databases', {}).get(self.database_name, True)
        self.update_activity_table_read_only(self.database_name, db_read_only=self.db_read_only)

    def filter_database_changed(self, database_name):
        if not hasattr(self, "database") or self.database.name != database_name:
            return
        self.sync(self.database.name)

    def reset_search(self):
        self.sync(self.database.name)

    def search(self, search_term):
        search_result = self.database.search(search_term, limit=self.MAX_LENGTH)
        self.setRowCount(len(search_result))
        if search_result or search_term == '':
            self.sync(self.database.name, search_result)

    def fuzzy_search(self, search_term):
        names = list(self.fuzzy_search_index[1].keys())
        fuzzy_search_result = process.extractBests(search_term, names, score_cutoff=10, limit=50)
        result = list(itertools.chain.from_iterable(
            [self.fuzzy_search_index[1][name] for name, score in fuzzy_search_result]
        ))
        self.setRowCount(len(result))
        if result or search_term == '':
            self.sync(self.database.name, result)


class ActivitiesBiosphereTable(ABDataFrameTable):
    def __init__(self):
        super(ActivitiesBiosphereTable, self).__init__()
        self.database_name = None
        self.technosphere = True
        self.act_fields = lambda: [f for f in ['reference product', 'name', 'location', 'unit'] if f in AB_metadata.dataframe.columns]
        self.ef_fields = lambda: [f for f in ['name', 'categories', 'type', 'unit'] if f in AB_metadata.dataframe.columns]
        self.fields = list()  # set during sync

        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.setDragEnabled(True)

        self.setup_context_menu()
        self.connect_signals()
        self.fuzzy_search_index = (None, None)

    def setup_context_menu(self):
        # context menu items are enabled/disabled elsewhere, in update_activity_table_read_only()
        self.open_activity_action = QtWidgets.QAction(
            QtGui.QIcon(icons.left), "Open activity", None)

        self.open_graph_action = QtWidgets.QAction(
            QtGui.QIcon(icons.graph_explorer), "Open in Graph Explorer", None)

        self.new_activity_action = QtWidgets.QAction(
            QtGui.QIcon(icons.add), "Add new activity", None
        )
        self.duplicate_activity_action = QtWidgets.QAction(
            QtGui.QIcon(icons.copy), "Duplicate activity", None
        )
        self.delete_activity_action = QtWidgets.QAction(
            QtGui.QIcon(icons.delete), "Delete activity", None
        )
        self.duplicate_activity_to_db_action = QtWidgets.QAction(
            QtGui.QIcon(icons.add_db), 'Duplicate to other database', None
        )

        self.actions = [
            self.open_activity_action,
            self.open_graph_action,
            self.new_activity_action,
            self.duplicate_activity_action,
            self.delete_activity_action,
            self.duplicate_activity_to_db_action,
        ]
        for action in self.actions:
            self.addAction(action)

        self.open_activity_action.triggered.connect(
            lambda x: self.item_double_clicked(self.currentIndex())
        )
        self.open_graph_action.triggered.connect(
            lambda x: signals.open_activity_graph_tab.emit(self.get_key(self.currentIndex()))
        )
        self.new_activity_action.triggered.connect(
            lambda: signals.new_activity.emit(self.database_name)
        )
        self.duplicate_activity_action.triggered.connect(
            lambda x: signals.duplicate_activity.emit(self.get_key(self.currentIndex()))
        )
        self.delete_activity_action.triggered.connect(
            lambda x: signals.delete_activity.emit(self.get_key(self.currentIndex()))
        )
        self.duplicate_activity_to_db_action.triggered.connect(
            lambda: signals.show_duplicate_to_db_interface.emit(self.get_key(self.currentIndex()))
        )

    def connect_signals(self):
        signals.database_selected.connect(
            lambda name, limit_width="ActivitiesTable": self.sync(name, limit_width=limit_width)
        )
        signals.database_changed.connect(self.filter_database_changed)
        signals.database_read_only_changed.connect(self.update_activity_table_read_only)

        self.doubleClicked.connect(self.item_double_clicked)

    def get_key(self, proxy_index):
        """Get the key from the mode.dataframe assuming the index provided refers to the proxy model."""
        index = self.get_source_index(proxy_index)
        return self.dataframe.iloc[index.row()]['key']

    def item_double_clicked(self, proxy_index):
        key = self.get_key(proxy_index)
        signals.open_activity_tab.emit(key)
        signals.add_activity_to_history.emit(key)

    @ABDataFrameTable.decorated_sync
    def sync(self, db_name):
        if db_name not in bw.databases:
            raise KeyError('This database does not exist!', db_name)
        self.database_name = db_name
        self.technosphere = is_technosphere_db(db_name)
        AB_metadata.add_metadata([db_name])  # adds metadata if not already available; needs to come before fields

        # disable context menu (actions) if biosphere table and/or if db read-only
        if self.technosphere:
            [action.setEnabled(True) for action in self.actions]
            self.db_read_only = project_settings.settings.get('read-only-databases', {}).get(db_name, True)
            self.update_activity_table_read_only(self.database_name, self.db_read_only)
        else:
            [action.setEnabled(False) for action in self.actions]

        # get fields
        fields = self.act_fields() if self.technosphere else self.ef_fields()
        self.fields = fields + ['key']
        print('*** Fields:', self.fields)

        # get dataframe
        df = AB_metadata.dataframe[AB_metadata.dataframe['database'] == db_name]
        df['key'] = [k for k in zip(df['database'], df['code'])]
        self.dataframe = df[self.fields].reset_index(drop=True)

        # sort ignoring case sensitivity
        self.dataframe = self.dataframe.iloc[self.dataframe["name"].str.lower().argsort()]
        self.dataframe.reset_index(inplace=True, drop=True)

    def update_activity_table_read_only(self, db_name, db_read_only):
        """[new, duplicate & delete] actions can only be selected for databases that are not read-only
                user can change state of dbs other than the open one: so check first"""
        if self.database_name == db_name:
            self.db_read_only = db_read_only
            self.new_activity_action.setEnabled(not self.db_read_only)
            self.duplicate_activity_action.setEnabled(not self.db_read_only)
            self.delete_activity_action.setEnabled(not self.db_read_only)

    def update_search_index(self):
        if self.database is not self.fuzzy_search_index[0]:
            activity_data = [obj['data'] for obj in self.database._get_queryset().dicts()]
            name_activity_dict = collections.defaultdict(list)
            for act in activity_data:
                name_activity_dict[act['name']].append(self.database.get(act['code']))
            self.fuzzy_search_index = (self.database, name_activity_dict)

    def filter_database_changed(self, database_name):
        if not hasattr(self, "database") or self.database.name != database_name:
            return
        self.sync(self.database.name)

    def reset_search(self):
        self.sync(self.database_name)

    def search(self, search_term):
        search_result = self.database.search(search_term, limit=self.MAX_LENGTH)
        self.setRowCount(len(search_result))
        if search_result or search_term == '':
            self.sync(self.database.name, search_result)

    def fuzzy_search(self, search_term):
        names = list(self.fuzzy_search_index[1].keys())
        fuzzy_search_result = process.extractBests(search_term, names, score_cutoff=10, limit=50)
        result = list(itertools.chain.from_iterable(
            [self.fuzzy_search_index[1][name] for name, score in fuzzy_search_result]
        ))
        self.setRowCount(len(result))
        if result or search_term == '':
            self.sync(self.database.name, result)