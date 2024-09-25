# -*- coding: utf-8 -*-
import datetime
import functools
from typing import Any, Optional

from PySide2.QtGui import QFont
import numpy as np
import pandas as pd
from PySide2.QtCore import QModelIndex, Qt, Slot
from PySide2.QtWidgets import QApplication

from activity_browser import log, project_settings
from activity_browser.actions.database.database_redo_allocation import DatabaseRedoAllocation
from activity_browser.bwutils import AB_metadata
from activity_browser.bwutils import commontasks as bc
from activity_browser.mod.bw2data import databases, projects
from activity_browser.ui.style import style_item
from activity_browser.ui.widgets.custom_allocation_editor import CustomAllocationEditor

from .base import DragPandasModel, EditablePandasModel, PandasModel


class DatabasesModel(EditablePandasModel):
    HEADERS = ["Name", "Records", "Read-only", "Depends", "Def. Alloc.", "Modified"]
    UNSPECIFIED_ALLOCATION = "(unspecified)"
    CUSTOM_ALLOCATION = "Custom..."
    NOT_APPLICABLE = "Not applicable"

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        projects.current_changed.connect(self.sync)
        databases.metadata_changed.connect(self.sync)
        self.dataChanged.connect(self._handle_data_changed)

    def get_db_name(self, proxy: QModelIndex) -> str:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), 0]

    def sync(self):
        self.beginResetModel()
        data = []
        for name in databases:
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
                    "Def. Alloc.": self._get_alloc_value(name),
                }
            )

        self._dataframe = pd.DataFrame(data, columns=self.HEADERS)
        self.endResetModel()

    @staticmethod
    def _get_alloc_value(db_name: str) -> str:
        if databases[db_name].get("backend") != "multifunctional":
            return DatabasesModel.NOT_APPLICABLE
        return databases[db_name].get("default_allocation",
                                      DatabasesModel.UNSPECIFIED_ALLOCATION)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Only allow editing of rows where the read-only flag is not set."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        read_only = self._dataframe.iat[index.row(), 2]
        multifunctional = self._dataframe.iat[index.row(), 4] != self.NOT_APPLICABLE
        # Skip the EditablePandasModel.flags() because it always returns the editable
        # flag
        result = PandasModel.flags(self, index)
        if not read_only and multifunctional:
            result |= Qt.ItemIsEditable
        return result

    def data(self, index: QModelIndex,
             role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        result = super().data(index, role)
        if index.isValid() and index.column() == 4:
            if role == Qt.ItemDataRole.DisplayRole and result is None:
                return self.UNSPECIFIED_ALLOCATION
            elif role == Qt.ItemDataRole.FontRole:
                if index.data() != self.NOT_APPLICABLE:
                    font = QFont()
                    font.setUnderline(True)
                    return font
            elif role == Qt.ItemDataRole.ForegroundRole:
                if index.data() != self.NOT_APPLICABLE:
                    return style_item.brushes["hyperlink"]
        return result

    def _handle_data_changed(self, top_left: QModelIndex, bottom_right: QModelIndex, roles: list[Qt.ItemDataRole]):
        if top_left.isValid() and bottom_right.isValid():
            # Default allocation column
            if top_left.column() <= 4 <= bottom_right.column():
                for row in range(top_left.row(), bottom_right.row() + 1):
                    current_alloc_idx = self.index(row, 4)
                    current_db = self.data(self.index(row, 0))
                    if self.data(current_alloc_idx) == self.UNSPECIFIED_ALLOCATION:
                        if databases[current_db].get("default_allocation") is not None:
                            del databases[current_db]["default_allocation"]
                    elif self.data(current_alloc_idx) == self.CUSTOM_ALLOCATION:
                        current = databases[current_db].get("default_allocation", "")
                        custom_value = CustomAllocationEditor.define_custom_allocation(
                            current, current_db, self.parent()
                        )
                        if custom_value != current:
                            databases[current_db]["default_allocation"] = custom_value
                        # No need to reset the "Custom..." value in the cell, because the
                        # flush below will trigger a refresh of the table from the persistent
                        # data
                    else:
                        databases[current_db]["default_allocation"] = self.data(current_alloc_idx)
                databases.flush()
                DatabaseRedoAllocation.run(current_db)

    def show_custom_allocation_editor(self, proxy: QModelIndex):
        if proxy.isValid() and proxy.column() == 4:
            current_db = proxy.siblingAtColumn(0).data()
            current_allocation = databases[current_db].get("default_allocation", "")
            custom_value = CustomAllocationEditor.define_custom_allocation(
                current_allocation, current_db, self.parent()
            )
            if custom_value != current_allocation:
                # In this approach there is no way currently to delete the
                # default_allocation completely
                databases[current_db]["default_allocation"] = custom_value
                databases.flush()
                DatabaseRedoAllocation.run(current_db)


class ActivitiesBiosphereModel(DragPandasModel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.database_name = ""
        self._visible_columns = []
        self.technosphere = True

    @property
    def _tentative_fields(self) -> list[str]:
        """
        We try to display these columns, but some might not be available, and
        some might be empty and later filtered out.
        """
        return AB_metadata.get_existing_fields(
            ["name", "reference product", "location", "unit",
             "ISIC rev.4 ecoinvent", "type", "key"]
        )

    @property
    def _tentative_columns(self) -> list[str]:
        """Return the list of titles for each tentative column"""
        # Create a local dict to avoid changing AB_names_to_bw_keys
        # We can not hardcode column names, because some might be filtered out
        # by AB_metadata.get_existing_fields above.
        column_names = {
            "name": "Name",
            "reference product": "Ref. product",
            "location": "Location",
            "unit": "Unit",
            "ISIC rev.4 ecoinvent": "ISIC rev.4 ecoinvent",
            "type": "Type",
            "key": "key",
        }
        return  [column_names[field] for field in self._tentative_fields]

    def columnCount(self, parent=None, *args, **kwargs):
        # Hide the key column, but keep the data to be able to open activities
        return 0 if self._dataframe is None else max(0, self._dataframe.shape[1] - 1)

    def get_key(self, proxy: QModelIndex) -> tuple:
        """Get the key from the model using the given proxy index"""
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), self._dataframe.columns.get_loc("key")]

    def clear(self) -> None:
        self._dataframe = pd.DataFrame([])
        self.updated.emit()

    @staticmethod
    def _remove_empty_columns(df: pd.DataFrame) -> pd.DataFrame:
        # Iterate over all the values instead of replacing empty strings
        # with np.nan and then dropping all empty columns. That solution has a
        # side effect, that in columns with some empty values sorting will break.
        # This solution is also slightly faster on the test databases.
        remove_cols = []
        for col in df.columns:
            if all((x == "" or x == np.nan for x in df[col])):
                remove_cols.append(col)
        df.drop(remove_cols, axis=1, inplace=True)
        return df.reset_index(drop=True)

    def df_from_metadata(self, db_name: str) -> pd.DataFrame:
        """Take the given database name and return the complete subset
        of that database from the metadata.

        The fields are used to prune the dataset of unused columns.
        """
        df = AB_metadata.get_database_metadata(db_name)
        # New / empty database? Shortcut the sorting / structuring process
        if df.empty:
            return df
        df = df.loc[:, self._tentative_fields]
        df.columns = self._tentative_columns

        # Sort dataframe on first column (activity name, usually)
        # while ignoring case sensitivity
        sort_field = df.columns[0]
        df = df.iloc[df[sort_field].str.lower().argsort()]
        sort_field_index = df.columns.to_list().index(sort_field)
        self.parent().horizontalHeader().setSortIndicator(
            sort_field_index, Qt.AscendingOrder
        )
        return self._remove_empty_columns(df)

    @Slot(str, name="syncModel")
    def sync(self, db_name: str, df: Optional[pd.DataFrame] = None) -> None:
        if df is not None:
            # skip the rest of the sync here if a dataframe is directly supplied
            log.debug("Pandas Dataframe passed to sync.", df.shape)
            # Remove the empty columns in a separate step, so that in case of empty
            # cells the search does not operate on str(nan) values, but empty strings
            self._dataframe = df
            self.updated.emit()
            return

        if db_name not in databases:
            return
        self.database_name = db_name

        # Get dataframe from metadata and update column-names
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self._dataframe = self.df_from_metadata(db_name)
        # Calculate visible columns after empty columns have been removed
        self._visible_columns = list(self._dataframe.columns)
        if "key" in self._visible_columns:
            # Empty databases have no columns
            self._visible_columns.remove("key")
        self.filterable_columns = {
            col: i for i, col in enumerate(self._visible_columns)
        }
        QApplication.restoreOverrideCursor()
        self.updated.emit()

    def search(self, pattern1: str = None, pattern2: str = None, logic="AND") -> None:
        """Filter the dataframe with two filters and a logical element
        in between to allow different filter combinations.

        TODO: Look at the possibility of using the proxy model to filter instead
        """
        df = self.df_from_metadata(self.database_name)
        if all((pattern1, pattern2)):
            mask1 = self.filter_dataframe(df, pattern1)
            mask2 = self.filter_dataframe(df, pattern2)
            # applying the logic
            if logic == "AND":
                mask = np.logical_and(mask1, mask2)
            elif logic == "OR":
                mask = np.logical_or(mask1, mask2)
            elif logic == "AND NOT":
                mask = np.logical_and(mask1, ~mask2)
        elif any((pattern1, pattern2)):
            mask = self.filter_dataframe(df, pattern1 or pattern2)
        else:
            self.sync(self.database_name)
            return
        df = df.loc[mask].reset_index(drop=True)
        self.sync(self.database_name, df=df)

    def filter_dataframe(self, df: pd.DataFrame, pattern: str) -> pd.Series:
        """Filter the dataframe returning a mask that is True for all rows
        where a search string has been found.

        It is a "contains" type of search (e.g. "oal" would find "coal").
        It also works for columns that contain tuples (e.g. ('water', 'ocean'),
        and will match on partials i.e. both 'ocean' and 'ean' work.

        An alternative solution would be to use .str.contains, but this does
        not work for columns containing tuples (https://stackoverflow.com/a/29463757)
        """
        mask = functools.reduce(
            np.logical_or,
            [
                df[col].apply(lambda x: pattern.lower() in str(x).lower())
                for col in self._visible_columns
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
