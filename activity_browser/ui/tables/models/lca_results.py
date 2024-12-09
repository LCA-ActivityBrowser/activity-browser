# -*- coding: utf-8 -*-
import numpy as np

from .base import PandasModel


class LCAResultsModel(PandasModel):
    def sync(self, df):
        self._dataframe = df.replace(np.nan, "", regex=True)
        self.updated.emit()


class InventoryModel(PandasModel):
    def sync(self, df):
        self._dataframe = df
        # set the visible columns
        self.filterable_columns = {
            col: i for i, col in enumerate(self._dataframe.columns.to_list())
        }
        # set the columns te be defined as num (all except the first five for both biopshere and technosphere
        self.different_column_types = {
            col: "num"
            for i, col in enumerate(self._dataframe.columns.to_list())
            if i >= 5
        }
        self.updated.emit()


class ContributionModel(PandasModel):
    def sync(self, df, unit="relative share"):

        if "unit" in df.columns:
            # overwrite the unit col with 'relative share' if looking at relative results (except 3 'total' and 'rest' rows)
            df["unit"] = [""] * 3 + [unit] * (len(df) - 3)

        # drop any rows where all numbers are 0
        self._dataframe = df.loc[~(df.select_dtypes(include=np.number) == 0).all(axis=1)]
        self.updated.emit()
