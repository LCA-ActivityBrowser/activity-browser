# -*- coding: utf-8 -*-
import datetime
import functools

import numpy as np
import pandas as pd
from PySide2.QtCore import Qt, QModelIndex, Slot
from PySide2.QtWidgets import QApplication

from activity_browser import log, project_settings
from activity_browser.mod.bw2data import projects, databases, utils
from activity_browser.bwutils import AB_metadata, commontasks as bc

from .base import PandasModel, DragPandasModel


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
            dt = datetime.datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S.%f')

            # final column includes interactive checkbox which shows read-only state of db
            database_read_only = project_settings.db_is_readonly(name)
            data.append({
                "Name": name,
                "Depends": ", ".join(databases[name].get("depends", [])),
                "Modified": dt,
                "Records": bc.count_database_records(name),
                "Read-only": database_read_only,
            })

        self._dataframe = pd.DataFrame(data, columns=self.HEADERS)
        self.updated.emit()


class ActivitiesBiosphereModel(DragPandasModel):
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
            log.debug("Pandas Dataframe passed to sync.", df.shape)
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

    def copy_exchanges_for_SDF(self, proxies: list) -> None:
        if len(proxies) > 1:
            keys = {self.get_key(p) for p in proxies}
        else:
            keys = {self.get_key(proxies[0])}
        QApplication.setOverrideCursor(Qt.WaitCursor)
        exchanges = bc.get_exchanges_from_a_list_of_activities(activities=list(keys),
                                                               as_keys=True)
        data = bc.get_exchanges_in_scenario_difference_file_notation(exchanges)
        df = pd.DataFrame(data)
        df.to_clipboard(excel=True, index=False)
        QApplication.restoreOverrideCursor()
