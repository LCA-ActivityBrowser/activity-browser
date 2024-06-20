import numbers
from copy import deepcopy
from typing import Iterator, Optional

import numpy as np
import pandas as pd
from PySide2.QtCore import QModelIndex, Qt, Slot

from activity_browser import signals
from activity_browser.mod import bw2data as bd

from .base import BaseTreeModel, DragPandasModel, EditablePandasModel, TreeItem


class MethodsListModel(DragPandasModel):
    HEADERS = ["Name", "Unit", "# CFs", "method"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.method_col = 0
        self.different_column_types = {"# CFs": "num"}
        bd.projects.current_changed.connect(self.sync)

        # needed to trigger creation of self.filterable_columns, which relies on method_col existing
        self.sync()

    def get_method(self, proxy: QModelIndex) -> tuple:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), self.method_col]

    @Slot(tuple, name="filterOnMethod")
    def filter_on_method(self, method: tuple) -> None:
        query = ", ".join(method)
        self.sync(query)

    @Slot(name="syncTable")
    def sync(self, query=None) -> None:
        sorted_names = sorted([(", ".join(method), method) for method in bd.methods])
        if query:
            sorted_names = (m for m in sorted_names if query.lower() in m[0].lower())
        self._dataframe = pd.DataFrame(
            [self.build_row(method_obj) for method_obj in sorted_names],
            columns=self.HEADERS,
        )
        self.method_col = self._dataframe.columns.get_loc("method")
        self.filterable_columns = {
            col: i for i, col in enumerate(self.HEADERS) if i is not self.method_col
        }
        self.updated.emit()

    @staticmethod
    def build_row(method_obj) -> dict:
        method = bd.methods[method_obj[1]]
        return {
            "Name": method_obj[0],
            "Unit": method.get("unit", "Unknown"),
            "# CFs": str(method.get("num_cfs", 0)),
            "method": method_obj[1],
        }


class ImpactCategoryItem(TreeItem):
    """Item in MethodsTreeModel."""

    # this manual typing of COLUMNS below could be a risk later:
    # potential fix could be to get data from HEADERS in tables/impact_categories/MethodsTree
    def __init__(self, data: list, parent=None):
        super().__init__(data, parent)

    @classmethod
    def build_item(cls, impact_cat, parent: TreeItem) -> "ImpactCategoryItem":
        item = cls(list(impact_cat), parent)
        parent.appendChild(item)
        return item


class MethodsTreeModel(BaseTreeModel):
    """Tree model for impact categories.
    Tree is based on data in self._dataframe
    self.setup_model_data() initializes data format
    self._dataframe is converted to a nested dict, stored in self.tree_data
    self.tree_data can be queried during sync, pruning the tree
    finally, the ui side is built with self.build_tree()

    for tree nested dict format see self.nest_data()
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

        bd.projects.current_changed.connect(self.setup_and_sync)

    def flags(self, index):
        res = super().flags(index) | Qt.ItemIsDragEnabled
        return res

    def setup_and_sync(self) -> None:
        self.setup_model_data()
        self.sync()

    @Slot(name="clearSyncModel")
    @Slot(str, name="syncModel")
    def sync(self, query=None) -> None:
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

    def build_tree(self, data: dict, root: ImpactCategoryItem) -> None:
        """Assemble the tree ui."""
        for key, value in data.items():
            if isinstance(value, dict):
                # this is a root or branch node
                new_data = [key] + [""] * (self.columnCount() - 1)
                new_root = root.build_item(new_data, root)
                self.build_tree(value, new_root)
            else:
                # this is a leaf node
                ImpactCategoryItem.build_item(value, root)

    @Slot(name="methodsAltered")
    def setup_model_data(self) -> None:
        """Construct a dataframe of impact categories and a complete nested
        dict of the dataframe.

        Trigger this at init and when a method is added/deleted.
        """
        sorted_names = sorted([(", ".join(method), method) for method in bd.methods])
        self._dataframe = pd.DataFrame(
            [MethodsListModel.build_row(method_obj) for method_obj in sorted_names],
            columns=self.HEADERS,
        )
        self.method_col = self._dataframe.columns.get_loc("method")
        # get the complete nested dict for the dataframe:
        self.tree_data = self.nest_data(self._dataframe)

    # TODO this method performs additional work and while necessary for the current
    # TODO implementation provides no real benefit, an overhaul of the model data
    # TODO creation would be better
    @staticmethod
    def nest_data(df: pd.DataFrame, method: tuple = None) -> dict:
        """Convert impact category dataframe into nested dict format.
        Tree can have arbitrary amount (0 or more) levels of branch depth.

        Format is:
        {root1: {branch1: (data),
                          (data)},
                {branch2: {branch3: (data),
                                    (data)},
                          {branch4: (data),
                                    (data)},
                          (data)}}
        Where:
        root#  : top level category (str) e.g.: CML 2001
        branch#: sub level category (str) e.g.: climate change
                 can be arbitrary amount of branches
        data   : data (leaf node) of category (tuple) e.g.: ("GWP 100a",
                                                             "kg CO2-Eq",
                                                             160,
                                                             "('CML 2001', 'climate change', 'GWP 100a')")
                 Here each index of the tuple refers to the data in the self.HEADERS list of this class
        """
        data = np.empty(df.shape[0], dtype=object)

        for idx, row in enumerate(df.to_numpy(dtype=object)):
            split = list(row[3])  # convert tuple to list
            split.append(tuple(row))
            data[idx] = split
            # data is np 1d array (list) of each dataframe row

        # From https://stackoverflow.com/a/19900276 but changed -2 to -1
        #  this version is ~2 orders of magnitude faster than the pandas
        #  option in the same answer
        simple_dict = {}
        for row in data:
            # row is e.g.: ['CML 2001',
            #               'climate change',
            #               'GWP 100a',
            #               ('CML 2001, climate change, GWP 100a',
            #                'kg CO2-Eq',
            #                160,
            #                ('CML 2001',
            #                 'climate change',
            #                 'GWP 100a'))]
            # so: [str, str, str, tuple(str, str, str, tuple(str, str, str))]
            temp_row = list(
                row[-1]
            )  # temp_row = tuple(str, str, str, tuple(str, str, str))
            temp_row[0] = temp_row[-1][-1]  # in the example this would be 'GWP 100a'
            # temp_row[0] is taken from [-1][-1] and not from row[2] as there can be an arbitrary depth in the category

            new_row = tuple(temp_row)
            # new_row format: ('GWP 100a',
            #                  'kg CO2-Eq',
            #                  160,
            #                  ('CML 2001',
            #                   'climate change',
            #                   'GWP 100a'))
            # new_row is the leaf node, the format is based on self.HEADERS
            here = simple_dict
            for elem in row[:-2]:
                if elem not in here:
                    # add root or branch node if it doesn't exist yet
                    here[elem] = {}
                # otherwise append the root/branch
                here = here[elem]
            # finally, add the leaf node:
            here[row[-1]] = new_row
        return simple_dict

    def get_method(self, tree_level: tuple) -> tuple:
        """Retrieve method data"""
        name = tree_level[1]
        if tree_level[0] == "branch":
            return tuple(tree_level[1])
        if not isinstance(name, str):
            name = ", ".join(tree_level[1])
        else:
            return tuple([tree_level[1]])
        methods = self._dataframe.loc[self._dataframe["Name"] == name, "method"]
        return next(iter(methods))

    def get_methods(self, name: str) -> Iterator:
        methods = self._dataframe.loc[
            self._dataframe["Name"].str.startswith(name), "method"
        ]
        if self.query:
            queries = [
                method
                for method in methods
                if self.query.lower() in ", ".join(method).lower()
            ]
            return queries
        return methods

    @Slot(QModelIndex, name="deleteMethod")
    def delete_method(self, level: tuple) -> None:
        method = self.get_method(level)
        signals.delete_method.emit(method, level[0])

    @Slot(tuple, name="filterOnMethod")
    def filter_on_method(self, method: tuple) -> None:
        query = ", ".join(method)
        self.sync(query)

    @staticmethod
    def search_tree(tree: dict, query: str, matches: int = 0) -> (dict, int):
        """Search the tree and remove non-matching leaves and branches."""
        remove = []
        for key, value in tree.items():
            if isinstance(value, tuple):
                # this is a leaf node
                if query.lower() not in ", ".join(value[-1]).lower():
                    # the query does not match
                    remove.append(key)
                else:
                    matches += 1
            else:
                # this is not a leaf node
                if query.lower() not in key.lower():
                    # the query does not match, go deeper
                    sub_tree, matches = MethodsTreeModel.search_tree(
                        value, query, matches
                    )
                    if len(sub_tree) > 0:
                        # there were query matches in this branch
                        tree[key] = sub_tree
                    else:
                        # there were no query matches in this branch
                        remove.append(key)
                else:
                    matches += 1
        for key in remove:
            tree.pop(key)
        return tree, matches


class MethodCharacterizationFactorsModel(EditablePandasModel):
    COLUMNS = ["name", "categories", "amount", "unit"]
    HEADERS = ["Name", "Category", "Amount", "Unit", "Uncertainty"] + ["cf"]
    UNCERTAINTY = ["loc", "scale", "shape", "minimum", "maximum"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.cf_column = 0
        self.method = None
        self.different_column_types = {k: "num" for k in self.UNCERTAINTY + ["Amount"]}
        self.filterable_columns = {col: i for i, col in enumerate(self.HEADERS[:-1])}

    @property
    def uncertain_cols(self) -> list:
        return [self._dataframe.columns.get_loc(c) for c in self.UNCERTAINTY]

    def load(self, method):
        assert self.method is None, "CF Model already loaded"
        self.method = method
        self.method.changed.connect(self.sync)

        self.sync()

    def sync(self) -> None:
        assert self.method is not None, "A method must first be set using load()."
        if not self.method.registered:
            return  # the method was deleted, this table will soon be closed
        self._dataframe = pd.DataFrame(
            [self.build_row(obj) for obj in self.method.load()],
            columns=self.HEADERS + self.UNCERTAINTY,
        )
        self.cf_column = self._dataframe.columns.get_loc("cf")
        self.updated.emit()

    @classmethod
    def build_row(cls, method_cf: tuple) -> dict:
        key, amount = method_cf[:2]
        flow = bd.get_activity(tuple(key))
        row = {cls.HEADERS[i]: flow.get(c) for i, c in enumerate(cls.COLUMNS)}
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
        """Get the characterization factor data of the selected row."""
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), self.cf_column]

    def get_value(self, proxy: QModelIndex) -> float:
        """Get the value of the selected cell."""
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), idx.column()]

    def get_col_from_index(self, proxy: QModelIndex) -> str:
        """Get the name of the column of the selected cell."""
        idx = self.proxy_to_source(proxy)
        return self.COLUMNS[idx.column()]

    def set_filterable_columns(self, hide: bool) -> None:
        filterable_cols = {col: i for i, col in enumerate(self.HEADERS[:-1])}
        if not hide:
            # also add the uncertainty columns
            filterable_cols.update(
                {col: i for col, i in zip(self.UNCERTAINTY, self.uncertain_cols)}
            )
        self.filterable_columns = filterable_cols
