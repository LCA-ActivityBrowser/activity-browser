# -*- coding: utf-8 -*-
from typing import Iterable

from PySide2 import QtWidgets
from PySide2.QtCore import QModelIndex, Slot

from activity_browser import actions
from activity_browser.mod.bw2data import methods

from ...signals import signals
from ..icons import qicons
from .views import ABDictTreeView, ABFilterableDataFrameView, ABDataFrameView
from .models import MethodCharacterizationFactorsModel, MethodsListModel, MethodsTreeModel
from .delegates import FloatDelegate, UncertaintyDelegate
from .inventory import ActivitiesBiosphereTable


class MethodsTable(ABFilterableDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(ABFilterableDataFrameView.DragDrop)
        self.model = MethodsListModel(self)

        # create variables for filtering
        if isinstance(self.model.filterable_columns, dict):
            self.header.column_indices = list(self.model.filterable_columns.values())

        self.duplicate_method_action = actions.MethodDuplicate.get_QAction(self.selected_methods, None)
        self.delete_method_action = actions.MethodDelete.get_QAction(self.selected_methods, None)

        self.connect_signals()

    def connect_signals(self):
        self.doubleClicked.connect(lambda p: signals.method_selected.emit(self.model.get_method(p)))
        self.model.updated.connect(self.update_proxy_model)
        methods.metadata_changed.connect(self.sync)

    def selected_methods(self) -> Iterable:
        """Returns a generator which yields the 'method' for each row."""
        return (self.model.get_method(p) for p in self.selectedIndexes())

    @Slot(name="syncTable")
    def sync(self, query=None) -> None:
        self.model.sync(query)

    def contextMenuEvent(self, event) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return

        menu = QtWidgets.QMenu(self)
        menu.addAction(
            qicons.edit, "Inspect Impact Category",
            lambda: signals.method_selected.emit(self.model.get_method(self.currentIndex()))
        )
        menu.addAction(self.duplicate_method_action)
        menu.addAction(self.delete_method_action)
        menu.exec_(event.globalPos())


class MethodsTree(ABDictTreeView):
    # TODO Current approach uses a complete regeneration of the tree including
    # TODO the root and all branch and leaf nodes. This conflicts with the fundamental
    # TODO structure of these models using links between parent and child nodes as new
    # TODO addresses are provided, invalidating provided indexes
    """
    The TreeView object for the Tree model of the AB used for the impact categories:

    NOTE: A limitation with the current implementation means that there is a limit
    to the names for the Impact categories (IC): This is as follows

    Assume an Impact category exists as:
    ('USEtox w-o LT', 'human toxicity w/o LT', 'carcinogenic w/o LT')
    Then any of the following cannot exist:
    ('human toxicity w/o LT', 'USEtox w-o LT', 'carcinogenic w/o LT')
    ('human toxicity w/o LT', 'carcinogenic w/o LT', 'USEtox w-o LT')
    ('USEtox w-o LT', 'carcinogenic w/o LT', 'human toxicity w/o LT')
    ('carcinogenic w/o LT', 'USEtox w-o LT', 'human toxicity w/o LT')
    ('carcinogenic w/o LT', 'human toxicity w/o LT', 'USEtox w-o LT')
    Due to the use of sets for comparisons the IC's cannot use identical names in
    a different order for a new IC.


    """
    HEADERS = ["Name", "Unit", "# CFs", "method"]

    def __init__(self, parent=None):
        super().__init__(parent)
        # set drag ability
        self.setDragEnabled(True)
        self.setDragDropMode(ABDictTreeView.DragOnly)

        # set model
        self.model = MethodsTreeModel(self)
        self.setModel(self.model)
        self.model.updated.connect(self.optional_expand)
        self.model.sync()
        self.setColumnHidden(self.model.method_col, True)

        # set first column's size
        self.setColumnWidth(0, 200)

        self.duplicate_method_action = actions.MethodDuplicate.get_QAction(self.selected_methods, self.tree_level)
        self.delete_method_action = actions.MethodDelete.get_QAction(self.selected_methods, self.tree_level)

        self._connect_signals()

    def _connect_signals(self):
        self.doubleClicked.connect(self.method_selected)
        methods.metadata_changed.connect(self.open_method)

    @Slot(name="syncTree")
    def sync(self, query=None) -> None:
        self.model.sync()

    @Slot(name="optionalExpandAll")
    def optional_expand(self) -> None:
        """auto-expand on sync with query through this function.

        NOTE: self.expandAll() is terribly slow with large trees, so you are advised not to use this without
         something like search [as implemented below through the query check].
         Could perhaps be fixed with canFetchMore and fetchMore, see also links below:
         https://interest.qt-project.narkive.com/ObOvIpWF/qtreeview-expand-expandall-performance
         https://www.qtcentre.org/threads/31642-Speed-Up-TreeView
        """
        if self.model.query and self.model.matches <= 285:
            self.expandAll()

    @Slot(name="openMethod")
    def open_method(self):
        """'Opens' the method tree, dependent on the previous state this method will
        generate a new tree and then expand all the nodes that were previously expanded.
        """
        expands = self.expanded_list()
        self.model.setup_model_data()
        self.model.sync()
        iterator = self.model.iterator(None)
        while iterator != None:
            item = self.build_path(iterator)
            if item in expands:
                self.setExpanded(self.model.createIndex(iterator.row(), 0, iterator), True)
            iterator = self.model.iterator(iterator)

    @Slot(QModelIndex, name="methodSelection")
    def method_selected(self):
        tree_level = self.tree_level()
        if tree_level[0] == 'leaf':
            method = self.model.get_method(tree_level)
            signals.method_selected.emit(method)

    def contextMenuEvent(self, event) -> None:
        """Right clicked menu, action depends on item level."""
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QtWidgets.QMenu(self)

        if self.tree_level()[0] == 'leaf':
            menu.addAction(qicons.edit, "Inspect Impact Category", self.method_selected)
        else:
            menu.addAction(qicons.forward, "Expand all sub levels", self.expand_branch)
            menu.addAction(qicons.backward, "Collapse all sub levels", self.collapse_branch)
        
        menu.addSeparator()

        menu.addAction(self.duplicate_method_action)
        menu.addAction(self.delete_method_action)

        menu.exec_(event.globalPos())

    def selected_methods(self) -> Iterable:
        """Returns a generator which yields the 'method' for each row."""
        tree_level = self.tree_level()
        if tree_level[0] == 'leaf':
            # filter on the leaf
            return [self.model.get_method(tree_level)]

        if tree_level[0] == 'root':
            # filter on the root + ', '
            # (this needs to be added in case one root level starts with a shorter name of another one
            # example: 'ecological scarcity 2013' and 'ecological scarcity 2013 no LT'
            filter_on = tree_level[1] + ', '
        else:
            # filter on the branch and its parents/roots
            filter_on = ', '.join(tree_level[1]) + ', '

        methods = self.model.get_methods(filter_on)
        return methods

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
        level = level or next(iter(self.selectedIndexes()))
        parent = level.parent()  # par for parent
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


class MethodCharacterizationFactorsTable(ABFilterableDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = MethodCharacterizationFactorsModel(parent=self)
        self.setVisible(False)
        self.setItemDelegateForColumn(2, FloatDelegate(self))
        self.setItemDelegateForColumn(4, UncertaintyDelegate(self))
        self.setItemDelegateForColumn(6, FloatDelegate(self))
        self.setItemDelegateForColumn(7, FloatDelegate(self))
        self.setItemDelegateForColumn(8, FloatDelegate(self))
        self.setItemDelegateForColumn(9, FloatDelegate(self))
        self.setItemDelegateForColumn(10, FloatDelegate(self))

        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.set_filter_data)
        self.model.updated.connect(lambda: self.setColumnHidden(5, True))

        self.read_only = True
        self.setAcceptDrops(not self.read_only)

        self.remove_cf_action = actions.CFRemove.get_QAction(self.method_name, self.selected_cfs)
        self.modify_uncertainty_action = actions.CFUncertaintyModify.get_QAction(self.method_name, self.selected_cfs)
        self.remove_uncertainty_action = actions.CFUncertaintyRemove.get_QAction(self.method_name, self.selected_cfs)

        self.model.dataChanged.connect(self.cell_edited)

    def method_name(self):
        return self.model.method.name

    def selected_cfs(self):
        return [self.model.get_cf(i) for i in self.selectedIndexes()]

    def cell_edited(self) -> None:
        """Store the edit made to the table in the underlying data."""
        if len(self.selectedIndexes()) == 0: return

        cell = self.selectedIndexes()[0]
        column = cell.column()

        if column in [2]:
            # if the column changed is 2 (Amount) --> This is a list in case of future editable columns
            new_amount = self.model.get_value(cell)
            actions.CFAmountModify.run(self.method_name, self.selected_cfs, new_amount)

    @Slot(bool, name="toggleUncertainColumns")
    def hide_uncertain(self, hide: bool = True) -> None:
        for i in self.model.uncertain_cols:
            self.setColumnHidden(i, hide)
        self.model.set_filterable_columns(hide)
        self.set_filter_data()

    def set_filter_data(self):
        if isinstance(self.model.filterable_columns, dict):
            self.header.column_indices = list(self.model.filterable_columns.values())

    def contextMenuEvent(self, event) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QtWidgets.QMenu(self)
        menu.addAction(self.modify_uncertainty_action)
        self.modify_uncertainty_action.setEnabled(not self.read_only)
        menu.addSeparator()
        menu.addAction(self.remove_uncertainty_action)
        self.remove_uncertainty_action.setEnabled(not self.read_only)
        menu.addAction(self.remove_cf_action)
        self.remove_cf_action.setEnabled(not self.read_only)
        menu.exec_(event.globalPos())

    def dragMoveEvent(self, event) -> None:
        """ Check if drops are allowed when dragging something over.
        """
        source_table = event.source()
        if not isinstance(source_table, ActivitiesBiosphereTable):
            # never allow drops from something other than biosphere databases
            self.setAcceptDrops(False)
        self.setAcceptDrops(not self.read_only)

    def dropEvent(self, event):
        source_table = event.source()
        keys = [source_table.get_key(i) for i in source_table.selectedIndexes()]
        if not isinstance(source_table, ActivitiesBiosphereTable):
            return
        event.accept()
        actions.CFNew.run(self.method_name(), keys)
        # TODO: Resize the view if the table did not already take up the full height.
