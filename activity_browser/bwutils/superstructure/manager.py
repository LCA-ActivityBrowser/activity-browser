# -*- coding: utf-8 -*-
import itertools
from typing import List

import pandas as pd

from .activities import fill_df_keys_with_fields
from .dataframe import scenario_columns
from .utils import guess_flow_type


EXCHANGE_KEYS = pd.Index(["from key", "to key"])
INDEX_KEYS = pd.Index(["from key", "to key", "flow type"])


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
            cols = scenario_columns(df)
            return pd.DataFrame(
                data=df.loc[:, cols], index=df.index, columns=cols
            )
        combo_idx = self._combine_indexes()

        if kind == "product":
            combo_cols = self._combine_columns()
            df = SuperstructureManager.product_combine_frames(
                self.frames, combo_idx, combo_cols
            )
            # Flatten the columns again for later processing.
            df.columns = df.columns.to_flat_index()
        elif kind == "addition":
            # Find the intersection subset of scenarios.
            cols = self._combine_columns_intersect()
            df = SuperstructureManager.addition_combine_frames(
                self.frames, combo_idx, cols
            )
        else:
            df = pd.DataFrame([], index=combo_idx)

        return df

    def _combine_columns(self) -> pd.MultiIndex:
        cols = [scenario_columns(df).to_list() for df in self.frames]
        return pd.MultiIndex.from_tuples(list(itertools.product(*cols)))

    def _combine_columns_intersect(self) -> pd.Index:
        iterable = iter(self.frames)
        cols = scenario_columns(next(iterable))
        for df in iterable:
            cols = cols.intersection(scenario_columns(df))
        return cols

    def _combine_indexes(self) -> pd.MultiIndex:
        """Returns a union of all of the given dataframe indexes."""
        iterable = iter(self.frames)
        idx = next(iterable).index
        for df in iterable:
            idx = idx.union(df.index)
        return idx

    @staticmethod
    def product_combine_frames(data: List[pd.DataFrame], index: pd.MultiIndex, cols: pd.MultiIndex) -> pd.DataFrame:
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
    def addition_combine_frames(data: List[pd.DataFrame], index: pd.MultiIndex, cols: pd.Index) -> pd.DataFrame:
        df = pd.DataFrame([], index=index, columns=cols)
        for f in data:
            data = f.loc[:, cols]
            df.loc[data.index, :] = data
        return df

    @staticmethod
    def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
        """Using the input/output index for a superstructure, drop duplicates
        where the last instance survives.
        """
        if not isinstance(df.index, pd.MultiIndex):
            df.index = SuperstructureManager.build_index(df)
        duplicates = df.index.duplicated(keep="last")
        if duplicates.any():
            print("Found and dropped {} duplicate exchanges.".format(duplicates.sum()))
            return df.loc[~duplicates, :]
        return df

    @staticmethod
    def build_index(df: pd.DataFrame) -> pd.MultiIndex:
        """Construct MultiIndex from exchange keys and flows, allowing for
        data merging.

        - If any of the exchange key columns are missing keys, attempt to fill
        them. If filling them does not succeed, raise an assertion.
        """
        if df.loc[:, EXCHANGE_KEYS].isna().any().all():
            df = fill_df_keys_with_fields(df)
            assert df.loc[:, EXCHANGE_KEYS].notna().all().all(), "Cannot find all keys."
        unknown_flows = df.loc[:, "flow type"].isna()
        if unknown_flows.any():
            print("Not all flow types are known, guessing {} flows".format(
                unknown_flows.sum()
            ))
            df.loc[unknown_flows, "flow type"] = df.loc[
                unknown_flows, EXCHANGE_KEYS].apply(guess_flow_type, axis=1)
        return pd.MultiIndex.from_tuples(
            df.loc[:, INDEX_KEYS].apply(tuple, axis=1),
            names=["input", "output", "flow"]
        )
