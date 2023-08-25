# -*- coding: utf-8 -*-
import datetime
import functools
from copy import deepcopy
from typing import Iterator, Optional
import os

import arrow
import brightway2 as bw
from bw2data.utils import natural_sort
import numpy as np
import pandas as pd
from PySide2.QtCore import Qt, QModelIndex, Slot
from PySide2.QtWidgets import QApplication

from activity_browser.bwutils import AB_metadata, commontasks as bc
from activity_browser.settings import project_settings
from activity_browser.signals import signals
from .base import PandasModel, DragPandasModel, TreeItem, BaseTreeModel

import logging
from activity_browser.logger import ABHandler

logger = logging.getLogger('ab_logs')
log = ABHandler.setup_with_logger(logger, __name__)


class DatabasesModel(PandasModel):
    HEADERS = ["Name", "Records", "Read-only", "Depends", "Modified"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        signals.project_selected.connect(self.sync)
        signals.databases_changed.connect(self.sync)

    def get_db_name(self, proxy: QModelIndex) -> str:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), 0]

    def sync(self):
        # code below is based on the assumption that bw uses utc timestamps
        tz = datetime.datetime.now(datetime.timezone.utc).astimezone()
        time_shift = - tz.utcoffset().total_seconds()

        data = []
        for name in natural_sort(bw.databases):
            dt = bw.databases[name].get("modified", "")
            if dt:
                dt = arrow.get(dt).shift(seconds=time_shift).humanize()
            # final column includes interactive checkbox which shows read-only state of db
            database_read_only = project_settings.db_is_readonly(name)
            data.append({
                "Name": name,
                "Depends": ", ".join(bw.databases[name].get("depends", [])),
                "Modified": dt,
                "Records": bc.count_database_records(name),
                "Read-only": database_read_only,
            })

        self._dataframe = pd.DataFrame(data, columns=self.HEADERS)
        self.updated.emit()


class ActivitiesBiosphereListModel(DragPandasModel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.act_fields = lambda: AB_metadata.get_existing_fields(["reference product", "name", "location", "unit", "ISIC rev.4 ecoinvent"])
        self.ef_fields = lambda: AB_metadata.get_existing_fields(["name", "categories", "type", "unit"])
        self.technosphere = True

    @property
    def fields(self) -> list:
        """ Constructs a list of fields relevant for the type of database.
        """
        return self.act_fields() if self.technosphere else self.ef_fields()

    def get_key(self, proxy: QModelIndex) -> tuple:
        """ Get the key from the model using the given proxy index"""
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), self._dataframe.columns.get_loc("key")]

    def clear(self) -> None:
        self._dataframe = pd.DataFrame([])
        self.updated.emit()

    def df_from_metadata(self, db_name: str) -> pd.DataFrame:
        """ Take the given database name and return the complete subset
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
        self.parent().horizontalHeader().setSortIndicator(sort_field_index, Qt.AscendingOrder)
        return df

    @Slot(str, name="syncModel")
    def sync(self, db_name: str, df: pd.DataFrame = None) -> None:
        if df is not None:
            # skip the rest of the sync here if a dataframe is directly supplied
            log.info("Pandas Dataframe passed to sync.", df.shape)
            self._dataframe = df
            self.updated.emit()
            return

        if db_name not in bw.databases:
            raise KeyError("This database does not exist!", db_name)
        self.database_name = db_name
        self.technosphere = bc.is_technosphere_db(db_name)

        # Get dataframe from metadata and update column-names
        QApplication.setOverrideCursor(Qt.WaitCursor)
        df = self.df_from_metadata(db_name)
        # remove empty columns
        df.replace('', np.nan, inplace=True)
        df.dropna(how='all', axis=1, inplace=True)
        self._dataframe = df.reset_index(drop=True)
        self.filterable_columns = {col: i for i, col in enumerate(self._dataframe.columns.to_list())}
        QApplication.restoreOverrideCursor()
        self.updated.emit()

    def search(self, pattern1: str = None, pattern2: str = None, logic='AND') -> None:
        """ Filter the dataframe with two filters and a logical element
        in between to allow different filter combinations.

        TODO: Look at the possibility of using the proxy model to filter instead
        """
        df = self.df_from_metadata(self.database_name)
        if all((pattern1, pattern2)):
            mask1 = self.filter_dataframe(df, pattern1)
            mask2 = self.filter_dataframe(df, pattern2)
            # applying the logic
            if logic == 'AND':
                mask = np.logical_and(mask1, mask2)
            elif logic == 'OR':
                mask = np.logical_or(mask1, mask2)
            elif logic == 'AND NOT':
                mask = np.logical_and(mask1, ~mask2)
        elif any((pattern1, pattern2)):
            mask = self.filter_dataframe(df, pattern1 or pattern2)
        else:
            self.sync(self.database_name)
            return
        df = df.loc[mask].reset_index(drop=True)
        self.sync(self.database_name, df=df)

    def filter_dataframe(self, df: pd.DataFrame, pattern: str) -> pd.Series:
        """ Filter the dataframe returning a mask that is True for all rows
        where a search string has been found.

        It is a "contains" type of search (e.g. "oal" would find "coal").
        It also works for columns that contain tuples (e.g. ('water', 'ocean'),
        and will match on partials i.e. both 'ocean' and 'ean' work.

        An alternative solution would be to use .str.contains, but this does
        not work for columns containing tuples (https://stackoverflow.com/a/29463757)
        """
        search_columns = (bc.bw_keys_to_AB_names.get(c, c) for c in self.fields)
        mask = functools.reduce(
            np.logical_or, [
                df[col].apply(lambda x: pattern.lower() in str(x).lower())
                for col in search_columns
            ]
        )
        return mask

    def delete_activities(self, proxies: list) -> None:
        if len(proxies) > 1:
            keys = [self.get_key(p) for p in proxies]
            signals.delete_activities.emit(keys)
        else:
            signals.delete_activity.emit(self.get_key(proxies[0]))

    def duplicate_activities(self, proxies: list) -> None:
        if len(proxies) > 1:
            keys = [self.get_key(p) for p in proxies]
            signals.duplicate_activities.emit(keys)
        else:
            signals.duplicate_activity.emit(self.get_key(proxies[0]))

    def duplicate_activity_to_new_loc(self, proxies: list) -> None:
        signals.duplicate_activity_new_loc.emit(self.get_key(proxies[0]))

    def duplicate_activities_to_db(self, proxies: list) -> None:
        if len(proxies) > 1:
            keys = [self.get_key(p) for p in proxies]
            signals.duplicate_to_db_interface_multiple.emit(keys, self.database_name)
        else:
            key = self.get_key(proxies[0])
            signals.duplicate_to_db_interface.emit(key, self.database_name)

    def copy_exchanges_for_SDF(self, proxies: list) -> None:
        if len(proxies) > 1:
            keys = [self.get_key(p) for p in proxies]
        else:
            keys = [self.get_key(proxies[0])]
        QApplication.setOverrideCursor(Qt.WaitCursor)
        exchanges = bc.get_exchanges_from_a_list_of_activities(activities=keys,
                                                               as_keys=True)
        data = bc.get_exchanges_in_scenario_difference_file_notation(exchanges)
        df = pd.DataFrame(data)
        df.to_clipboard(excel=True, index=False)
        QApplication.restoreOverrideCursor()


class ActivitiesBiosphereItem(TreeItem):
    """ Item in ActivitiesBiosphereTreeModel."""
    # this manual typing of COLUMNS below could be a risk later:
    # potential fix could be to get data from HEADERS in tables/inventory/ActivitiesBiosphereTree
    def __init__(self, data: list, parent=None):
        super().__init__(data, parent)

    @classmethod
    def build_item(cls, impact_cat, parent: TreeItem) -> 'ActivitiesBiosphereItem':
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
    HEADERS = ["reference product", "name", "location", "unit", "ISIC rev.4 ecoinvent"]

    def __init__(self, parent=None, database_name=None):
        super().__init__(parent)
        self.database_name = database_name
        self.HEADERS = AB_metadata.get_existing_fields(
            ["reference product", "name", "location", "unit", "ISIC rev.4 ecoinvent"])

        self.root = ActivitiesBiosphereItem.build_root(self.HEADERS)

        # All of the various variables.
        self._dataframe: Optional[pd.DataFrame] = None
        self.all_col = 0
        self.tree_data = None
        self.matches = None
        self.query = None

        self.ISIC_tree, self.ISIC_tree_codes, self.ISIC_order = self.get_isic_tree()
        self.setup_model_data()

        signals.project_selected.connect(self.setup_and_sync)

    def flags(self, index):
        res = super().flags(index) | Qt.ItemIsDragEnabled
        return res

    def get_isic_tree(self) -> dict:
        """Generate an entry for every class of the ISIC and store its path"""

        # this file is from https://unstats.un.org/unsd/classifications/Econ/isic
        # the file is structured such that each sub-class of the previous has 1 character more in column 'code'
        # that means each super-class is already seen before we get to the sub-class
        # we use that as a feature to create the 'tree path'
        path = os.path.join(os.getcwd(), "activity_browser", "static", "database_classifications",
                            "ISIC_Rev_4_english_structure.Txt")
        df = pd.read_csv(path)

        tree_data = {}
        tree_codes = {}
        tree_numeric_order = {}
        last_super = tuple()
        last_super_depth = 0
        for idx, row in df.iterrows():
            cls, name = row
            current_depth = len(cls)
            key = cls + ":" + name
            tree_codes[cls] = key
            tree_numeric_order[cls] = idx

            if current_depth > last_super_depth:
                # this is a sub-class at a deeper level as the last entry we read
                value = tuple(list(last_super) + [key])
            elif current_depth <= last_super_depth:
                # this is a (sub-)class at a same or higher level than the last entry we read
                depth = last_super_depth - current_depth + 1
                value = tuple(list(last_super)[:-depth] + [key])

            tree_data[key] = value
            last_super = value
            # take the last class level, split on ':' and take the length of the number
            last_super_depth = len(last_super[-1].split(":")[0])
        return tree_data, tree_codes, tree_numeric_order

    def setup_and_sync(self) -> None:
        self.setup_model_data()
        self.sync()

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

        Trigger this at init and when an activity is added/edited/deleted.
        """
        # Get dataframe from metadata and update column-names
        QApplication.setOverrideCursor(Qt.WaitCursor)
        df = self.df_from_metadata(self.database_name)
        # remove empty columns
        df.replace('', np.nan, inplace=True)
        df.dropna(how='all', axis=1, inplace=True)
        df['tree_order'] = df.apply(lambda row: self.tree_order(row), axis=1)
        df['tree_path_tuple'] = df.apply(lambda row: self.tree_path_tuple(row), axis=1)
        df = df.reset_index(drop=True)

        # Sort dataframe on column: 'product' and then on 'tree_order'
        sort_field = df.columns[0]
        df = df.iloc[df[sort_field].str.lower().argsort()]
        df = df.iloc[df['tree_order'].argsort()]
        del df['tree_order']
        self._dataframe = df

        self.path_col = self._dataframe.columns.get_loc("tree_path_tuple")

        # get the complete nested dict for the dataframe:
        self.tree_data = self.nest_data(self._dataframe)
        QApplication.restoreOverrideCursor()

    def df_from_metadata(self, db_name: str) -> pd.DataFrame:
        """ Take the given database name and return the complete subset
        of that database from the metadata.

        The fields are used to prune the dataset of unused columns.
        """
        df = AB_metadata.get_database_metadata(db_name)
        # New / empty database? Shortcut the sorting / structuring process
        if df.empty:
            return df
        df = df.loc[:, self.HEADERS + ["key"]]
        df.columns = [bc.bw_keys_to_AB_names.get(c, c) for c in self.HEADERS] + ["key"]
        return df

    def tree_order(self, row) -> int:
        """Give item order to row, if no class exists, move to lowest rank."""
        classification = row['ISIC rev.4 ecoinvent']
        if not isinstance(classification, str):
            # this is not a valid number, return high number (low rank)
            return 99999
        # match based on the actual number code, ignore letters or text
        class_code = classification.split(':')[0]
        if len(class_code) > 1 and not class_code[-1].isdigit():
            class_code = class_code[:-1]
        order = self.ISIC_order.get(class_code, 99999)
        return order

    def tree_path_tuple(self, row) -> tuple:
        """Convert the row to a tuple"""
        classification = row['ISIC rev.4 ecoinvent']
        if not isinstance(classification, str):
            # this is not a valid number, return 'No classification'
            return tuple(list(('No classification',)) + [row['Product']])
        # match based on the actual number code, ignore letters or text
        class_code = classification.split(':')[0]
        if len(class_code) > 1 and not class_code[-1].isdigit():
            class_code = class_code[:-1]
        classification = self.ISIC_tree_codes.get(class_code, ('No classification',))
        tup = self.ISIC_tree[classification]
        tup = tuple(list(tup) + [row['Product']])
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
            split = list(row[-1])  # convert tuple to list
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
            temp_row = list(row[-1])  # temp_row = tuple(str, str, str, tuple(str, str, str))

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

    def get_activity(self, tree_level: tuple) -> tuple:
        """Retrieve method data"""
        name = tree_level[1]
        if tree_level[0] == 'branch':
            return tuple(tree_level[1])
        if not isinstance(name, str):
            name = ", ".join(tree_level[1])
        else:
            return tuple([tree_level[1]])
        methods = self._dataframe.loc[self._dataframe["Name"] == name, "method"]
        return next(iter(methods))

    def get_activities(self, name: str) -> Iterator:
        methods = self._dataframe.loc[self._dataframe["Name"].str.startswith(name), "method"]
        if self.query:
            queries = [
                method for method in methods
                if self.query.lower() in ', '.join(method).lower()
            ]
            return queries
        return methods

    def search_tree(self, query: str) -> dict:
        """Search the dataframe on the query and return a new nested tree."""

        df = deepcopy(self._dataframe)
        mask = functools.reduce(
            np.logical_or, [
                df[col].apply(lambda x: query.lower() in str(x).lower())
                for col in df.columns
            ]
        )
        return self.nest_data(df.loc[mask].reset_index(drop=True)), len(df)