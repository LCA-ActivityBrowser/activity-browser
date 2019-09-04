# -*- coding: utf-8 -*-
import datetime
import arrow
import brightway2 as bw
from PyQt5 import QtWidgets, QtCore
from bw2data.utils import natural_sort
import functools
import numpy as np
import pandas as pd

from activity_browser.app.settings import project_settings

from .delegates import CheckboxDelegate
from .views import ABDataFrameView, dataframe_sync
from ..icons import qicons
from ...signals import signals
from ...bwutils import AB_metadata
from ...bwutils.commontasks import bw_keys_to_AB_names, is_technosphere_db


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
        self.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        # TODO: Figure out problems with MacOS painting CheckboxDelegate incorrectly.
        # See https://github.com/LCA-ActivityBrowser/activity-browser/issues/278
        # self.setItemDelegateForColumn(2, CheckboxDelegate(self))
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum
        ))
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
        menu.exec(a0.globalPos())

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
                # Flip the read-only value for the database
                new_value = not bool(index.data())
                db_name = self.model.index(index.row(), 0).data()
                self.read_only_changed(db_name, new_value)
                self.sync()
        super().mousePressEvent(e)

    @property
    def selected_db_name(self) -> str:
        """ Return the database name of the user-selected index.
        """
        index = self.get_source_index(self.currentIndex())
        return self.model.index(index.row(), 0).data()

    def open_database(self, proxy):
        index = self.get_source_index(proxy)
        signals.database_selected.emit(self.model.index(index.row(), 0).data())

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


class ActivitiesBiosphereTable(ABDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.database_name = None
        self.technosphere = True
        self.act_fields = lambda: AB_metadata.get_existing_fields(['reference product', 'name', 'location', 'unit'])
        self.ef_fields = lambda: AB_metadata.get_existing_fields(['name', 'categories', 'type', 'unit'])
        self.fields = list()  # set during sync
        self.db_read_only = True

        self.setDragEnabled(True)
        self.drag_model = True  # to enable the DragPandasModel (with flags for dragging)
        self.setDragDropMode(QtWidgets.QTableView.DragOnly)

        self.new_activity_action = QtWidgets.QAction(
            qicons.add, "Add new activity", None
        )
        self.duplicate_activity_action = QtWidgets.QAction(
            qicons.copy, "Duplicate activity", None
        )
        self.delete_activity_action = QtWidgets.QAction(
            qicons.delete, "Delete activity", None
        )

        self.connect_signals()

    def contextMenuEvent(self, event) -> None:
        """ Construct and present a menu.
        """
        menu = QtWidgets.QMenu()
        menu.addAction(
            qicons.left, "Open activity",
            lambda: self.open_activity_tab(self.currentIndex())
        )
        menu.addAction(
            qicons.graph_explorer, "Open in Graph Explorer",
            lambda: signals.open_activity_graph_tab.emit(self.get_key(self.currentIndex()))
        )
        menu.addAction(self.new_activity_action)
        menu.addAction(self.duplicate_activity_action)
        menu.addAction(self.delete_activity_action)
        menu.addAction(
            qicons.add_db, "Duplicate to other database",
            lambda: signals.show_duplicate_to_db_interface.emit(self.get_key(self.currentIndex()))
        )
        menu.exec(event.globalPos())

    def connect_signals(self):
        signals.database_selected.connect(
            lambda name: self.sync(name)
        )
        signals.database_changed.connect(self.check_database_changed)
        signals.database_read_only_changed.connect(self.update_activity_table_read_only)

        self.new_activity_action.triggered.connect(
            lambda: signals.new_activity.emit(self.database_name)
        )
        self.duplicate_activity_action.triggered.connect(
            lambda: signals.duplicate_activity.emit(self.get_key(self.currentIndex()))
        )
        self.delete_activity_action.triggered.connect(
            lambda: signals.delete_activity.emit(self.get_key(self.currentIndex()))
        )
        self.doubleClicked.connect(self.open_activity_tab)

    def reset_table(self) -> None:
        self.database_name = None
        self.dataframe = pd.DataFrame()

    def get_key(self, proxy_index):
        """Get the key from the mode.dataframe assuming the index provided refers to the proxy model."""
        index = self.get_source_index(proxy_index)
        return self.dataframe.iloc[index.row()]['key']

    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def open_activity_tab(self, proxy: QtCore.QModelIndex) -> None:
        key = self.get_key(proxy)
        signals.open_activity_tab.emit(key)
        signals.add_activity_to_history.emit(key)

    @QtCore.pyqtSlot(str)
    def check_database_changed(self, db_name: str) -> None:
        """ Determine if we need to re-sync (did 'our' db change?).
        """
        if db_name == self.database_name and db_name in bw.databases:
            self.sync(db_name)

    @dataframe_sync
    def sync(self, db_name: str, df: pd.DataFrame=None) -> None:
        if df is not None:
            # skip the rest of the sync here if a dataframe is directly supplied
            print('Pandas Dataframe passed to sync.', df.shape)
            self.dataframe = df
            return

        if db_name not in bw.databases:
            raise KeyError('This database does not exist!', db_name)
        self.database_name = db_name
        self.technosphere = is_technosphere_db(db_name)

        # disable context menu (actions) if biosphere table and/or if db read-only
        if self.technosphere:
            self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
            self.db_read_only = project_settings.settings.get('read-only-databases', {}).get(db_name, True)
            self.update_activity_table_read_only(self.database_name, self.db_read_only)
        else:
            self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

        # get fields
        fields = self.act_fields() if self.technosphere else self.ef_fields()
        self.fields = [bw_keys_to_AB_names.get(c, c) for c in fields] + ["key"]

        # Get dataframe from metadata and update column-names
        df = AB_metadata.get_database_metadata(db_name)[fields + ["key"]]
        df.columns = self.fields
        self.dataframe = df.reset_index(drop=True)

        # Sort dataframe on first column (activity name, usually)
        # while ignoring case sensitivity
        sort_field = self.fields[0]
        self.dataframe = self.dataframe.iloc[self.dataframe[sort_field].str.lower().argsort()]
        sort_field_index = self.fields.index(sort_field)
        self.horizontalHeader().setSortIndicator(sort_field_index, QtCore.Qt.AscendingOrder)
        self.dataframe.reset_index(inplace=True, drop=True)

    def search(self, pattern1: str=None, pattern2: str=None, logic='AND') -> None:
        """ Filter the dataframe with two filters and a logical element
        in between to allow different filter combinations.

        TODO: Look at the possibility of using the proxy model to filter instead
        """
        if not pattern1 and not pattern2:
            self.reset_search()
        if pattern1 and pattern2:
            # print('filtering on both search terms')
            mask1 = self.filter_dataframe(self.dataframe, pattern1)
            mask2 = self.filter_dataframe(self.dataframe, pattern2)
            # applying the logic
            if logic == 'AND':
                mask = np.logical_and(mask1, mask2)
            elif logic == 'OR':
                mask = np.logical_or(mask1, mask2)
            elif logic == 'AND NOT':
                mask = np.logical_and(mask1, ~mask2)
        else:
            # print('filtering on ONE search term')
            pattern = pattern1 if pattern1 else pattern2
            mask = self.filter_dataframe(self.dataframe, pattern)
        df = self.dataframe.loc[mask].reset_index(drop=True)
        self.sync(self.database_name, df=df)

    def filter_dataframe(self, df: pd.DataFrame, pattern: str) -> pd.Series:
        """ Filter the dataframe returning a mask that is True for all rows
        where a search string has been found.

        It is a "contains" type of search (e.g. "oal" would find "coal").
        It also works for columns that contain tuples (e.g. ('water', 'ocean'),
        and will match on partials i.e. both 'ocean' and 'ean' work.

        An alternative solution would be to use .str.contains, but this does
        not work for columns containing tuples (https://stackoverflow.com/a/29463757)
        """
        search_columns = self.act_fields() if self.technosphere else self.ef_fields()
        search_columns = [bw_keys_to_AB_names.get(c, c) for c in search_columns]
        mask = functools.reduce(
            np.logical_or, [
                df[col].apply(lambda x: pattern.lower() in str(x).lower())
                for col in search_columns
            ]
        )
        return mask

    def reset_search(self) -> None:
        """ Explicitly reload the model data from the metadata.
        """
        self.sync(self.database_name)

    def update_activity_table_read_only(self, db_name: str, db_read_only: bool) -> None:
        """ [new, duplicate & delete] actions can only be selected for
        databases that are not read-only.

        The user can change state of dbs other than the open one, so check
        if database name matches.
        """
        if self.database_name == db_name:
            self.db_read_only = db_read_only
            self.new_activity_action.setEnabled(not self.db_read_only)
            self.duplicate_activity_action.setEnabled(not self.db_read_only)
            self.delete_activity_action.setEnabled(not self.db_read_only)


