from typing import List

from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Slot

from activity_browser import actions
from ...settings import project_settings
from ...signals import signals
from ..icons import qicons
from .delegates import CheckboxDelegate
from .models import DatabasesModel, ActivitiesBiosphereModel
from .views import ABDataFrameView, ABFilterableDataFrameView


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

        self.relink_action = actions.DatabaseRelink.get_QAction(self.current_database)
        self.new_activity_action = actions.ActivityNew.get_QAction(self.current_database)
        self.delete_db_action = actions.DatabaseDelete.get_QAction(self.current_database)
        self.duplicate_db_action = actions.DatabaseDuplicate.get_QAction(self.current_database)

        self.model = DatabasesModel(parent=self)
        self._connect_signals()

    def _connect_signals(self):
        self.doubleClicked.connect(
            lambda p: signals.database_selected.emit(self.model.get_db_name(p))
        )
        self.model.updated.connect(self.update_proxy_model)

    def contextMenuEvent(self, event) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return

        menu = QtWidgets.QMenu(self)
        menu.addAction(self.delete_db_action)
        menu.addAction(self.relink_action)
        menu.addAction(self.duplicate_db_action)
        menu.addAction(self.new_activity_action)
        proxy = self.indexAt(event.pos())
        if proxy.isValid():
            db_name = self.model.get_db_name(proxy)
            self.relink_action.setEnabled(not project_settings.db_is_readonly(db_name))
            self.new_activity_action.setEnabled(not project_settings.db_is_readonly(db_name))
        menu.exec_(event.globalPos())

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
                self.model.sync()
        super().mousePressEvent(e)

    def current_database(self) -> str:
        """ Return the database name of the user-selected index.
        """
        return self.model.get_db_name(self.currentIndex())


class ActivitiesBiosphereTable(ABFilterableDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_read_only = True

        self.model = ActivitiesBiosphereModel(parent=self)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QTableView.DragOnly)
        self.setSelectionBehavior(self.SelectRows)

        # context-menu items
        self.open_activity_action = actions.ActivityOpen.get_QAction(self.selected_keys)
        self.open_activity_graph_action = actions.ActivityGraph.get_QAction(self.selected_keys)
        self.new_activity_action = actions.ActivityNew.get_QAction(self.current_database)
        self.dup_activity_action = actions.ActivityDuplicate.get_QAction(self.selected_keys)
        self.dup_activity_new_loc_action = actions.ActivityDuplicateToLoc.get_QAction(lambda: self.selected_keys()[0])
        self.delete_activity_action = actions.ActivityDelete.get_QAction(self.selected_keys)
        self.relink_activity_exch_action = actions.ActivityRelink.get_QAction(self.selected_keys)
        self.dup_other_db_action = actions.ActivityDuplicateToDB.get_QAction(self.selected_keys)
        self.copy_exchanges_for_SDF_action = QtWidgets.QAction(
            qicons.superstructure, 'Exchanges for scenario difference file', None
        )
        self.connect_signals()

    def current_database(self) -> str:
        return self.model.database_name

    @property
    def technosphere(self) -> bool:
        return self.model.technosphere

    def contextMenuEvent(self, event) -> None:
        """ Construct and present a menu.
        """
        if self.indexAt(event.pos()).row() == -1 and len(self.model._dataframe) != 0:
            return

        if len(self.selected_keys()) > 1:
            # more than 1 activity is selected
            act = 'activities'
            self.dup_activity_new_loc_action.setEnabled(False)
            self.relink_activity_exch_action.setEnabled(False)
        elif len(self.selected_keys()) == 1 and self.db_read_only:
            act = 'activity'
            self.dup_activity_new_loc_action.setEnabled(False)
            self.relink_activity_exch_action.setEnabled(False)
        else:
            act = 'activity'
            self.dup_activity_new_loc_action.setEnabled(True)
            self.relink_activity_exch_action.setEnabled(True)

        self.open_activity_action.setText(f'Open {act}')
        self.open_activity_graph_action.setText(f'Open {act} in Graph Explorer')
        self.dup_activity_action.setText(f'Duplicate {act}')
        self.delete_activity_action.setText(f'Delete {act}')

        menu = QtWidgets.QMenu()

        if len(self.model._dataframe) == 0:
            # if the database is empty, only add the 'new' activity option and return
            menu.addAction(self.new_activity_action)
            menu.exec_(event.globalPos())
            return

        # submenu duplicates
        submenu_dupl = QtWidgets.QMenu(menu)
        submenu_dupl.setTitle(f'Duplicate {act}')
        submenu_dupl.setIcon(qicons.copy)
        submenu_dupl.addAction(self.dup_activity_action)
        submenu_dupl.addAction(self.dup_activity_new_loc_action)
        submenu_dupl.addAction(self.dup_other_db_action)
        # submenu copy to clipboard
        submenu_copy = QtWidgets.QMenu(menu)
        submenu_copy.setTitle('Copy to clipboard')
        submenu_copy.setIcon(qicons.copy_to_clipboard)
        submenu_copy.addAction(self.copy_exchanges_for_SDF_action)

        menu.addAction(self.open_activity_action)
        menu.addAction(self.open_activity_graph_action)
        menu.addAction(self.new_activity_action)
        menu.addMenu(submenu_dupl)
        menu.addAction(self.delete_activity_action)
        menu.addAction(self.relink_activity_exch_action)
        menu.addMenu(submenu_copy)

        menu.exec_(event.globalPos())

    def connect_signals(self):
        signals.database_read_only_changed.connect(self.update_activity_table_read_only)

        self.copy_exchanges_for_SDF_action.triggered.connect(self.copy_exchanges_for_SDF)

        self.doubleClicked.connect(self.open_activity_action.trigger)

        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.set_context_menu_policy)
        self.model.updated.connect(self.update_filter_settings)

    def get_key(self, proxy: QtCore.QModelIndex) -> tuple:
        return self.model.get_key(proxy)

    def selected_keys(self) -> List[tuple]:
        return list(set([self.model.get_key(index) for index in self.selectedIndexes()]))

    def update_filter_settings(self) -> None:
        # Write the column indices so only those columns get filter button
        if isinstance(self.model.filterable_columns, dict):
            self.header.column_indices = list(self.model.filterable_columns.values())

    @Slot(name="copyFlowInformation")
    def copy_exchanges_for_SDF(self) -> None:
        self.model.copy_exchanges_for_SDF(self.selectedIndexes())

    def sync(self, db_name: str) -> None:
        self.model.sync(db_name)

    @Slot(name="updateMenuContext")
    def set_context_menu_policy(self) -> None:
        if self.model.technosphere:
            self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
            self.db_read_only = project_settings.db_is_readonly(self.current_database())
            self.update_activity_table_read_only(self.current_database(), self.db_read_only)
        else:
            self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

    def search(self, pattern1: str = None) -> None:
        self.model.search(pattern1)
        self.apply_filters()

    @Slot(name="resetSearch")
    def reset_search(self) -> None:
        self.model.sync(self.model.current_database)

    @Slot(str, bool, name="updateReadOnly")
    def update_activity_table_read_only(self, db_name: str, db_read_only: bool) -> None:
        """ [new, duplicate & delete] actions can only be selected for
        databases that are not read-only.

        The user can change state of dbs other than the open one, so check
        if database name matches.
        """
        if self.current_database() == db_name:
            self.db_read_only = db_read_only
            self.new_activity_action.setEnabled(not self.db_read_only)
            self.dup_activity_action.setEnabled(not self.db_read_only)
            self.delete_activity_action.setEnabled(not self.db_read_only)
            self.dup_activity_new_loc_action.setEnabled(not self.db_read_only)
            self.relink_activity_exch_action.setEnabled(not self.db_read_only)
