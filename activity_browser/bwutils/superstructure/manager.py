# -*- coding: utf-8 -*-
import itertools
from typing import List
import numpy as np
import time
import pandas as pd

import brightway2 as bw

from .activities import fill_df_keys_with_fields
from .dataframe import scenario_columns
from .utils import guess_flow_type, SUPERSTRUCTURE, _time_it_


EXCHANGE_KEYS = pd.Index(["from key", "to key"])
INDEX_KEYS = pd.Index(["from key", "to key", "flow type"])


class SuperstructureManager(object):
    """A combination of methods used to manipulate and transform superstructures."""
    def __init__(self, df: pd.DataFrame, *dfs: pd.DataFrame):
        # Prepare dataframes for further processing
        self.frames: List[pd.DataFrame] = [
            SuperstructureManager.format_dataframe(df)
        ] + [SuperstructureManager.format_dataframe(f) for f in dfs]
        self.is_multiple = len(self.frames) > 1

    def combined_data(self, kind: str = "product", check_duplicates = None) -> pd.DataFrame:
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
            if check_duplicates is not None:
                df = check_duplicates(df)
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
    def format_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Format the input superstructure dataframes.
        If in the future more formatting functions are needed, they should be added here.
        """
        if not isinstance(df.index, pd.MultiIndex):
            df.index = SuperstructureManager.build_index(df)
        df = SuperstructureManager.remove_duplicates(df)
        df = SuperstructureManager.merge_flows_to_self(df)

        return df

    @staticmethod
    def merge_flows_to_self(df: pd.DataFrame) -> pd.DataFrame:
        """Merge any 'technosphere' flows to and from the same key (a.k.a. flow to self).

        This function checks if any flows to self exist and merges them with a production flow.
        If no production flow exists, it is added.
        """
        # get all flows to self
        flows_to_self = df.loc[df.apply(lambda x: True if x['from key'] == x['to key']
                                                          and x['flow type'] == 'technosphere'
        else False, axis=1), :]

        list_exc = []
        prod_indexes = []
        for idx, row in df.loc[flows_to_self.index].iterrows():

            prod_idx = (idx[0], idx[1], 'production')
            tech_idx = (idx[0], idx[1], 'technosphere')

            scenario_cols = df.columns.difference(SUPERSTRUCTURE)

            if not df.index.isin([prod_idx]).any():
                # this flow to self does not have a similar 'production' flow to self.
                # find the default production value and add it as a 'production' flow

                # WARNING: this way of getting the production amount only works for processes with
                # 1 reference flow (because we just take index 0 from list of production exchanges)
                # Once AB has support for multiple reference flows, we need to adjust this code to match the
                # right flow -something with looping over the flows and getting the right product or something-.
                prod_amt = list(bw.get_activity(idx[0]).production())[0].get('amount', 1)

                # make a new df to edit the production, add the correct values/indices where needed
                # and concat to the main df
                new_prod = df.loc[tech_idx]
                new_prod.loc['flow type'] = 'production'
                new_prod.loc[scenario_cols] = prod_amt
                list_exc.append(new_prod)
            else:
                prod_indexes.append(prod_idx)
                list_exc.append(df.loc[prod_idx])
        if len(flows_to_self) > 0:
            prod_idxs = [(x[0], x[1], "production") for x in flows_to_self.index]
            tech_idxs = [(x[0], x[1], "technosphere") for x in flows_to_self.index]

            extra_df = pd.DataFrame(list_exc)
            extra_df.index = prod_idxs

            extra_df.loc[:, scenario_cols] = extra_df.loc[:, scenario_cols] / (extra_df.loc[:, scenario_cols] + df.loc[tech_idxs, scenario_cols].values)

            # drop the 'technosphere' flows
            df = df.drop(flows_to_self.index)
            df = df.drop(prod_indexes)
            df = pd.concat([df, extra_df], axis=0)
        return df

    @staticmethod
    def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
        """Using the input/output index for a superstructure, drop duplicates
        where the last instance survives.
        """
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
            _df = df.loc[:, EXCHANGE_KEYS].notna()
            assert _df.all().all(), "Cannot find all keys. {} of {} exchanges are broken.".format(len(df[_df]),
                                                                                                  len(df))
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
