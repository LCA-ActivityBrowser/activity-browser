# -*- coding: utf-8 -*-
from typing import Iterable

from PySide2 import QtWidgets
from PySide2.QtCore import QModelIndex, Slot

from ...signals import signals
from ..icons import qicons
from .views import ABDataFrameView, ABDictTreeView
from .models import CFModel, MethodsListModel, MethodsTreeModel
from .delegates import FloatDelegate, UncertaintyDelegate


class MethodsTable(ABDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(ABDataFrameView.DragOnly)
        self.model = MethodsListModel(self)

        self.doubleClicked.connect(
            lambda p: signals.method_selected.emit(self.model.get_method(p))
        )
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)

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
        menu = QtWidgets.QMenu(self)
        menu.addAction(
            qicons.copy, "Duplicate Impact Category",
            lambda: self.model.copy_method(self.currentIndex())
        )
        menu.exec_(event.globalPos())


class MethodsTree(ABDictTreeView):
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

    @Slot(QModelIndex, name="methodSelection")
    def method_selected(self):
        tree_level = self.tree_level()
        if tree_level[0] == 'leaf':
            method = self.model.get_method(tree_level)
            signals.method_selected.emit(method)

    def contextMenuEvent(self, event) -> None:
        """Right clicked menu, action depends on item level."""
        menu = QtWidgets.QMenu(self)
        if self.tree_level()[0] == 'leaf':
            menu.addAction(qicons.copy, "Duplicate Impact Category", self.copy_method)
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
            filter_on = ', '.join(tree_level[1])

        methods = self.model.get_methods(filter_on)
        return methods

    def tree_level(self) -> tuple:
        """Return list of (tree level, content).

        Where content depends on level:
        leaf:   the name of impact category, str()
        root:   the name of the root, str()
        branch: the descending list of branch levels, list()
            branch example: ('CML 2001', 'climate change')"""
        indexes = self.selectedIndexes()
        if indexes[1].data() != '' or indexes[2].data() != '':
            return 'leaf', indexes[0].data()
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


class CFTable(ABDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = CFModel(parent=self)
        self.setVisible(False)
        self.setItemDelegateForColumn(4, UncertaintyDelegate(self))
        self.setItemDelegateForColumn(6, FloatDelegate(self))
        self.setItemDelegateForColumn(7, FloatDelegate(self))
        self.setItemDelegateForColumn(8, FloatDelegate(self))
        self.setItemDelegateForColumn(9, FloatDelegate(self))
        self.setItemDelegateForColumn(10, FloatDelegate(self))
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)

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

    def contextMenuEvent(self, event) -> None:
        menu = QtWidgets.QMenu(self)
        menu.addAction(qicons.edit, "Modify uncertainty", self.modify_uncertainty)
        menu.addSeparator()
        menu.addAction(qicons.delete, "Remove uncertainty", self.remove_uncertainty)
        menu.exec_(event.globalPos())

    @Slot(name="modifyCFUncertainty")
    def modify_uncertainty(self) -> None:
        self.model.modify_uncertainty(self.currentIndex())

    @Slot(name="removeCFUncertainty")
    def remove_uncertainty(self) -> None:
        self.model.remove_uncertainty(self.selectedIndexes())
