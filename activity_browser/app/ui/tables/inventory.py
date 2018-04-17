# -*- coding: utf-8 -*-
import datetime
import collections
import itertools

from PyQt5 import QtCore, QtGui, QtWidgets
import arrow

import brightway2 as bw
from bw2data.utils import natural_sort
from fuzzywuzzy import process

from .table import ABTableWidget, ABTableItem
from ..icons import icons
from ...signals import signals


class DatabasesTable(ABTableWidget):
    HEADERS = ["Name", "Depends", "Last modified", "Size", "Read-only"]

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
        # add activity (important for empty databases, where the activities table will not show up)
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

    @ABTableWidget.decorated_sync
    def sync(self):
        self.setRowCount(len(bw.databases))
        self.setHorizontalHeaderLabels(self.HEADERS)
        for row, name in enumerate(natural_sort(bw.databases)):
            self.setItem(row, 0, ABTableItem(name, db_name=name))
            depends = bw.databases[name].get('depends', [])
            self.setItem(row, 1, ABTableItem(", ".join(depends), db_name=name))
            dt = bw.databases[name].get('modified', '')
            # code below is based on the assumption that bw uses utc timestamps
            tz = datetime.datetime.now(datetime.timezone.utc).astimezone()
            time_shift = - tz.utcoffset().total_seconds()
            if dt:
                dt = arrow.get(dt).shift(seconds=time_shift).humanize()
            self.setItem(row, 2, ABTableItem(dt, db_name=name))
            self.setItem(
                row, 3, ABTableItem(str(len(bw.Database(name))), db_name=name)
            )
            self.setItem(row, 4, ABTableItem(None, set_flags=[QtCore.Qt.ItemIsUserCheckable]))


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
        0: "name",
        1: "reference product",
        2: "location",
        3: "unit",
        4: "key",
    }
    HEADERS = ["Name", "Reference Product", "Location", "Unit", "Key"]

    def __init__(self, parent=None):
        super(ActivitiesTable, self).__init__(parent)
        self.database_name = None
        self.setDragEnabled(True)
        self.setColumnCount(len(self.HEADERS))
        self.setup_context_menu()
        self.connect_signals()
        self.fuzzy_search_index = (None, None)

    def setup_context_menu(self):
        self.add_activity_action = QtWidgets.QAction(
            QtGui.QIcon(icons.add), "Add new activity", None
        )
        self.copy_activity_action = QtWidgets.QAction(
            QtGui.QIcon(icons.copy), "Copy activity", None
        )
        self.delete_activity_action = QtWidgets.QAction(
            QtGui.QIcon(icons.delete), "Delete activity", None
        )
        self.open_left_tab_action = QtWidgets.QAction(
            QtGui.QIcon(icons.left), "Open in new tab", None
        )
        self.copy_to_db_action = QtWidgets.QAction(
            QtGui.QIcon(icons.add_db), 'Copy to database', None
        )
        self.addAction(self.add_activity_action)
        self.addAction(self.copy_activity_action)
        self.addAction(self.delete_activity_action)
        self.addAction(self.open_left_tab_action)
        self.addAction(self.copy_to_db_action)
        self.add_activity_action.triggered.connect(
            lambda: signals.new_activity.emit(self.database.name)
        )
        self.copy_activity_action.triggered.connect(
            lambda x: signals.copy_activity.emit(self.currentItem().key)
        )
        self.delete_activity_action.triggered.connect(
            lambda x: signals.delete_activity.emit(self.currentItem().key)
        )
        self.open_left_tab_action.triggered.connect(
            lambda x: signals.open_activity_tab.emit("activities", self.currentItem().key)
        )
        self.copy_to_db_action.triggered.connect(
            lambda: signals.copy_to_db.emit(self.currentItem().key)
        )

    def connect_signals(self):
        signals.database_selected.connect(self.sync)
        signals.database_changed.connect(self.filter_database_changed)

        self.itemDoubleClicked.connect(
            lambda x: signals.open_activity_tab.emit("activities", x.key)
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
    def sync(self, name, data=None):
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
                self.setItem(row, col, ABTableItem(ds.get(value, ''), key=ds.key, color=value))
                if value == "key":
                    self.setItem(row, col, ABTableItem(str(ds.key), key=ds.key, color=value))

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
