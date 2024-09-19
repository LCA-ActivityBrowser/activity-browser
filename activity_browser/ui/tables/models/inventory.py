# -*- coding: utf-8 -*-
import datetime
import functools
from copy import deepcopy
from typing import Optional
import os
from typing import Tuple
from logging import getLogger

import numpy as np
import pandas as pd
from PySide2.QtCore import QModelIndex, Qt, Slot
from PySide2.QtWidgets import QApplication

import activity_browser
from activity_browser import project_settings
from activity_browser.bwutils import AB_metadata
from activity_browser.bwutils import commontasks as bc
from activity_browser.mod.bw2data import databases, projects, utils

from .base import PandasModel, DragPandasModel, TreeItem, BaseTreeModel

log = getLogger(__name__)


class DatabasesModel(PandasModel):
    HEADERS = ["Name", "Records", "Read-only", "Depends", "Modified"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        projects.current_changed.connect(self.sync)
        databases.metadata_changed.connect(self.sync)

    def get_db_name(self, proxy: QModelIndex) -> str:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), 0]

    def sync(self):
        data = []
        for name in utils.natural_sort(databases):
            # get the modified time, in case it doesn't exist, just write 'now' in the correct format
            dt = databases[name].get("modified", datetime.datetime.now().isoformat())
            dt = datetime.datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S.%f")

            # final column includes interactive checkbox which shows read-only state of db
            database_read_only = project_settings.db_is_readonly(name)
            data.append(
                {
                    "Name": name,
                    "Depends": ", ".join(databases[name].get("depends", [])),
                    "Modified": dt,
                    "Records": bc.count_database_records(name),
                    "Read-only": database_read_only,
                }
            )

        self._dataframe = pd.DataFrame(data, columns=self.HEADERS)
        self.updated.emit()


class ActivitiesBiosphereListModel(DragPandasModel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.act_fields = lambda: AB_metadata.get_existing_fields(
            ["reference product", "name", "location", "unit", "ISIC rev.4 ecoinvent"]
        )
        self.ef_fields = lambda: AB_metadata.get_existing_fields(
            ["name", "categories", "type", "unit"]
        )
        self.technosphere = True

        self.query = None

    @property
    def fields(self) -> list:
        """Constructs a list of fields relevant for the type of database."""
        return self.act_fields() if self.technosphere else self.ef_fields()

    def get_key(self, proxy: QModelIndex) -> tuple:
        """Get the key from the model using the given proxy index"""
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), self._dataframe.columns.get_loc("key")]

    def clear(self) -> None:
        self._dataframe = pd.DataFrame([])
        self.updated.emit()

    def df_from_metadata(self, db_name: str) -> pd.DataFrame:
        """Take the given database name and return the complete subset
        of that database from the metadata.

        The fields are used to prune the dataset of unused columns.
        """
        df = AB_metadata.get_database_metadata(db_name)
        # New / empty database? Shortcut the sorting / structuring process
        if df.empty:
            return df
        df = df.loc[:, self.fields + ["key"]]
        df.columns = [bc.bw_keys_to_AB_names.get(c, c) for c in self.fields] + ["key"]

        # Sort dataframe on first column (activity name, usually)
        # while ignoring case sensitivity
        sort_field = df.columns[0]
        df = df.iloc[df[sort_field].str.lower().argsort()]
        sort_field_index = df.columns.to_list().index(sort_field)
        self.parent().horizontalHeader().setSortIndicator(
            sort_field_index, Qt.AscendingOrder
        )
        return df

    @Slot(str, name="syncModel")
    def sync(self, db_name: str, df: pd.DataFrame = None, query=None) -> None:
        self.query = query

        if df is not None:
            # skip the rest of the sync here if a dataframe is directly supplied
            log.debug("Pandas Dataframe passed to sync.")
            self._dataframe = df
            self.updated.emit()
            return

        if db_name not in databases:
            return
        self.database_name = db_name
        self.technosphere = bc.is_technosphere_db(db_name)

        # Get dataframe from metadata and update column-names
        QApplication.setOverrideCursor(Qt.WaitCursor)
        df = self.df_from_metadata(db_name)

        if query:
            # apply query if present
            mask = self.filter_dataframe(df, query)
            df = df.loc[mask].reset_index(drop=True)

        # remove empty columns
        df.replace("", np.nan, inplace=True)
        df.dropna(how="all", axis=1, inplace=True)
        self._dataframe = df.reset_index(drop=True)
        self.filterable_columns = {
            col: i for i, col in enumerate(self._dataframe.columns.to_list())
        }
        QApplication.restoreOverrideCursor()
        self.updated.emit()

    def search(self, pattern: str = None) -> None:
        """Filter the dataframe with pattern."""
        self.sync(self.database_name, query=pattern)

    def filter_dataframe(self, df: pd.DataFrame, pattern: str) -> pd.Series:
        """Filter the dataframe returning a mask that is True for all rows
        where a search string has been found.

        It is a "contains" type of search (e.g. "oal" would find "coal").
        It also works for columns that contain tuples (e.g. ('water', 'ocean'),
        and will match on partials i.e. both 'ocean' and 'ean' work.

        An alternative solution would be to use .str.contains, but this does
        not work for columns containing tuples (https://stackoverflow.com/a/29463757)
        """
        search_columns = (bc.bw_keys_to_AB_names.get(c, c) for c in self.fields)
        mask = functools.reduce(
            np.logical_or,
            [
                df[col].apply(lambda x: pattern.lower() in str(x).lower())
                for col in search_columns
            ],
        )
        return mask

    def copy_exchanges_for_SDF(self, proxies: list) -> None:
        if len(proxies) > 1:
            keys = {self.get_key(p) for p in proxies}
        else:
            keys = {self.get_key(proxies[0])}
        QApplication.setOverrideCursor(Qt.WaitCursor)
        exchanges = bc.get_exchanges_from_a_list_of_activities(
            activities=list(keys), as_keys=True
        )
        data = bc.get_exchanges_in_scenario_difference_file_notation(exchanges)
        df = pd.DataFrame(data)
        df.to_clipboard(excel=True, index=False)
        QApplication.restoreOverrideCursor()


class ActivitiesBiosphereItem(TreeItem):
    """Item in ActivitiesBiosphereTreeModel."""

    # this manual typing of COLUMNS below could be a risk later:
    # potential fix could be to get data from HEADERS in tables/inventory/ActivitiesBiosphereTree
    def __init__(self, data: list, parent=None):
        super().__init__(data, parent)

    @classmethod
    def build_item(cls, impact_cat, parent: TreeItem) -> "ActivitiesBiosphereItem":
        item = cls(list(impact_cat), parent)
        parent.appendChild(item)
        return item


class ActivitiesBiosphereTreeModel(BaseTreeModel):
    """Tree model for activities in a database.
    Tree is based on data in self._dataframe
    self.setup_model_data() initializes data format
    self._dataframe is converted to a nested dict, stored in self.tree_data
    self.tree_data can be queried during sync, pruning the tree
    finally, the ui side is built with self.build_tree()

    for tree nested dict format see self.nest_data()
    """

    HEADERS = [
        "reference product",
        "name",
        "location",
        "unit",
        "ISIC rev.4 ecoinvent",
        "key",
    ]

    def __init__(self, parent=None, database_name=None):
        super().__init__(parent)
        self.database_name = database_name
        self.HEADERS = AB_metadata.get_existing_fields(self.HEADERS)

        self.root = ActivitiesBiosphereItem.build_root(self.HEADERS)

        # all of the various variables.
        self._dataframe: Optional[pd.DataFrame] = None
        self.tree_data = None
        self.matches = None
        self.query = None

        self.ISIC_tree, self.ISIC_tree_codes, self.ISIC_order = self.get_isic_tree()
        self.setup_model_data()

    def flags(self, index):
        res = super().flags(index) | Qt.ItemIsDragEnabled
        return res

    def get_isic_tree(self) -> Tuple[dict, dict, dict]:
        """Generate an entry for every class of the ISIC and store its path.

        this file is from https://unstats.un.org/unsd/classifications/Econ/isic
        stored locally under path variable below
        the file is sorted and structured such that each sub-class of the previous has 1 character more in column
        'code', that means each super-class is already seen before we get to the sub-class
        we use that as a feature to create the 'tree path'

        Returns
        -------
        tuple: A tuple of 3 dicts
            tree_data: keys are str of classification:name, values are the tree path consisting of keys
            tree_codes: keys are classification number, values are the full keys
            tree_numeric_order: keys are classification number, values are the row number in file
        """
        path = os.path.join(
            os.path.dirname(os.path.abspath(activity_browser.__file__)),
            "static",
            "database_classifications",
            "ISIC_Rev_4_english_structure.txt",
        )

        df = pd.read_csv(path)

        tree_data = {}
        tree_codes = {}
        tree_numeric_order = {}
        last_super = tuple()
        last_super_depth = 0
        for idx, row in df.iterrows():
            cls, name = row  # cls is the number classification, name is the proper name
            current_depth = len(cls)  # we measure the depth by the length of cls
            key = f"{cls}:{name}"
            tree_codes[cls] = key  # add the full key to the classification cls in dict
            tree_numeric_order[cls] = (
                idx  # add the row number to the classification cls in dict
            )

            if current_depth > last_super_depth:
                # this is a sub-class at a deeper level as the last entry we read
                path = tuple(
                    list(last_super) + [key]
                )  # create a tuple of the tree path
            elif current_depth <= last_super_depth:
                # this is a (sub-)class at a same or higher level than the last entry we read
                depth = (
                    last_super_depth - current_depth + 1
                )  # find how many entries to clip of the path
                path = tuple(
                    list(last_super)[:-depth] + [key]
                )  # create a tuple of the tree path

            tree_data[key] = path  # add the treepath to the key in dict
            last_super = path  # add as last_super

            # take the last class level, split on ':' and take the length of the class as depth
            last_super_depth = len(last_super[-1].split(":")[0])
        return tree_data, tree_codes, tree_numeric_order

    def setup_and_sync(self) -> None:
        self.setup_model_data()
        self.sync(self.query)

    @Slot(name="clearSyncModel")
    @Slot(str, name="syncModel")
    def sync(self, query=None) -> None:
        self.beginResetModel()
        self.root.clear()
        self.query = query
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if self.query:
            self._data, self.matches = self.search_tree(self.query)
        else:
            self._data = self.tree_data
        self.build_tree(self._data, self.root)
        self.endResetModel()
        QApplication.restoreOverrideCursor()
        self.updated.emit()

    def build_tree(self, data: dict, root: ActivitiesBiosphereItem) -> None:
        """Assemble the tree ui."""
        for key, value in data.items():
            if isinstance(value, dict):
                # this is a root or branch node
                new_data = [key] + [""] * (self.columnCount() - 1)
                new_root = root.build_item(new_data, root)
                self.build_tree(value, new_root)
            else:
                # this is a leaf node
                ActivitiesBiosphereItem.build_item(value, root)

    @Slot(name="activitiesAltered")
    def setup_model_data(self) -> None:
        """Construct a dataframe of activities and a complete nested
        dict of the dataframe.

        Run this at init and when an activity is added/edited/deleted.
        """
        # Get dataframe from metadata and update column-names
        df = self.df_from_metadata(self.database_name)

        QApplication.setOverrideCursor(Qt.WaitCursor)
        # remove empty columns
        df.replace("", np.nan, inplace=True)
        df.dropna(how="all", axis=1, inplace=True)
        df["tree_order"] = df.apply(lambda row: self.tree_order(row), axis=1)
        df["tree_path_tuple"] = df.apply(lambda row: self.tree_path_tuple(row), axis=1)
        df = df.reset_index(drop=True)

        # Sort dataframe on column: 'product' and then on 'tree_order'
        sort_field = df.columns[0]
        df = df.iloc[df[sort_field].str.lower().argsort()]
        df = df.iloc[df["tree_order"].argsort()]
        del df["tree_order"]
        self._dataframe = df

        self.path_col = self._dataframe.columns.get_loc("tree_path_tuple")

        # get the complete nested dict for the dataframe:
        self.tree_data = self.nest_data(self._dataframe)
        QApplication.restoreOverrideCursor()

    def df_from_metadata(self, db_name: str) -> pd.DataFrame:
        """Take the given database name and return the complete subset
        of that database from the metadata.

        The fields are used to prune the dataset of unused columns.
        """
        df = AB_metadata.get_database_metadata(db_name)
        # New / empty database? Shortcut the sorting / structuring process
        if df.empty:
            return df
        df = df.loc[:, self.HEADERS]
        df.columns = [bc.bw_keys_to_AB_names.get(col, col) for col in self.HEADERS]
        return df

    def tree_order(self, row) -> int:
        """Give item order to row, if no class exists, move to lowest rank."""
        classification = row["ISIC rev.4 ecoinvent"]
        if not isinstance(classification, str):
            # this is not a valid number, return high number (low rank)
            return 99999
        # match based on the actual number code, ignore letters or text
        class_code = classification.split(":")[0]  # take only class code
        if len(class_code) > 1 and not class_code[-1].isdigit():
            class_code = class_code[:-1]  # only read the numeric part of the code
        order = self.ISIC_order.get(
            class_code, 99999
        )  # get the row number from the ISIC file for this class
        return order

    def tree_path_tuple(self, row) -> tuple:
        """Convert the row to a tuple"""
        classification = row["ISIC rev.4 ecoinvent"]
        if not isinstance(classification, str):
            # this is not a valid number, return 'No classification'
            return tuple(list(("No classification",)) + [row["Product"]])
        # match based on the actual number code, ignore letters or text
        class_code = classification.split(":")[0]
        if len(class_code) > 1 and not class_code[-1].isdigit():
            class_code = class_code[:-1]
        classification = self.ISIC_tree_codes.get(class_code, ("No classification",))
        tup = self.ISIC_tree[classification]
        tup = tuple(list(tup) + [row["Product"]])
        return tup

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
        root#  : top level category (str) e.g.: A:Agriculture, forestry and fishing
        branch#: sub level category (str) e.g.: 01:Crop and animal production, hunting and related service activities
                 can be arbitrary amount of branches
        data   : data (leaf node) of category (tuple) e.g.: ("A:Agriculture, forestry and fishing",
                                                             "01:Crop and animal production, hunting and related service activities",
                                                             [...],
                                                             "0111:Growing of cereals (except rice), leguminous crops and oil seeds"
                                                             <activity data as tuple>)
                 Here each index of the tuple refers to the data in the self.HEADERS list of this class
        """
        data = np.empty(
            df.shape[0], dtype=object
        )  # create 1D np.array with same len as input df

        for idx, row in enumerate(df.to_numpy(dtype=object)):
            split = list(row[-1])  # convert tuple to list
            split.append(tuple(row))
            data[idx] = (
                split  # the split is a list of 2 items, 0) the tree path and 1) the complete row data
            )

        # From https://stackoverflow.com/a/19900276 but changed -2 to -1
        #  this version is ~2 orders of magnitude faster than the pandas
        #  option in the same answer
        simple_dict = {}
        for row in data:
            # e.g. use this as example: ['A:Agriculture, forestry and fishing', '01:Crop and animal production, hunting and related service activities', '011:Growing of non-perennial crops', '0111:Growing of cereals (except rice), leguminous crops and oil seeds', 'sweet corn', ('sweet corn', 'sweet corn production', 'US', 'kilogram', '0111:Growing of cereals (except rice), leguminous crops and oil seeds', ('cutoff38', '4e26f787e6b76f2bbcb72e2ec1318f8a'), ('A:Agriculture, forestry and fishing', '01:Crop and animal production, hunting and related service activities', '011:Growing of non-perennial crops', '0111:Growing of cereals (except rice), leguminous crops and oil seeds', 'sweet corn'))]
            # row is e.g.: ['A:Agriculture, forestry and fishing',
            #               [...],
            #               '0111:Growing of cereals (except rice), leguminous crops and oil seeds',
            #               'sweet corn',
            #               ('sweet corn',
            #                'sweet corn production',
            #                'US',
            #                'kilogram',
            #                '0111:Growing of cereals (except rice), leguminous crops and oil seeds',
            #                ('cutoff38', '4e26f787e6b76f2bbcb72e2ec1318f8a'),
            #                <repeat of entire path as tuple>)]
            # so: [str, [...], str, tuple(str, str, str, str, str, tuple(str, str), tuple(str, [...], str))]
            new_row = tuple(row[-1])  # activity data

            # new_row is the leaf node, the format is based on self.HEADERS
            here = simple_dict
            for elem in row[:-2]:  # iterate over the full treepath
                if elem not in here:
                    # add root or branch node if it doesn't exist yet
                    here[elem] = {}
                # append the root/branch
                here = here[elem]
            # finally, add the leaf node:
            here[row[-1]] = new_row
        return simple_dict

    def get_keys(self, tree_path: str) -> list:
        """Get all the keys under the selected root/branch."""
        # apply search on the tree_path to get all activities
        filtered_df = self.search_df(tree_path, cols=["tree_path_tuple"])
        # apply any actual search queries if active
        if self.query:
            filtered_df = self.search_df(self.query, df=filtered_df)
        keys = filtered_df["key"].tolist()
        return keys

    def search_df(
        self, query: str, cols: list = None, df: pd.DataFrame = None
    ) -> pd.DataFrame:
        """Search DataFrame (default: self._dataframe) on query (optional: specify cols) and return filtered dataframe.

        Parameters
        ----------
        query: query string
        cols: optional, limited set of columns to search in
        df: optional, if given, search this df, otherwise, search self._dataframe

        Returns
        -------
        df: the filtered dataframe

        """
        if not isinstance(df, pd.DataFrame):
            df = deepcopy(self._dataframe)
        cols = cols or df.columns
        mask = functools.reduce(
            np.logical_or,
            [df[col].apply(lambda x: query.lower() in str(x).lower()) for col in cols],
        )
        return df.loc[mask].reset_index(drop=True)

    def search_tree(self, query: str) -> Tuple[dict, int]:
        """Search self._dataframe on query and return a nested tree and amt of hits.

        Parameters
        ----------
        query: query string

        Returns
        -------
        nested tree and how many hits were found

        """
        df = self.search_df(query)
        return self.nest_data(df), len(df)

    def copy_exchanges_for_SDF(self, keys: list) -> None:
        QApplication.setOverrideCursor(Qt.WaitCursor)
        exchanges = bc.get_exchanges_from_a_list_of_activities(
            activities=keys, as_keys=True
        )
        data = bc.get_exchanges_in_scenario_difference_file_notation(exchanges)
        df = pd.DataFrame(data)
        df.to_clipboard(excel=True, index=False)
        QApplication.restoreOverrideCursor()
