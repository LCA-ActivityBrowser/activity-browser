# -*- coding: utf-8 -*-
import itertools
from typing import List

import pandas as pd

from .activities import fill_df_keys_with_fields
from .utils import SUPERSTRUCTURE, EXCHANGE_KEYS


class SuperstructureManager(object):
    """A combination of methods used to manipulate and transform superstructures."""
    def __init__(self, df: pd.DataFrame, *dfs: pd.DataFrame):
        # Prepare dataframes for further processing
        self.frames: List[pd.DataFrame] = [
            SuperstructureManager.remove_duplicates(df)
        ] + [SuperstructureManager.remove_duplicates(f) for f in dfs]
        self.is_multiple = len(self.frames) > 1

    def combined_data(self, kind: str = "product") -> pd.DataFrame:
        """Combines multiple superstructures using a specific kind of logic.

        Currently implemented: 'product' creates an outer-product combination
        from all of the columns of the dataframes and injects values from all
        the frames for their specific indexes, any shared indexes are overridden
        where the later dataframes have preference.

        Uses parts of https://stackoverflow.com/a/45286061

        If only a single dataframe is given to the manager, return this dataframe instead.
        """
        if not self.is_multiple:
            df = next(iter(self.frames))
            cols = df.columns.difference(SUPERSTRUCTURE, sort=False)
            return pd.DataFrame(
                data=df.loc[:, cols], index=df.index, columns=cols
            )
        combo_idx = self._combine_indexes()

        if kind == "product":
            combo_cols = self._combine_columns()
            df = SuperstructureManager.product_combine_frames(
                self.frames, combo_cols, combo_idx
            )
            # Flatten the columns again for later processing.
            df.columns = df.columns.to_flat_index()
        else:
            df = pd.DataFrame([], index=combo_idx)

        return df

    def _combine_columns(self) -> pd.MultiIndex:
        cols = [df.columns.difference(SUPERSTRUCTURE, sort=False).to_list() for df in self.frames]
        return pd.MultiIndex.from_tuples(list(itertools.product(*cols)))

    def _combine_indexes(self) -> pd.MultiIndex:
        """Returns a union of all of the given dataframe indexes."""
        iterable = iter(self.frames)
        idx = next(iterable).index
        for df in iterable:
            idx = idx.union(df.index)
        return idx

    @staticmethod
    def product_combine_frames(data: List[pd.DataFrame], cols: pd.MultiIndex, index: pd.MultiIndex) -> pd.DataFrame:
        """Iterate through the dataframes, filling data into the combined
        dataframe with duplicate indexes being resolved using a 'last one wins'
        logic.
        """
        df = pd.DataFrame([], index=index, columns=cols)
        for idx, f in enumerate(data):
            data = f.loc[:, cols.get_level_values(idx)]
            data.columns = cols
            df.loc[data.index, :] = data
        return df

    @staticmethod
    def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
        """Using the input/output index for a superstructure, drop duplicates
        where the last instance survives.
        """
        if not isinstance(df.index, pd.MultiIndex):
            df.index = SuperstructureManager.index_from_keys(df)
        duplicates = df.index.duplicated(keep="last")
        return df.loc[~duplicates, :] if duplicates.any() else df

    @staticmethod
    def index_from_keys(df: pd.DataFrame) -> pd.MultiIndex:
        """Construct MultiIndex from exchange keys, allowing for data merging."""
        if df.loc[:, EXCHANGE_KEYS].isna().any().all():
            df = fill_df_keys_with_fields(df)
            assert df.loc[:, EXCHANGE_KEYS].notna().all().all(), "Cannot find all keys."
        return pd.MultiIndex.from_tuples(
            df.loc[:, EXCHANGE_KEYS].apply(tuple, axis=1),
            names=["input", "output"]
        )
