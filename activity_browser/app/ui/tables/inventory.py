# -*- coding: utf-8 -*-
import datetime
import arrow
import brightway2 as bw
from PyQt5 import QtGui, QtWidgets, QtCore
from bw2data.utils import natural_sort
import functools
import numpy as np
import pandas as pd

from activity_browser.app.settings import project_settings

from .delegates import CheckboxDelegate
from .views import ABDataFrameView, dataframe_sync
from ..icons import icons, qicons
from ...signals import signals
from ...bwutils.metadata import AB_metadata
from ...bwutils.commontasks import is_technosphere_db


class DatabasesTable(ABDataFrameView):
    """ Displays metadata for the databases found within the selected project.

    Databases can be read-only or writable, with users preference persisted
    in settings file.
    - User double-clicks to see the activities and flows within a db
    - A context menu (right click) provides further functionality
    """
    HEADERS = ["Name", "Records", "Read-only", "Depends", "Modified"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.verticalHeader().setVisible(False)
        self.setSelectionMode(ABDataFrameView.SingleSelection)
        self.setItemDelegateForColumn(2, CheckboxDelegate(self))
        self._connect_signals()

    def _connect_signals(self):
        signals.project_selected.connect(self.sync)
        signals.databases_changed.connect(self.sync)
        self.doubleClicked.connect(self.open_database)

    def contextMenuEvent(self, a0) -> None:
        menu = QtWidgets.QMenu(self)
        menu.addAction(
            qicons.delete, "Delete database",
            lambda: signals.delete_database.emit(self.selected_db_name)
        )
        menu.addAction(
            qicons.duplicate, "Copy database",
            lambda: signals.copy_database.emit(self.selected_db_name)
        )
        menu.addAction(
            qicons.add, "Add new activity",
            lambda: signals.new_activity.emit(self.selected_db_name)
        )
        menu.popup(QtGui.QCursor.pos())
        menu.exec()

    def mousePressEvent(self, e):
        """ A single mouseclick should trigger the 'read-only' column to alter
        its value.

        NOTE: This is kind of hacky as we are deliberately sidestepping
        the 'delegate' system that should handle this.
        If this is important in the future: call self.edit(index)
        (inspired by: https://stackoverflow.com/a/11778012)
        """
        if e.button() == QtCore.Qt.LeftButton:
            index = self.indexAt(e.pos())
            if index.column() == 2:
                value = self.dataframe.iloc[index.row(), index.column()]
                new_value = True if not value else False
                db_name = self.dataframe.iloc[index.row(), ]["Name"]
                self.read_only_changed(db_name, new_value)
                self.sync()
        super().mousePressEvent(e)

    @property
    def selected_db_name(self) -> str:
        """ Return the database name of the user-selected index.
        """
        index = self.get_source_index(next(p for p in self.selectedIndexes()))
        return self.dataframe.iloc[index.row(), ]["Name"]

    def open_database(self, proxy):
        index = self.get_source_index(proxy)
        signals.database_selected.emit(self.dataframe.iloc[index.row(), ]["Name"])

    @staticmethod
    @QtCore.pyqtSlot(str, bool)
    def read_only_changed(db: str, read_only: bool):
        """ User has clicked to update a db to either read-only or not.
        """
        project_settings.modify_db(db, read_only)
        signals.database_read_only_changed.emit(db, read_only)

    @dataframe_sync
    def sync(self):
        databases_read_only_settings = project_settings.settings.get("read-only-databases", {})
        # code below is based on the assumption that bw uses utc timestamps
        tz = datetime.datetime.now(datetime.timezone.utc).astimezone()
        time_shift = - tz.utcoffset().total_seconds()

        data = []
        for name in natural_sort(bw.databases):
            dt = bw.databases[name].get("modified", "")
            if dt:
                dt = arrow.get(dt).shift(seconds=time_shift).humanize()
            # final column includes interactive checkbox which shows read-only state of db
            database_read_only = databases_read_only_settings.get(name, True)
            data.append({
                "Name": name,
                "Depends": ", ".join(bw.databases[name].get("depends", [])),
                "Modified": dt,
                "Records": len(bw.Database(name)),
                "Read-only": database_read_only,
            })

        self.dataframe = pd.DataFrame(data, columns=self.HEADERS)

    def _resize(self):
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum)
        )

    def rowCount(self) -> int:
        return self.model.rowCount()


class ActivitiesBiosphereTable(ABDataFrameView):
    def __init__(self):
        super(ActivitiesBiosphereTable, self).__init__()
        self.database_name = None
        self.dataframe = pd.DataFrame()
        self.technosphere = True
        self.act_fields = lambda: AB_metadata.get_existing_fields(['reference product', 'name', 'location', 'unit'])
        self.ef_fields = lambda: AB_metadata.get_existing_fields(['name', 'categories', 'type', 'unit'])
        self.fields = list()  # set during sync

        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.setDragEnabled(True)
        self.drag_model = True  # to enable the DragPandasModel (with flags for dragging)
        self.setDragDropMode(1)  # QtGui.QAbstractItemView.DragOnly

        self.setup_context_menu()
        self.connect_signals()

    def setup_context_menu(self):
        # context menu items are enabled/disabled elsewhere, in update_activity_table_read_only()
        self.open_activity_action = QtWidgets.QAction(
            QtGui.QIcon(icons.left), "Open activity", None)

        self.open_graph_action = QtWidgets.QAction(
            QtGui.QIcon(icons.graph_explorer), "Open in Graph Explorer", None)

        # self.calculate_LCA = QtWidgets.QAction(
        #     QtGui.QIcon(icons.calculate), "calculate LCA", None)
        #
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
            # self.calculate_LCA,
            self.new_activity_action,
            self.duplicate_activity_action,
            self.delete_activity_action,
            self.duplicate_activity_to_db_action,
        ]
        for action in self.actions:
            self.addAction(action)

        # TODO: several of these actions could be done for several activities at
        #  the same time (e.g. deleting), which is currently not supported

        self.open_activity_action.triggered.connect(
            lambda x: self.item_double_clicked(self.currentIndex())
        )
        self.open_graph_action.triggered.connect(
            lambda x: signals.open_activity_graph_tab.emit(self.get_key(self.currentIndex()))
        )
        # self.calculate_LCA.triggered.connect(
        #     lambda x: self.LCA_calculation(self.get_key(self.currentIndex()))
        # )
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
            lambda name: self.sync(name)
        )
        # signals.database_changed.connect(self.filter_database_changed)
        signals.database_changed.connect(self.check_database_changed)
        signals.database_read_only_changed.connect(self.update_activity_table_read_only)

        self.doubleClicked.connect(self.item_double_clicked)

    def reset_table(self):
        self.database_name = None
        self.dataframe = pd.DataFrame()

    def get_key(self, proxy_index):
        """Get the key from the mode.dataframe assuming the index provided refers to the proxy model."""
        index = self.get_source_index(proxy_index)
        return self.dataframe.iloc[index.row()]['key']

    def item_double_clicked(self, proxy_index):
        key = self.get_key(proxy_index)
        signals.open_activity_tab.emit(key)
        signals.add_activity_to_history.emit(key)

    @QtCore.pyqtSlot(str)
    def check_database_changed(self, db_name: str) -> None:
        """ Determine if we need to re-sync (did 'our' db change?).
        """
        if db_name == self.database_name and db_name in bw.databases:
            self.sync(db_name)

    # def LCA_calculation(self, key):
    #     print(key)
    #     func_unit = {key: 1.0}
    #     for func_unit in bw.calculation_setups[name]['inv']:
    #         for key, amount in func_unit.items():
    #             self.append_row(key, str(amount))

    @dataframe_sync
    def sync(self, db_name, df=None):
        if isinstance(df, pd.DataFrame):  # skip the rest of the sync here if a dataframe is directly supplied
            print('Pandas Dataframe passed to sync.', df.shape)
            self.dataframe = df
            return

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

        # get dataframe
        df = AB_metadata.get_database_metadata(db_name)
        self.dataframe = df[self.fields].reset_index(drop=True)

        # sort ignoring case sensitivity
        sort_field = self.fields[0]
        self.dataframe = self.dataframe.iloc[self.dataframe[sort_field].str.lower().argsort()]
        sort_field_index = self.fields.index(sort_field)
        self.horizontalHeader().setSortIndicator(sort_field_index, QtCore.Qt.AscendingOrder)
        self.dataframe.reset_index(inplace=True, drop=True)
        self.dataframe_search_copy = self.dataframe

    def search(self, filter1=None, filter2=None, logic='AND'):
        """Filter the dataframe with two filters and a logical element in between
        to allow different filter combinations."""
        if not filter1 and not filter2:
            self.reset_search()
        if filter1 and filter2:
            # print('filtering on both search terms')
            mask1 = self.filter_dataframe(self.dataframe_search_copy, filter=filter1)
            mask2 = self.filter_dataframe(self.dataframe_search_copy, filter=filter2)
            # applying the logic
            if logic == 'AND':
                mask = np.logical_and(mask1, mask2)
            elif logic == 'OR':
                mask = np.logical_or(mask1, mask2)
            elif logic == 'AND NOT':
                mask = np.logical_and(mask1, ~mask2)
        else:
            # print('filtering on ONE search term')
            filter = filter1 if filter1 else filter2
            mask = self.filter_dataframe(self.dataframe_search_copy, filter=filter)
        df = self.dataframe_search_copy.loc[mask].reset_index(drop=True)
        self.sync(self.database_name, df=df)

    def filter_dataframe(self, df, filter=None):
        """
Filter a dataframe. Returns a mask that is True for all rows where a search string has been found.
It is a "contains" type of search (e.g. "oal" would find "coal").
It works also for columns that contain tuples (e.g. ('water', 'ocean'), but then only finds matches, i.e. 'ocean', but not 'ean'.
        """
        # ALTERNATIVE SOLUTIONS (FOR FUTURE REFERENCE)
        # df = df[df['name'].str.contains(filter)]  # simplest version (very quick)
        # search_columns = [str(c) for c in df.columns if c != 'key']
        # print('Searchin in the following columns:', df.columns)
        # mask = functools.reduce(np.logical_or, [df[col].str.contains(filter) for col in search_columns])
        mask = functools.reduce(np.logical_or,
                                [df[col].apply(lambda x: True if filter in x else False) for col in df.columns])
        return mask

    def reset_search(self):
        # could also set the self.dataframe_search_copy here (but would have to test a bit)
        self.sync(self.database_name)

    def update_activity_table_read_only(self, db_name, db_read_only):
        """[new, duplicate & delete] actions can only be selected for databases that are not read-only
                user can change state of dbs other than the open one: so check first"""
        if self.database_name == db_name:
            self.db_read_only = db_read_only
            self.new_activity_action.setEnabled(not self.db_read_only)
            self.duplicate_activity_action.setEnabled(not self.db_read_only)
            self.delete_activity_action.setEnabled(not self.db_read_only)


