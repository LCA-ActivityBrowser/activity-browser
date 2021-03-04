# -*- coding: utf-8 -*-
from copy import deepcopy
import numbers
from typing import Iterator, Optional

import brightway2 as bw
import numpy as np
import pandas as pd
from PySide2.QtCore import QModelIndex, Qt, Slot

from activity_browser.signals import signals
from ...wizards import UncertaintyWizard
from .base import PandasModel, DragPandasModel, TreeItem, BaseTreeModel


class MethodsListModel(DragPandasModel):
    HEADERS = ["Name", "Unit", "# CFs", "method"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.method_col = 0
        signals.project_selected.connect(self.sync)
        signals.new_method.connect(self.filter_on_method)

    def get_method(self, proxy: QModelIndex) -> tuple:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), self.method_col]

    @Slot(QModelIndex, name="copyMethod")
    def copy_method(self, proxy: QModelIndex) -> None:
        method = self.get_method(proxy)
        signals.copy_method.emit(method)

    @Slot(tuple, name="filterOnMethod")
    def filter_on_method(self, method: tuple) -> None:
        query = ", ".join(method)
        self.sync(query)

    @Slot(name="syncTable")
    def sync(self, query=None) -> None:
        sorted_names = sorted([(", ".join(method), method) for method in bw.methods])
        if query:
            sorted_names = (
                m for m in sorted_names if query.lower() in m[0].lower()
            )
        self._dataframe = pd.DataFrame([
            self.build_row(method_obj) for method_obj in sorted_names
        ], columns=self.HEADERS)
        self.method_col = self._dataframe.columns.get_loc("method")
        self.updated.emit()

    @staticmethod
    def build_row(method_obj) -> dict:
        method = bw.methods[method_obj[1]]
        return {
            "Name": method_obj[0],
            "Unit": method.get("unit", "Unknown"),
            "# CFs": str(method.get("num_cfs", 0)),
            "method": method_obj[1],
        }


class CFModel(PandasModel):
    COLUMNS = ["name", "categories", "amount", "unit"]
    HEADERS = ["Name", "Category", "Amount", "Unit", "Uncertainty"] + ["cf"]
    UNCERTAINTY = ["loc", "scale", "shape", "minimum", "maximum"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.cf_column = 0
        self.method: Optional[bw.Method] = None
        signals.method_modified.connect(self.sync)

    @property
    def uncertain_cols(self) -> list:
        return [self._dataframe.columns.get_loc(c) for c in self.UNCERTAINTY]

    @Slot(name="syncExistingModel")
    @Slot(tuple, name="syncNewModel")
    def sync(self, method: Optional[tuple] = None) -> None:
        if self.method and self.method.name != method:
            return
        if method:
            self.method = bw.Method(method)
        assert self.method is not None, "A method must be set."
        self._dataframe = pd.DataFrame([
            self.build_row(obj) for obj in self.method.load()
        ], columns=self.HEADERS + self.UNCERTAINTY)
        self.cf_column = self._dataframe.columns.get_loc("cf")
        self.updated.emit()

    @classmethod
    def build_row(cls, method_cf: tuple) -> dict:
        key, amount = method_cf[:2]
        flow = bw.get_activity(key)
        row = {
            cls.HEADERS[i]: flow.get(c) for i, c in enumerate(cls.COLUMNS)
        }
        # If uncertain, unpack the uncertainty dictionary
        uncertain = not isinstance(amount, numbers.Number)
        if uncertain:
            row.update({k: amount.get(k, "nan") for k in cls.UNCERTAINTY})
            uncertain = amount.get("uncertainty type")
            amount = amount["amount"]
        else:
            uncertain = 0
        row.update({"Amount": amount, "Uncertainty": uncertain, "cf": method_cf})
        return row

    def get_cf(self, proxy: QModelIndex) -> tuple:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), self.cf_column]

    @Slot(QModelIndex, name="modifyCFUncertainty")
    def modify_uncertainty(self, proxy: QModelIndex) -> None:
        """Need to know both keys to select the correct exchange to update."""
        method_cf = self.get_cf(proxy)
        wizard = UncertaintyWizard(method_cf, self.parent())
        wizard.complete.connect(self.modify_cf)
        wizard.show()

    @Slot(list, name="removeCFUncertainty")
    def remove_uncertainty(self, proxy_indexes: Iterator[QModelIndex]) -> None:
        to_be_modified = [self.get_cf(p) for p in proxy_indexes]
        signals.remove_cf_uncertainties.emit(to_be_modified, self.method.name)

    @Slot(tuple, object, name="modifyCf")
    def modify_cf(self, cf: tuple, uncertainty: dict) -> None:
        """Update the CF with new uncertainty information, possibly converting
        the second item in the tuple to a dictionary without losing information.
        """
        data = [*cf]
        if isinstance(data[1], dict):
            data[1].update(uncertainty)
        else:
            uncertainty["amount"] = data[1]
            data[1] = uncertainty
        signals.edit_method_cf.emit(tuple(data), self.method.name)


class ImpactCategoryItem(TreeItem):
    """ Item in MethodsTreeModel."""
    # this manual typing of COLUMNS below could be a risk later:
    # potential fix could be to get data from HEADERS in tables/impact_categories/MethodsTree
    def __init__(self, data: list, parent=None):
        super().__init__(data, parent)

    @classmethod
    def build_item(cls, impact_cat, parent: TreeItem) -> 'ImpactCategoryItem':
        item = cls(list(impact_cat), parent)
        parent.appendChild(item)
        return item


class MethodsTreeModel(BaseTreeModel):
    """
    Tree model for impact categories.
    Tree is auto generated in tables/impact_categories/MethodsTree
    """
    HEADERS = ["Name", "Unit", "# CFs", "method"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.root = ImpactCategoryItem.build_root(self.HEADERS)

        # All of the various variables.
        self._dataframe: Optional[pd.DataFrame] = None
        self.method_col = 0
        self.tree_data = None
        self.matches = None
        self.query = None

        self.setup_model_data()

        signals.project_selected.connect(self.sync)
        signals.new_method.connect(self.setup_model_data)
        signals.new_method.connect(self.filter_on_method)

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsDragEnabled

    def build_tree(self, data: dict, root: ImpactCategoryItem) -> None:
        for key, value in data.items():
            if isinstance(value, dict):
                new_data = [key] + [""] * (self.columnCount() - 1)
                new_root = root.build_item(new_data, root)
                self.build_tree(value, new_root)
            else:
                ImpactCategoryItem.build_item(value, root)

    @Slot(name="methodsAltered")
    def setup_model_data(self) -> None:
        """Construct a dataframe of impact categories and a complete nested
        dict of the dataframe.

        Trigger this at the start and when a method is added/deleted.
        """
        sorted_names = sorted([(", ".join(method), method) for method in bw.methods])
        self._dataframe = pd.DataFrame([
            MethodsListModel.build_row(method_obj) for method_obj in sorted_names
        ], columns=self.HEADERS)
        self.method_col = self._dataframe.columns.get_loc("method")
        self.tree_data = self.nest_data(self._dataframe)

    @Slot(name="clearSyncModel")
    @Slot(str, name="syncModel")
    def sync(self, query: str = None) -> None:
        self.beginResetModel()
        self.root.clear()
        self.query = query
        if self.query:
            tree = deepcopy(self.tree_data)
            self._data, self.matches = self.search_tree(tree, self.query)
        else:
            self._data = self.tree_data
        self.build_tree(self._data, self.root)
        self.endResetModel()
        self.updated.emit()

    def get_method(self, tree_level: tuple) -> tuple:
        """Retrieve method data"""
        name = tree_level[1]
        methods = self._dataframe.loc[self._dataframe["Name"] == name, "method"]
        return next(iter(methods))

    def get_methods(self, name: str) -> Iterator:
        methods = self._dataframe.loc[self._dataframe["Name"].str.startswith(name), "method"]
        if self.query:
            queries = [
                method for method in methods
                if self.query.lower() in ', '.join(method).lower()
            ]
            return queries
        return methods

    @Slot(QModelIndex, name="copyMethod")
    def copy_method(self, level: tuple) -> None:
        method = self.get_method(level)
        signals.copy_method.emit(method)

    @Slot(tuple, name="filterOnMethod")
    def filter_on_method(self, method: tuple) -> None:
        query = ", ".join(method)
        self.sync(query)

    @staticmethod
    def nest_data(df: pd.DataFrame) -> dict:
        """Convert impact category dataframe into nested dict format.

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
        data = np.empty(df.shape[0], dtype=object)
        for idx, row in enumerate(df.to_numpy(dtype=object)):
            split = row[0].split(', ')  # split 'Name' column on ', '
            split.append(tuple(row))
            data[idx] = split

        # From https://stackoverflow.com/a/19900276 but changed -2 to -1
        #  this version is ~2 orders of magnitude faster than the pandas
        #  option in the same answer
        simple_dict = {}
        for row in data:
            here = simple_dict
            for elem in row[:-1]:
                if elem not in here:
                    here[elem] = {}
                here = here[elem]
            here[row[-1]] = row[-1]

        tree, _ = MethodsTreeModel.simplify_dict(simple_dict)
        return tree

    @staticmethod
    def simplify_dict(names_dict: dict) -> (dict, bool):
        """Recursively flatten the given nested dictionary."""
        clean_dict = {}
        for key, value in names_dict.items():
            if isinstance(value, dict):
                # this is not the leaf node, go deeper to find leaf
                tree, is_leaf = MethodsTreeModel.simplify_dict(value)
                if not is_leaf and len(value) == 1:
                    # 'tree' is not leaf (end node) and only one sub level
                    # combine sublevel, then add to tree
                    key_orig = next(iter(tree.keys()))
                    key = "{}, {}".format(key, key_orig)
                    clean_dict[key] = tree[key_orig]
                else:
                    # 'tree' is either a leaf or has more sublevels
                    # add as dict entry
                    clean_dict[key] = tree
            else:
                # this is a leaf node, return the key
                return key, True
        return clean_dict, False

    @staticmethod
    def search_tree(tree: dict, query: str, matches: int = 0) -> (dict, int):
        """Search the tree and remove non-matching leaves and branches."""
        remove = []
        for key, value in tree.items():
            if isinstance(value, tuple):
                # this is a leaf node
                if query.lower() not in value[0].lower():
                    # the query does not match
                    remove.append(key)
                else:
                    matches += 1
            else:
                # this is not a leaf node, go deeper
                sub_tree, matches = MethodsTreeModel.search_tree(value, query, matches)
                if len(sub_tree) > 0:
                    # there were query matches in this branch
                    tree[key] = sub_tree
                else:
                    # there were no query matches in this branch
                    remove.append(key)

        for key in remove:
            tree.pop(key)
        return tree, matches
