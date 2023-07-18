# -*- coding: utf-8 -*-
from typing import Iterable

from PySide2 import QtWidgets
from PySide2.QtCore import QModelIndex, Slot

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

        self.doubleClicked.connect(
            lambda p: signals.method_selected.emit(self.model.get_method(p))
        )
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)
        signals.new_method.connect(self.sync)
        signals.method_deleted.connect(self.sync)

    def selected_methods(self) -> Iterable:
        """Returns a generator which yields the 'method' for each row."""
        return (self.model.get_method(p) for p in self.selectedIndexes())

    @Slot(name="syncTable")
    def sync(self, query=None) -> None:
        self.model.sync(query)

    @Slot(name="resizeView")
    def custom_view_sizing(self) -> None:
        self.setColumnHidden(self.model.method_col, True)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum
        ))

    def contextMenuEvent(self, event) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QtWidgets.QMenu(self)
        menu.addAction(
            qicons.copy, "Duplicate Impact Category",
            lambda: self.model.copy_method(self.currentIndex())
        )
        menu.addAction(
            qicons.delete, "Delete Impact Category",
            lambda: self.model.delete_method(self.currentIndex())
        )
        menu.addAction(
            qicons.edit, "Inspect Impact Category",
            lambda: signals.method_selected.emit(self.model.get_method(self.currentIndex()))
        )
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
        self.model.updated.connect(self.custom_view_sizing)
        self.model.updated.connect(self.optional_expand)
        self.model.sync()
        self.setColumnHidden(self.model.method_col, True)

    def _connect_signals(self):
        super()._connect_signals()
        self.doubleClicked.connect(self.method_selected)
        signals.new_method.connect(self.open_method)
        signals.method_deleted.connect(self.open_method)

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
        iter = self.model.iterator(None)
        while iter != None:
            item = self.build_path(iter)
            if item in expands:
                self.setExpanded(self.model.createIndex(iter.row(), 0, iter), True)
            iter = self.model.iterator(iter)

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
        menu.addAction(qicons.copy, "Duplicate Impact Category",
                       lambda: self.copy_method()
                       )
        menu.addAction(qicons.delete, "Delete Impact Category",
                       lambda: self.delete_method()
                       )
        if self.tree_level()[0] == 'leaf':
            menu.addAction(qicons.edit, "Inspect Impact Category", self.method_selected)
        else:
            menu.addAction(qicons.forward, "Expand all sub levels", self.expand_branch)
            menu.addAction(qicons.backward, "Collapse all sub levels", self.collapse_branch)
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

    @Slot(name="copyMethod")
    def copy_method(self) -> None:
        """Call copy on the (first) selected method and present rename dialog."""
        self.model.copy_method(self.tree_level())

    @Slot(name="deleteMethod")
    def delete_method(self) -> None:
        """Call copy on the (first) selected method and present rename dialog."""
        self.model.delete_method(self.tree_level())

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
        self.model.updated.connect(self.custom_view_sizing)
        self.model.updated.connect(self.set_filter_data)
        self.read_only = True
        self.setAcceptDrops(not self.read_only)

        signals.set_uncertainty.connect(self.modify_uncertainty)

    @Slot(name="resizeView")
    def custom_view_sizing(self) -> None:
        self.setColumnHidden(self.model.cf_column, True)
        self.hide_uncertain()
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum
        ))

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
        edit = menu.addAction(qicons.edit, "Modify uncertainty", self.modify_uncertainty)
        edit.setEnabled(not self.read_only)
        menu.addSeparator()
        remove = menu.addAction(qicons.clear, "Remove uncertainty", self.remove_uncertainty)
        remove.setEnabled(not self.read_only)
        delete = menu.addAction(qicons.delete, "Delete", self.delete_cf)
        delete.setEnabled(not self.read_only)
        menu.exec_(event.globalPos())

    @Slot(name="modifyCFUncertainty")
    def modify_uncertainty(self, index) -> None:
        if index.internalId() == self.currentIndex().internalId():
            self.model.modify_uncertainty(self.currentIndex())

    @Slot(name="removeCFUncertainty")
    def remove_uncertainty(self) -> None:
        self.model.remove_uncertainty(self.selectedIndexes())

    @Slot(name="deleteCF")
    def delete_cf(self) -> None:
        self.model.delete_cf(self.selectedIndexes())

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
        signals.add_cf_method.emit(keys[0], self.model.method.name)
        # TODO: Resize the view if the table did not already take up the full height.
