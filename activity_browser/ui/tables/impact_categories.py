# -*- coding: utf-8 -*-
from typing import Iterable

import brightway2 as bw
from pandas import DataFrame
from PySide2 import QtWidgets
from PySide2.QtCore import QModelIndex, Slot

from ...signals import signals
from ..icons import qicons
from ..widgets import TupleNameDialog
from .views import ABDataFrameView, ABDictTreeView, tree_model_decorate
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
        # set data
        self.dataframe = self.get_dataframe()
        self.sync()
        self.setColumnHidden(self.method_col, True)

    def _connect_signals(self):
        super()._connect_signals()
        signals.project_selected.connect(self.sync)
        self.doubleClicked.connect(self.method_selected)

    def _select_model(self):
        return MethodsTreeModel(self.data)

    def get_dataframe(self) -> None:
        """Retrieve dataframe of (queried) impact categories"""
        sorted_names = sorted([(", ".join(method), method) for method in bw.methods])

        dataframe = DataFrame([
            self.build_row(method_obj) for method_obj in sorted_names
        ], columns=self.HEADERS)
        self.method_col = dataframe.columns.get_loc("method")
        return dataframe

    @tree_model_decorate
    def sync(self, query=None) -> None:
        self.nest_data()
        if query:
            self.data, self.matches = self.search_tree(self.tree_data, query)
        else:
            self.data = self.tree_data

    def query_sync(self, query=None):
        """auto-expand on sync with query through this function."""
        if query and len(query) != 0:
            self.sync(query=query)
            if self.matches <= 285:
                self.expandAll()
            # NOTE: self.expandAll() is terribly slow with large trees, so you are advised not to use this without
            # something like search [as implemented below through the query check].
            # Could perhaps be fixed with canFetchMore and fetchMore, see also links below:
            # https://interest.qt-project.narkive.com/ObOvIpWF/qtreeview-expand-expandall-performance
            # https://www.qtcentre.org/threads/31642-Speed-Up-TreeView
        else:
            self.sync()

    def build_row(self, method_obj) -> dict:
        method = bw.methods[method_obj[1]]
        return {
            "Name": method_obj[0],
            "Unit": method.get("unit", "Unknown"),
            "# CFs": str(method.get("num_cfs", 0)),
            "method": method_obj[1],
        }

    def nest_data(self):
        """Convert impact category dataframe into nested dict format, apply search if required.

        Format is:
        {root1: {branch1: {leaf1: data},
                          {leaf2: data}},
                {branch2: {branch3: {leaf3: data},
                                    {leaf4: data}},
                          {branch4: {leaf5: data},
                                    {leaf6: data}},
                          {leaf7: data}}}
        Where:
        rootx  : top level category (str) eg: CML 2001
        branchx: sub level category (str) eg: climate change
                 can be arbitrary amount of branches
        leafx  : category level (str)     eg: GWP 100a
                 leaves and branches can be mixed together under roots or other branches
        data   : data of category (tuple) eg: ('CML 2001, climate change, GWP 100a',
                                               'kg CO2-Eq',
                                               160,
                                               "('CML 2001', 'climate change', 'GWP 100a')")
                 here each index of the tuple refers to the data in the HEADERS list of this class
        """
        updated_df = self.prep_df(self.dataframe)
        dirty_nested_df = self.retro_dictify(updated_df)
        self.tree_data, _ = self.names_dict_clean(dirty_nested_df)

    def get_method(self, tree_level=None) -> tuple:
        """Retrieve method data"""
        if not tree_level:
            tree_level = self.tree_level()
        return self.dataframe[self.dataframe['Name'] == tree_level[1]]['method']

    @Slot(QModelIndex, name="methodSelection")
    def method_selected(self):
        tree_level = self.tree_level()
        if tree_level[0] == 'leaf':
            method = self.get_method(tree_level).to_list()[0]
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
            method = self.get_method(tree_level)
            return (m for m in method)
        elif tree_level[0] == 'root':
            # filter on the root + ', '
            # (this needs to be added in case one root level starts with a shorter name of another one
            # example: 'ecological scarcity 2013' and 'ecological scarcity 2013 no LT'
            filter_on = tree_level[1] + ', '
        else:
            # filter on the branch and its parents/roots
            filter_on = ', '.join(tree_level[1])

        methods = self.dataframe[self.dataframe['Name'].str.startswith(filter_on)]['method']
        return (m for m in methods)

    def tree_level(self):
        """Return list of [tree level, content].

        Where content depends on level:
        leaf:   the name of impact category, str()
        root:   the name of the root, str()
        branch: the descending list of branch levels, list()
            branch example: ['CML 2001', 'climate change']"""
        if self.selectedIndexes()[1].data() != '' or self.selectedIndexes()[2].data() != '':
            return ['leaf', self.selectedIndexes()[0].data()]
        elif self.selectedIndexes()[0].parent().data() is None:
            return ['root', self.selectedIndexes()[0].data()]
        else:
            return ['branch', self.find_levels()]

    def find_levels(self, level=None):
        """Find all levels of branch."""
        if not level:
            level = self.selectedIndexes()[0]
        par = level.parent()  # par for parent
        levels = [level.data()]
        if par.data() != None:
            while par.data() != None:
                levels.append(par.data())
                par = par.parent()
        else:
            levels.append(par.data())
        return levels[::-1]

    def prep_df(self, df):
        """Prepare data to be nested."""
        splits = []
        for row in df.iterrows():
            data = tuple(row[1])
            names = data[0]  # 'Name' column

            split = names.split(', ')
            split.append(data)
            splits.append(split)
        return DataFrame(splits)

    def retro_dictify(self, frame):
        """Create nested dict from dataframe."""
        # From https://stackoverflow.com/a/19900276 but changed -2 to -1
        # this version is ~2 orders of magnitude faster than the pandas option in the same answer
        d = {}
        for row in frame.values:
            here = d
            for elem in row[:-1]:
                if elem not in here:
                    here[elem] = {}
                here = here[elem]
            here[row[-1]] = row[-1]
        return d

    def names_dict_clean(self, names_dict):
        """Clean output from retro_dictify.

        Removes 'None' nodes and combines irrelevant nodes (with only 1 sublevel)
        """
        clean_dict = {}
        for key, *value in names_dict.items():

            if type(value[0]) == dict and None not in value[0].keys():
                # this is not the leaf node, go deeper to find leaf

                tree, is_leaf = self.names_dict_clean(value[0])
                if not is_leaf and len(value[0]) == 1:
                    # 'tree' is not leaf (end node) and only one sub level
                    # combine sublevel, then add to tree

                    key_orig = [k for k in tree.keys()][0]
                    key = key + ', ' + key_orig
                    clean_dict[key] = tree[key_orig]
                else:
                    # 'tree' is either a leaf or has more sublevels
                    # add as dict entry
                    clean_dict[key] = tree
            else:
                # this is a leaf node, return the key
                return key, True
        return clean_dict, False

    def search_tree(self, tree, query, matches=0):
        """Search the tree and remove non-matching leaves and branches."""
        remove = []
        for key, value in tree.items():
            if type(value) == tuple:
                # this is a leaf node
                if query.lower() not in value[0].lower():
                    # the query does not match
                    remove.append(key)
                else:
                    matches += 1
            else:
                # this is not a leaf node, go deeper
                sub_tree, matches = self.search_tree(value, query, matches)
                if len(sub_tree) > 0:
                    # there were query matches in this branch
                    tree[key] = sub_tree
                else:
                    # there were no query matches in this branch
                    remove.append(key)

        for key in remove:
            tree.pop(key)
        return tree, matches

    @Slot(name="copyMethod")
    def copy_method(self) -> None:
        """Call copy on the (first) selected method and present rename dialog."""
        method = bw.Method(self.get_method())
        dialog = TupleNameDialog.get_combined_name(
            self, "Impact category name", "Combined name:", method.name, "Copy"
        )
        if dialog.exec_() == TupleNameDialog.Accepted:
            new_name = dialog.result_tuple
            if new_name in bw.methods:
                warn = "Impact Category with name '{}' already exists!".format(new_name)
                QtWidgets.QMessageBox.warning(self, "Copy failed", warn)
                return
            method.copy(new_name)
            print("Copied method {} into {}".format(str(method.name), str(new_name)))
            signals.new_method.emit(new_name)


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
