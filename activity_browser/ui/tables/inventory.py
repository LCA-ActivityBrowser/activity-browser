# -*- coding: utf-8 -*-
import brightway2 as bw
from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Slot

from ...settings import project_settings
from ...signals import signals
from ..icons import qicons
from .delegates import CheckboxDelegate
from .models import DatabasesModel, ActivitiesBiosphereModel
from .views import ABDataFrameView


class DatabasesTable(ABDataFrameView):
    """ Displays metadata for the databases found within the selected project.

    Databases can be read-only or writable, with users preference persisted
    in settings file.
    - User double-clicks to see the activities and flows within a db
    - A context menu (right click) provides further functionality
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.verticalHeader().setVisible(False)
        self.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.setItemDelegateForColumn(2, CheckboxDelegate(self))
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum
        ))
        self.relink_action = QtWidgets.QAction(
            qicons.edit, "Relink database", None
        )
        self.model = DatabasesModel(parent=self)
        self._connect_signals()

    def _connect_signals(self):
        signals.project_selected.connect(self.sync)
        signals.databases_changed.connect(self.sync)
        self.doubleClicked.connect(
            lambda p: signals.database_selected.emit(self.model.get_db_name(p))
        )
        self.relink_action.triggered.connect(
            lambda: signals.relink_database.emit(self.selected_db_name, self)
        )

    def contextMenuEvent(self, a0) -> None:
        menu = QtWidgets.QMenu(self)
        menu.addAction(
            qicons.delete, "Delete database",
            lambda: signals.delete_database.emit(self.selected_db_name)
        )
        menu.addAction(self.relink_action)
        menu.addAction(
            qicons.duplicate_database, "Copy database",
            lambda: signals.copy_database.emit(self.selected_db_name, self)
        )
        menu.addAction(
            qicons.add, "Add new activity",
            lambda: signals.new_activity.emit(self.selected_db_name)
        )
        proxy = self.indexAt(a0.pos())
        if proxy.isValid():
            db_name = self.model.get_db_name(proxy)
            self.relink_action.setEnabled(not project_settings.db_is_readonly(db_name))
        menu.exec_(a0.globalPos())

    def mousePressEvent(self, e):
        """ A single mouseclick should trigger the 'read-only' column to alter
        its value.

        NOTE: This is kind of hacky as we are deliberately sidestepping
        the 'delegate' system that should handle this.
        If this is important in the future: call self.edit(index)
        (inspired by: https://stackoverflow.com/a/11778012)
        """
        if e.button() == QtCore.Qt.LeftButton:
            proxy = self.indexAt(e.pos())
            if proxy.column() == 2:
                # Flip the read-only value for the database
                new_value = not bool(proxy.data())
                db_name = self.model.get_db_name(proxy)
                project_settings.modify_db(db_name, new_value)
                signals.database_read_only_changed.emit(db_name, new_value)
                self.sync()
        super().mousePressEvent(e)

    @property
    def selected_db_name(self) -> str:
        """ Return the database name of the user-selected index.
        """
        return self.model.get_db_name(self.currentIndex())

    def sync(self):
        # code below is based on the assumption that bw uses utc timestamps
        self.model.sync()
        self._resize()


class ActivitiesBiosphereTable(ABDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.database_name = None
        self.db_read_only = True

        self.model = ActivitiesBiosphereModel(parent=self)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QTableView.DragOnly)

        self.new_activity_action = QtWidgets.QAction(
            qicons.add, "Add new activity", None
        )
        self.duplicate_activity_action = QtWidgets.QAction(
            qicons.copy, "Duplicate activity/-ies", None
        )
        self.delete_activity_action = QtWidgets.QAction(
            qicons.delete, "Delete activity/-ies", None
        )

        self.connect_signals()

    @property
    def technosphere(self) -> bool:
        return self.model.technosphere

    def contextMenuEvent(self, event) -> None:
        """ Construct and present a menu.
        """
        menu = QtWidgets.QMenu()
        menu.addAction(qicons.right, "Open activity", self.open_activity_tabs)
        menu.addAction(
            qicons.graph_explorer, "Open in Graph Explorer",
            lambda: signals.open_activity_graph_tab.emit(
                self.model.get_key(self.currentIndex())
            )
        )
        menu.addAction(self.new_activity_action)
        menu.addAction(self.duplicate_activity_action)
        menu.addAction(self.delete_activity_action)
        menu.addAction(
            qicons.duplicate_to_other_database, "Duplicate to other database",
            self.duplicate_activities_to_db
        )
        menu.exec_(event.globalPos())

    def connect_signals(self):
        signals.database_selected.connect(
            lambda name: self.sync(name)
        )
        signals.database_changed.connect(self.check_database_changed)
        signals.database_read_only_changed.connect(self.update_activity_table_read_only)

        self.new_activity_action.triggered.connect(
            lambda: signals.new_activity.emit(self.database_name)
        )
        self.duplicate_activity_action.triggered.connect(self.duplicate_activities)
        self.delete_activity_action.triggered.connect(self.delete_activities)
        self.doubleClicked.connect(self.open_activity_tab)

    def get_key(self, proxy: QtCore.QModelIndex) -> tuple:
        """ TEMP function."""
        print("CALLED!")
        return self.model.get_key(proxy)

    @Slot(QtCore.QModelIndex, name="openActivityTab")
    def open_activity_tab(self, proxy: QtCore.QModelIndex) -> None:
        key = self.model.get_key(proxy)
        signals.open_activity_tab.emit(key)
        signals.add_activity_to_history.emit(key)

    @Slot(name="openActivityTabs")
    def open_activity_tabs(self) -> None:
        for key in (self.model.get_key(p) for p in self.selectedIndexes()):
            signals.open_activity_tab.emit(key)
            signals.add_activity_to_history.emit(key)

    @Slot(name="deleteActivities")
    def delete_activities(self) -> None:
        if len(self.selectedIndexes()) > 1:
            keys = [self.model.get_key(p) for p in self.selectedIndexes()]
            signals.delete_activities.emit(keys)
        else:
            signals.delete_activity.emit(self.model.get_key(self.currentIndex()))

    @Slot(name="duplicateActivitiesWithinDb")
    def duplicate_activities(self) -> None:
        if len(self.selectedIndexes()) > 1:
            keys = [self.model.get_key(p) for p in self.selectedIndexes()]
            signals.duplicate_activities.emit(keys)
        else:
            signals.duplicate_activity.emit(self.model.get_key(self.currentIndex()))

    @Slot(str)
    def check_database_changed(self, db_name: str) -> None:
        """ Determine if we need to re-sync (did 'our' db change?).
        """
        if db_name == self.database_name and db_name in bw.databases:
            self.sync(db_name)

    @Slot(name="duplicateActivitiesToOtherDb")
    def duplicate_activities_to_db(self) -> None:
        if len(self.selectedIndexes()) > 1:
            keys = [self.model.get_key(p) for p in self.selectedIndexes()]
            signals.duplicate_to_db_interface_multiple.emit(keys, self.database_name)
        else:
            key = self.model.get_key(self.currentIndex())
            signals.duplicate_to_db_interface.emit(key, self.database_name)

    def sync(self, db_name: str) -> None:
        self.database_name = db_name
        self.model.sync(db_name)
        self._resize()
        self.set_context_menu_policy()

    def set_context_menu_policy(self) -> None:
        if self.model.technosphere:
            self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
            self.db_read_only = project_settings.db_is_readonly(self.database_name)
            self.update_activity_table_read_only(self.database_name, self.db_read_only)
        else:
            self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

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
