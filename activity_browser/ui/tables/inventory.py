# -*- coding: utf-8 -*-
from typing import Iterable

from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Slot, QModelIndex

from ...bwutils import AB_metadata
from ...settings import project_settings
from ...signals import signals
from ..icons import qicons
from .delegates import CheckboxDelegate
from .models import DatabasesModel, ActivitiesBiosphereListModel, ActivitiesBiosphereTreeModel
from .views import ABDictTreeView, ABDataFrameView, ABFilterableDataFrameView


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
            qicons.edit, "Relink the database", None
        )
        self.new_activity_action =QtWidgets.QAction(
            qicons.add, "Add new activity", None
        )
        self.model = DatabasesModel(parent=self)
        self._connect_signals()

    def _connect_signals(self):
        self.doubleClicked.connect(
            lambda p: signals.database_selected.emit(self.model.get_db_name(p))
        )
        self.relink_action.triggered.connect(
            lambda: signals.relink_database.emit(self.selected_db_name)
        )
        self.new_activity_action.triggered.connect(
            lambda: signals.new_activity.emit(self.selected_db_name)
        )
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)

    def contextMenuEvent(self, event) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return

        menu = QtWidgets.QMenu(self)
        menu.addAction(
            qicons.delete, "Delete database",
            lambda: signals.delete_database.emit(self.selected_db_name)
        )
        menu.addAction(self.relink_action)
        menu.addAction(
            qicons.duplicate_database, "Copy database",
            lambda: signals.copy_database.emit(self.selected_db_name)
        )
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

    @property
    def selected_db_name(self) -> str:
        """ Return the database name of the user-selected index.
        """
        return self.model.get_db_name(self.currentIndex())


class ActivitiesBiosphereTable(ABFilterableDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_read_only = True

        self.model = ActivitiesBiosphereListModel(parent=self)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QTableView.DragOnly)

        self.new_activity_action = QtWidgets.QAction(
            qicons.add, "Add new activity", None
        )
        self.duplicate_activity_action = QtWidgets.QAction(
            qicons.copy, "Duplicate activity/-ies", None
        )
        self.duplicate_activity_new_loc_action = QtWidgets.QAction(
            qicons.copy, "Duplicate activity to new location", None
        )
        self.duplicate_activity_new_loc_action.setToolTip(
            "Duplicate this activity to another location.\n"
            "Link the exchanges to a new location if it is availabe.")  # only for 1 activity
        self.delete_activity_action = QtWidgets.QAction(
            qicons.delete, "Delete activity/-ies", None
        )
        self.copy_exchanges_for_SDF_action = QtWidgets.QAction(
            qicons.superstructure, "Exchanges for scenario difference file", None
        )
        self.connect_signals()

    @property
    def database_name(self) -> str:
        return self.model.database_name

    @property
    def technosphere(self) -> bool:
        return self.model.technosphere

    def contextMenuEvent(self, event) -> None:
        """ Construct and present a menu.
        """
        if self.indexAt(event.pos()).row() == -1 and len(self.model._dataframe) != 0:
            return

        if len(self.selectedIndexes()) > 1:
            act = 'activities'
            self.duplicate_activity_new_loc_action.setEnabled(False)
        elif len(self.selectedIndexes()) == 1 and self.db_read_only:
            act = 'activity'
            self.duplicate_activity_new_loc_action.setEnabled(False)
        else:
            act = 'activity'
            self.duplicate_activity_new_loc_action.setEnabled(True)

        self.duplicate_activity_action.setText("Duplicate {}".format(act))
        self.delete_activity_action.setText("Delete {}".format(act))

        menu = QtWidgets.QMenu()
        if len(self.model._dataframe) == 0:
            # if the database is empty, only add the 'new' activity option and return
            menu.addAction(self.new_activity_action)
            menu.exec_(event.globalPos())
            return

        menu.addAction(qicons.right, "Open activity", self.open_activity_tabs)
        menu.addAction(
            qicons.graph_explorer, "Open in Graph Explorer",
            lambda: signals.open_activity_graph_tab.emit(
                self.model.get_key(self.currentIndex())
            )
        )
        menu.addAction(self.new_activity_action)
        menu.addAction(self.duplicate_activity_action)
        menu.addAction(self.duplicate_activity_new_loc_action)
        menu.addAction(self.delete_activity_action)
        menu.addAction(
            qicons.edit, "Relink the activity exchanges",
            self.relink_activity_exchanges
        )
        menu.addAction(
            qicons.duplicate_to_other_database, "Duplicate to other database",
            self.duplicate_activities_to_db
        )

        # Submenu copy to clipboard
        submenu_copy = QtWidgets.QMenu(menu)
        submenu_copy.setTitle('Copy to clipboard')
        submenu_copy.setIcon(qicons.copy_to_clipboard)
        submenu_copy.addAction(self.copy_exchanges_for_SDF_action)
        menu.addMenu(submenu_copy)

        menu.exec_(event.globalPos())

    def connect_signals(self):
        signals.database_read_only_changed.connect(self.update_activity_table_read_only)
        self.new_activity_action.triggered.connect(
            lambda: signals.new_activity.emit(self.database_name)
        )
        self.duplicate_activity_action.triggered.connect(self.duplicate_activities)
        self.duplicate_activity_new_loc_action.triggered.connect(self.duplicate_activity_to_new_loc)
        self.delete_activity_action.triggered.connect(self.delete_activities)
        self.copy_exchanges_for_SDF_action.triggered.connect(self.copy_exchanges_for_SDF)
        self.doubleClicked.connect(self.open_activity_tab)
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)
        self.model.updated.connect(self.set_context_menu_policy)
        self.model.updated.connect(self.update_filter_settings)

    def get_key(self, proxy: QtCore.QModelIndex) -> tuple:
        return self.model.get_key(proxy)

    def update_filter_settings(self) -> None:
        # Write the column indices so only those columns get filter button
        if isinstance(self.model.filterable_columns, dict):
            self.header.column_indices = list(self.model.filterable_columns.values())

    @Slot(QtCore.QModelIndex, name="openActivityTab")
    def open_activity_tab(self, proxy: QtCore.QModelIndex) -> None:
        self.open_activity_tab_w_key(self.model.get_key(proxy))

    @Slot(name="openActivityTabs")
    def open_activity_tabs(self) -> None:
        for proxy in self.selectedIndexes():
            self.open_activity_tab_w_key(self.model.get_key(proxy))

    def open_activity_tab_w_key(self, key) -> None:
        signals.safe_open_activity_tab.emit(key)
        signals.add_activity_to_history.emit(key)

    @Slot(name="relinkActivityExchanges")
    def relink_activity_exchanges(self) -> None:
        for key in (self.model.get_key(a) for a in self.selectedIndexes()):
            signals.relink_activity.emit(key)

    @Slot(name="deleteActivities")
    def delete_activities(self) -> None:
        self.model.delete_activities(self.selectedIndexes())

    @Slot(name="duplicateActivitiesWithinDb")
    def duplicate_activities(self) -> None:
        self.model.duplicate_activities(self.selectedIndexes())

    @Slot(name="duplicateActivitiesToNewLocWithinDb")
    def duplicate_activity_to_new_loc(self) -> None:
        self.model.duplicate_activity_to_new_loc(self.selectedIndexes())

    @Slot(name="duplicateActivitiesToOtherDb")
    def duplicate_activities_to_db(self) -> None:
        self.model.duplicate_activities_to_db(self.selectedIndexes())

    @Slot(name="copyFlowInformation")
    def copy_exchanges_for_SDF(self) -> None:
        self.model.copy_exchanges_for_SDF(self.selectedIndexes())

    def sync(self, db_name: str) -> None:
        self.model.sync(db_name)

    @Slot(name="updateMenuContext")
    def set_context_menu_policy(self) -> None:
        if self.model.technosphere:
            self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
            self.db_read_only = project_settings.db_is_readonly(self.database_name)
            self.update_activity_table_read_only(self.database_name, self.db_read_only)
        else:
            self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

    def search(self, pattern1: str = None) -> None:
        self.model.search(pattern1)
        self.apply_filters()

    @Slot(name="resetSearch")
    def reset_search(self) -> None:
        self.model.sync(self.model.database_name)

    @Slot(str, bool, name="updateReadOnly")
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

class ActivitiesBiosphereTree(ABDictTreeView):
    HEADERS = ["ISIC rev.4 ecoinvent", "reference product", "name", "location", "unit", "key"]

    def __init__(self, parent=None, database_name=None):
        super().__init__(parent)
        self.database_name = database_name
        self.HEADERS = AB_metadata.get_existing_fields(self.HEADERS)

        # set drag ability
        self.setDragEnabled(True)
        self.setDragDropMode(ABDictTreeView.DragOnly)
        self.technosphere = True  # we need this for drag/drop functionality
        # set model
        self.model = ActivitiesBiosphereTreeModel(self, self.database_name)
        self.setModel(self.model)
        self.model.updated.connect(self.custom_view_sizing)
        self.model.updated.connect(self.optional_expand)
        self.model.sync()

    def _connect_signals(self):
        super()._connect_signals()
        self.doubleClicked.connect(self.open_activity_tab)
        # Signal for when new activity is added --> self.open_activity
        # Signal for when activity is edited --> self.open_activity)
        # Signal for when activity is deleted --> self.open_activity)

    @Slot(name="syncTree")
    def sync(self, query=None) -> None:
        self.model.sync(query)

    @Slot(name="optionalExpandAll")
    def optional_expand(self) -> None:
        """auto-expand on sync with query through this function.

        NOTE: self.expandAll() is terribly slow with large trees, so you are advised not to use this without
         something like search [as implemented below through the query check].
         Could perhaps be fixed with canFetchMore and fetchMore, see also links below:
         https://interest.qt-project.narkive.com/ObOvIpWF/qtreeview-expand-expandall-performance
         https://www.qtcentre.org/threads/31642-Speed-Up-TreeView
        """
        if self.model.query and self.model.matches <= 250:
            self.expandAll()

    @Slot(name="openActivity")
    def open_activity(self):
        """'Opens' the method tree, dependent on the previous state this method will
        generate a new tree and then expand all the nodes that were previously expanded.
        """
        expands = self.expanded_list()
        self.model.setup_model_data()
        self.model.sync()
        iter = self.model.iterator(None)
        while iter != None:
            item = self.build_path(iter)
            if item in expands:
                self.setExpanded(self.model.createIndex(iter.row(), 0, iter), True)
            iter = self.model.iterator(iter)

    def get_key(self, proxy: QtCore.QModelIndex) -> tuple:
        # TODO see if I can select underlying entries programatically if not leaf???

        return self.selected_keys()

    @Slot(name="openActivityTab")
    def open_activity_tab(self):
        tree_level = self.tree_level()
        if tree_level[0] == 'leaf':
            key = tree_level[1][-1]
            signals.safe_open_activity_tab.emit(key)
            signals.add_activity_to_history.emit(key)

    def contextMenuEvent(self, event) -> None:
        """Right clicked menu, action depends on item level."""
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QtWidgets.QMenu(self)
        if self.tree_level()[0] == 'leaf':
            pass
        else:
            pass
        menu.exec_(event.globalPos())

    def selected_keys(self) -> Iterable:
        """Return all keys selected."""
        tree_level = self.tree_level()
        if tree_level[0] == 'leaf':
            # select key of the leaf
            return [tree_level[1][-1]]
        if tree_level[0] == 'root':
            # filter on the root + ', '
            # (this needs to be added in case one root level starts with a shorter name of another one
            # example: 'activity a' and 'activity a, words'
            filter_on = tree_level[1]
        else:  # branch level
            # filter on the branch and its parents/roots
            filter_on = str(tuple(tree_level[1]))[1:-2]

        activities = self.model.get_keys(filter_on)
        return activities

    def tree_level(self) -> tuple:
        """Return list of (tree level, content).
        Where content depends on level:
        leaf:   the descending list of branch levels, list()
        root:   the name of the root, str()
        branch: the descending list of branch levels, list()
            leaf/branch example: ('CML 2001', 'climate change')"""
        indexes = self.selectedIndexes()
        if indexes[1].data() != '' or indexes[2].data() != '':
            return 'leaf', self.find_levels()
        elif indexes[0].parent().data() is None:
            return 'root', indexes[0].data()
        else:
            return 'branch', self.find_levels()

    def find_levels(self, level=None) -> list:
        """Find all levels of branch."""
        if not level:
            idx = self.selectedIndexes()
            if idx[-1].data() != '':
                level = idx[-1]
            else:
                level = idx[0]
            parent = idx[0].parent()
        else:
            parent = level.parent()
        levels = [level.data()]
        while parent.data() is not None:
            levels.append(parent.data())
            parent = parent.parent()
        return levels[::-1]

    def expanded_list(self):
        it = self.model.iterator(None)
        expanded_items = []
        while it != None:
            if self.isExpanded(self.model.createIndex(it.row(), 0, it)):
                expanded_items.append(self.build_path(it))
            it = self.model.iterator(it)
        return expanded_items

    def build_path(self, iter):
        """Given an iterator of the TreeItem type build the path back to the
        root ancestor. This is intended for testing membership of expanded
        entries."""
        item = set()
        p = iter
        while p != self.model.root:
            item.add(p.data(0))
            p = p.parent()
        return item

    def search(self, query: str = None) -> None:
        self.model.sync(query)

    @Slot(name="resetSearch")
    def reset_search(self) -> None:
        self.model.sync()
