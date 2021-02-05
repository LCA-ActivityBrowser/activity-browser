# -*- coding: utf-8 -*-
import numpy as np

from .base import PandasModel


class LCAResultsModel(PandasModel):
    def sync(self, df):
        self._dataframe = df.replace(np.nan, '', regex=True)
        self.refresh_model()


class InventoryModel(PandasModel):
    def sync(self, df):
        self._dataframe = df
        self.refresh_model()


class ContributionModel(PandasModel):
    def sync(self, df):
        self._dataframe = df.replace(np.nan, '', regex=True)
        self.refresh_model()
