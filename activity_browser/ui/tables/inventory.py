from typing import List

from PySide2 import QtCore, QtWidgets
from PySide2.QtCore import Slot
from multifunctional import allocation_strategies, list_available_properties

from activity_browser import actions
from activity_browser.mod.bw2data import databases
from activity_browser.ui.tables.delegates.combobox import ComboBoxDelegate
from activity_browser.ui.tables.delegates.text_button import TextButtonDelegate
from activity_browser.ui.widgets.custom_allocation_editor import CustomAllocationEditor

from ...settings import project_settings
from ...signals import signals
from ..icons import qicons
from .delegates import CheckboxDelegate
from .models import ActivitiesBiosphereModel, DatabasesModel
from .views import ABDataFrameView, ABFilterableDataFrameView


class DatabasesTable(ABDataFrameView):
    """Displays metadata for the databases found within the selected project.

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
        # Use a callable for the delegate, so that every newly created combobox
        # uses an up-to-date value
        def allocation_options() -> list[str]:
            options = list(allocation_strategies.keys())
            evaluated_properties = list_available_properties(self.current_database())
            properties_dict = {item[0]:item[1] for item in evaluated_properties}
            # Color the combo entries according to their status
            for i in range(len(options)):
                if options[i] in properties_dict:
                    brush = CustomAllocationEditor.brush_for_message_type(
                        properties_dict[options[i]]
                    )
                    options[i] = (options[i], options[i], brush)

            # Make the unspecified value the first in the list of options
            options.insert(0, DatabasesModel.UNSPECIFIED_ALLOCATION)
            options.append(DatabasesModel.CUSTOM_ALLOCATION)
            return options

        combo_delegate = ComboBoxDelegate(allocation_options, self)
        combo_delegate.set_early_commit_item(DatabasesModel.CUSTOM_ALLOCATION)

        def db_allocation() -> str:
            allocation = databases[self.current_database()].get("default_allocation")
            if allocation is None:
                allocation = DatabasesModel.UNSPECIFIED_ALLOCATION
            return allocation

        button_delegate = TextButtonDelegate(db_allocation)
        # self.setItemDelegateForColumn(4, combo_delegate)
        self.setItemDelegateForColumn(4, button_delegate)
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked |
            QtWidgets.QAbstractItemView.EditTrigger.SelectedClicked
        )

        self.relink_action = actions.DatabaseRelink.get_QAction(self.current_database)
        self.new_activity_action = actions.ActivityNew.get_QAction(
            self.current_database
        )
        self.delete_db_action = actions.DatabaseDelete.get_QAction(
            self.current_database
        )
        self.duplicate_db_action = actions.DatabaseDuplicate.get_QAction(
            self.current_database
        )
        self.re_allocate_action = actions.DatabaseRedoAllocation.get_QAction(
            self.current_database
        )

        self.model = DatabasesModel(parent=self)
        button_delegate.clicked.connect(self.model.show_custom_allocation_editor)
        self.update_proxy_model()
        # Set up an initial sort on the table
        # This is kept and applied even after the model is reset.
        # Without this the list of databases does not match the sorting
        # of the table and the first click on the header does nothing
        self.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)
        self._connect_signals()

    def _connect_signals(self):
        self.doubleClicked.connect(self._handle_double_click)
        self.model.modelReset.connect(self._handle_model_reset)

    def _handle_model_reset(self):
        for i in range(self.proxy_model.rowCount()):
            index = self.proxy_model.index(i, 4)
            if index.flags() & QtCore.Qt.ItemIsEditable:
                self.openPersistentEditor(index)

    def contextMenuEvent(self, event) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return

        menu = QtWidgets.QMenu(self)
        menu.addAction(self.delete_db_action)
        menu.addAction(self.relink_action)
        menu.addAction(self.duplicate_db_action)
        menu.addAction(self.new_activity_action)
        if databases[self.current_database()].get("backend") == "multifunctional":
            menu.addAction(self.re_allocate_action)
        proxy = self.indexAt(event.pos())
        if proxy.isValid():
            db_name = self.model.get_db_name(proxy)
            db_read_only = project_settings.db_is_readonly(db_name)
            self.relink_action.setEnabled(not db_read_only)
            self.re_allocate_action.setEnabled(not db_read_only)
            self.new_activity_action.setEnabled(not db_read_only)
        menu.exec_(event.globalPos())

    def mousePressEvent(self, e):
        """A single mouseclick should trigger the 'read-only' column to alter
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
                self.proxy_model.setData(proxy, new_value)

        super().mousePressEvent(e)

    def _handle_double_click(self, index: QtCore.QModelIndex):
        # No double click on the checkboxes
        if index.isValid() and index.column() != 2:
            # No double click on editable default allocation column,
            # because this should open the item editor
            read_only_idx = self.proxy_model.index(index.row(), 2)
            rd_only = self.proxy_model.data(read_only_idx)

            def_alloc_idx = self.proxy_model.index(index.row(), 4)
            def_alloc_editable = bool(
                self.proxy_model.flags(def_alloc_idx) & QtCore.Qt.ItemIsEditable
            )

            if index.column() != 4 or not def_alloc_editable:
                signals.database_selected.emit(self.model.get_db_name(index))

    def current_database(self) -> str:
        """Return the database name of the user-selected index."""
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
        self.open_activity_graph_action = actions.ActivityGraph.get_QAction(
            self.selected_keys
        )
        self.new_activity_action = actions.ActivityNew.get_QAction(
            self.current_database
        )
        self.dup_activity_action = actions.ActivityDuplicate.get_QAction(
            self.selected_keys
        )
        self.dup_activity_new_loc_action = actions.ActivityDuplicateToLoc.get_QAction(
            lambda: self.selected_keys()[0]
        )
        self.delete_activity_action = actions.ActivityDelete.get_QAction(
            self.selected_keys
        )
        self.relink_activity_exch_action = actions.ActivityRelink.get_QAction(
            self.selected_keys
        )
        self.dup_other_db_action = actions.ActivityDuplicateToDB.get_QAction(
            self.selected_keys
        )
        self.copy_exchanges_for_SDF_action = QtWidgets.QAction(
            qicons.superstructure, "Exchanges for scenario difference file", None
        )
        self.connect_signals()

    def current_database(self) -> str:
        return self.model.database_name

    @property
    def technosphere(self) -> bool:
        return self.model.technosphere

    def contextMenuEvent(self, event) -> None:
        """Construct and present a menu."""
        if self.indexAt(event.pos()).row() == -1 and len(self.model._dataframe) != 0:
            return

        if len(self.selected_keys()) > 1:
            # more than 1 activity is selected
            act = "activities"
            self.dup_activity_new_loc_action.setEnabled(False)
            self.relink_activity_exch_action.setEnabled(False)
        elif len(self.selected_keys()) == 1 and self.db_read_only:
            act = "activity"
            self.dup_activity_new_loc_action.setEnabled(False)
            self.relink_activity_exch_action.setEnabled(False)
        else:
            act = "activity"
            self.dup_activity_new_loc_action.setEnabled(True)
            self.relink_activity_exch_action.setEnabled(True)

        self.open_activity_action.setText(f"Open {act}")
        self.open_activity_graph_action.setText(f"Open {act} in Graph Explorer")
        self.dup_activity_action.setText(f"Duplicate {act}")
        self.delete_activity_action.setText(f"Delete {act}")

        menu = QtWidgets.QMenu()

        if len(self.model._dataframe) == 0:
            # if the database is empty, only add the 'new' activity option and return
            menu.addAction(self.new_activity_action)
            menu.exec_(event.globalPos())
            return

        # submenu duplicates
        submenu_dupl = QtWidgets.QMenu(menu)
        submenu_dupl.setTitle(f"Duplicate {act}")
        submenu_dupl.setIcon(qicons.copy)
        submenu_dupl.addAction(self.dup_activity_action)
        submenu_dupl.addAction(self.dup_activity_new_loc_action)
        submenu_dupl.addAction(self.dup_other_db_action)
        # submenu copy to clipboard
        submenu_copy = QtWidgets.QMenu(menu)
        submenu_copy.setTitle("Copy to clipboard")
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

        self.copy_exchanges_for_SDF_action.triggered.connect(
            self.copy_exchanges_for_SDF
        )

        self.doubleClicked.connect(self.open_activity_action.trigger)

        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.set_context_menu_policy)
        self.model.updated.connect(self.update_filter_settings)

    def get_key(self, proxy: QtCore.QModelIndex) -> tuple:
        return self.model.get_key(proxy)

    def selected_keys(self) -> List[tuple]:
        return list(
            set([self.model.get_key(index) for index in self.selectedIndexes()])
        )

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
            self.update_activity_table_read_only(
                self.current_database(), self.db_read_only
            )
        else:
            self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

    def search(self, pattern1: str = None) -> None:
        self.model.search(pattern1)
        self.apply_filters()

    @Slot(name="resetSearch")
    def reset_search(self) -> None:
        self.model.sync(self.current_database())
        self.apply_filters()

    @Slot(str, bool, name="updateReadOnly")
    def update_activity_table_read_only(self, db_name: str, db_read_only: bool) -> None:
        """[new, duplicate & delete] actions can only be selected for
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
