# -*- coding: utf-8 -*-
import itertools
from typing import List
import numpy as np
import pandas as pd
from PySide2.QtWidgets import QApplication, QPushButton
from PySide2.QtCore import Qt
from typing import Union, Optional

import brightway2 as bw

from .activities import fill_df_keys_with_fields, get_activities_from_keys
from .dataframe import scenario_columns
from .utils import guess_flow_type, SUPERSTRUCTURE, _time_it_

import logging
from activity_browser.logger import ABHandler

logger = logging.getLogger('ab_logs')
log = ABHandler.setup_with_logger(logger, __name__)

from .file_dialogs import ABPopup
from ..errors import (CriticalScenarioExtensionError, ScenarioExchangeNotFoundError,
                      ImportCanceledError,
                      )

from .exchanges import set_default_exchange_values

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

    def combined_data(self, kind: str = "product", skip_checks: bool = False) -> pd.DataFrame:
        """
        Combines multiple superstructures using logic specified by the first argument (kind).

        Currently implemented: 'product' creates an outer-product combination
        from all of the columns of the dataframes and injects values from all
        the frames for their specific indexes, any shared indexes are overridden
        where the later dataframes have preference.

        Uses parts of https://stackoverflow.com/a/45286061

        If only a single dataframe is given to the manager, return this dataframe instead.

        Parameters
        ----------
        kind: a string that indicates the type of combination to make for the class self.frames variable
        can be of the form 'product', or 'addition'
        skip_checks: A boolean trigger that should be set to True if the duplicate checks are not required.
        Primarily of use when removing a dataframe, in which case duplicates are removed without warnings
        provided to the user.

        Returns
        -------
        A single pandas dataframe built from the separate dataframes held in the objects frame variable
        """
        if not self.is_multiple:
            df = next(iter(self.frames))
            if skip_checks:
                df = SuperstructureManager.remove_duplicates(df)
            cols = scenario_columns(df)
            df = set_default_exchange_values(df, cols)
            df = SuperstructureManager.merge_flows_to_self(df)
            return pd.DataFrame(
                data=df.loc[:, cols], index=df.index, columns=cols
            )
        combo_idx = self._combine_indexes()

        if kind == "product":
            combo_cols = self._combine_columns()
            df = SuperstructureManager.product_combine_frames(
                self.frames, combo_idx, combo_cols, skip_checks
            )
            # Flatten the columns again for later processing.
            df.columns = df.columns.to_flat_index()
        elif kind == "addition":
            # Find the intersection subset of scenarios.
            cols = self._combine_columns_intersect()
            if cols.empty:
                msg = "While attempting to combine the scenario files an error was detected. No scenario columns were found in common between the files. For combining scenarios by extension at least one scenario needs to be found in common."
                critical = ABPopup.abCritical("Combining scenario files.", msg, QPushButton('Cancel'))
                critical.exec_()
                raise CriticalScenarioExtensionError
            df = SuperstructureManager.addition_combine_frames(
                self.frames, combo_idx, cols, skip_checks
            )
            # Note the dataframe is built with a common index built from all files.
            # So no duplicates will be present in the DataFrame (df), eliminating checks
        else:
            df = pd.DataFrame([], index=combo_idx)
        cols = scenario_columns(df)
        return pd.DataFrame(
            data=df.loc[:, cols], index=df.index, columns=cols
        )

    def _combine_columns(self) -> pd.MultiIndex:
        """
        Combines the scenario columns from the objects self.frames variable following combinatoric
        principles.

        Raises
        ------
        CriticalScenarioExtensionError if multiple dataframes in the self.frames variable contain the
        same scenario names

        Returns
        -------
        A pandas multi-index with the separate dataframes in self.frames contributing to the index levels
        """
        def test_column_names(cols):
            col_set = set()
            cols_len = 0
            for col in cols:
                col_set = col_set.union(col)
                cols_len += len(col)
            if cols_len != len(col_set):
                # if some scenario columns are non-unique
                msg = "While attempting to combine the scenario files an error was detected. The scenario "\
                "files are being extended through combinations, this requires the scenario names to be "\
                "unique. Some scenario names between files were found to be non-unique.<br> To correct "\
                "this please make sure that the scenario names between the files are unique, before trying "\
                "again"
                critical  = ABPopup.abCritical("Combining scenario files", msg, QPushButton('Cancel'))
                critical.exec_()
                raise CriticalScenarioExtensionError()
        cols = [scenario_columns(df).to_list() for df in self.frames]
        test_column_names(cols)
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
    def product_combine_frames(data: List[pd.DataFrame], index: pd.MultiIndex, cols: pd.MultiIndex, skip_checks: bool = False) -> pd.DataFrame:
        """Iterate through the dataframes, filling data into the combined
        dataframe with duplicate indexes being resolved using a 'last one wins'
        logic.

        Parameters
        ----------
        data: A List of dataframes, each dataframe corresponding to a dataframe from a single scenario difference file
        index: The combined Multi-index for the final merged dataframe
        cols: A Multi-index object that contains all of the levels (scenario names) from the different scenario files)
        this is used to create a combined set of scenario names
        skip_checks: a boolean that triggers the use of duplicate checks (not required when removing scenario files)

        Returns
        -------
        A pandas dataframe constructed from the combined inputs to the class self.frames variable
        """
        def combine(one, two):
            """ Should hopefully provide a failsafe approach to combining the different scenario combinations,
            by using a simple vector - vector assignment approach.
            """
            for col_two in SUPERSTRUCTURE.symmetric_difference(two.columns):
                for idx in one.columns:
                    if col_two in set(idx):
                        one.loc[two.index, idx] = two.loc[:, col_two]
        base_scenario_data = pd.DataFrame([], index=index, columns=SUPERSTRUCTURE)
        scenarios_data = pd.DataFrame([], index=index, columns=cols)
        if not skip_checks:
            tmp_df = SuperstructureManager.check_duplicates(data)
            for idx, f in enumerate(tmp_df):
                f = set_default_exchange_values(f, scenario_columns(f))
                combine(scenarios_data, f)
                base_scenario_data.loc[f.index, :] = f.loc[:, SUPERSTRUCTURE]
        else:
            for idx, f in enumerate(data):
                f = SuperstructureManager.remove_duplicates(f)
                f = set_default_exchange_values(f, scenario_columns(f))
                combine(scenarios_data, f)
                base_scenario_data.loc[f.index, :] = f.loc[:, SUPERSTRUCTURE]

        scenarios_data.columns = cols.to_flat_index()
        df = pd.concat([base_scenario_data, scenarios_data], axis=1)
        df = SuperstructureManager.merge_flows_to_self(df)
        df.replace(np.nan, 0, inplace=True)
        return df

    @staticmethod
    def addition_combine_frames(data: List[pd.DataFrame], index: pd.MultiIndex, cols: pd.Index, skip_checks: bool = False) -> pd.DataFrame:
        """
        Iterates through the combined dataframes to produce a single merged dataframe where duplicates are resolved
        with a "last one wins" approach

        Parameters
        ----------
        data: list of input dataframes from the scenario difference files
        index: pandas Multi-Index used to create the x-index from the merged indexes of the data input
        cols: the list of scenario columns from the scenario difference files
        skip_checks: a simple boolean used to avoid the duplicate checks (when removing a scenario file)

        Returns
        -------
        A pandas dataframe constructed from the combined inputs to the class self.frames variable
        """
        columns = data.columns if isinstance(data, pd.DataFrame) else data[0].columns

        df = pd.DataFrame([], index=index, columns=columns)
        if not skip_checks:
            SuperstructureManager.check_duplicates(data)
            for f in data:
                f = set_default_exchange_values(f, cols)
                df.loc[f.index, columns] = f.loc[:, columns]
        else:
            for f in data:
                if skip_checks:
                    f = SuperstructureManager.remove_duplicates(f)
                f = set_default_exchange_values(f, cols)
                df.loc[f.index, columns] = f.loc[:, columns]
        df = SuperstructureManager.merge_flows_to_self(df)
        df.replace(np.nan, 0, inplace=True)
        return df.loc[:, cols]

    @staticmethod
    def format_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Format the input superstructure dataframes.
        If in the future more formatting functions are needed, they should be added here.
        """
        if not isinstance(df.index, pd.MultiIndex):
            df.index = SuperstructureManager.build_index(df)
        # all import checks should take place before merge_flows_to_self
#        df = SuperstructureManager.check_duplicates(df)
#        df = SuperstructureManager.merge_flows_to_self(df)

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
                new_prod = df.loc[tech_idx].copy()
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
            denominator = (extra_df.loc[:, scenario_cols] + df.loc[tech_idxs, scenario_cols].values)
            extra_df.loc[:, scenario_cols] = extra_df.loc[:, scenario_cols] / denominator
            # if we did divide by 0 then replace these nans by 0
            extra_df.loc[:, scenario_cols] = extra_df.loc[:, scenario_cols].fillna(0)

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
            log.warning("Found and dropped {} duplicate exchanges.".format(duplicates.sum()))
            return df.loc[~duplicates, :]
        return df

    @staticmethod
    def build_index(df: pd.DataFrame) -> pd.MultiIndex:
        """Construct MultiIndex from exchange keys and flows, allowing for
        data merging.

        - If any of the exchange key columns are missing keys, attempt to fill
        them. If filling them does not succeed, raise an assertion.
        """
        unknown_flows = df.loc[:, "flow type"].isna()
        if unknown_flows.any():
            log.warning("Not all flow types are known, guessing {} flows".format(
                unknown_flows.sum()
            ))
            df.loc[unknown_flows, "flow type"] = df.loc[
                unknown_flows, EXCHANGE_KEYS].apply(guess_flow_type, axis=1)
        return pd.MultiIndex.from_tuples(
            df.loc[:, INDEX_KEYS].apply(tuple, axis=1),
            names=["input", "output", "flow"]
        )

    @staticmethod
    def exchangesPopup() -> ABPopup:
        """
        Provides a popup message if there is an issue to find some of the scenario exchanges in the uploaded files

        Returns
        -------
        A QDialog with a critical Error
        """
        msg = "<p>One, or several, exchanges (rows) in the scenario file could not be found in the database (meaning:"\
              " a part or all of the exchange information, i.e. input or output product/activity/unit/geography, or the"\
            " key, have no match in the project databases).</p> <p>It is not possible to proceed at this point."\
            " you may save the scenario file with an additional column indicating the problematic exchanges.</p>"
        pop = ABPopup.abCritical("Exchange(s) not found", msg, QPushButton('Save'), QPushButton('Cancel'))
        pop.save_options()
        return pop

    @staticmethod
    def fill_empty_process_keys_in_exchanges(df: pd.DataFrame) -> pd.DataFrame:
        """identifies those exchanges in the input dataframe that are missing keys.
         If the keys cannot be found in the available databases then an Exception is
         raised

         Raises
         ------
         ScenarioExchangeNotFoundError if a scenario exchange is not present in the local database

         Parameters
         ----------
         df: the input dataframe containing scenario data with exchanges that need to be
         checked for the presence of a key

         Returns
         -------
         A pandas dataframe with complete entries for the dataframes 'to key' and 'from key' fields
         """
        if df.loc[:, EXCHANGE_KEYS].isna().any().any():
            df = fill_df_keys_with_fields(df)
            _df = df.loc[df.loc[:, EXCHANGE_KEYS].isna().any(axis=1)]
            if not _df.empty:
                sdf_keys = SuperstructureManager.exchangesPopup()
                sdf_keys.save_options()
                sdf_keys.dataframe_to_file(df, _df.index)
                QApplication.restoreOverrideCursor()
                sdf_keys.exec_()
                raise ScenarioExchangeNotFoundError("Cannot find key(s) in local databases.")
        return df

    @staticmethod
    def verify_scenario_process_keys(df: pd.DataFrame) -> pd.DataFrame:
        """Checks all process keys in the scenario file and does not provide alternative keys based on exchange
        metadata.

        Raises
        ------
        ScenarioExchangeNotFoundError if a scenario exchange is not present in the local database

        Parameters
        -------
        df: the dataframe with process keys that need to be verified

        Returns
        -------
        A scenario dataframe with all scenario exchange keys verified with the local brightway databases
        """
        dbs = set(df.loc[:, 'from database']).union(df.loc[:, 'to database'])
        df_ = pd.DataFrame({}, columns=df.columns)
        for db in dbs:
            _ = get_activities_from_keys(df, db)
            df_ = pd.concat([df_, _], axis=0, ignore_index=False)
        if not df_.empty:
            errors_df = pd.DataFrame(df_, index=None, columns=['from key', 'to key', 'flow type'])
            sdf_keys = SuperstructureManager.exchangesPopup()
            sdf_keys.save_options()
            sdf_keys.dataframe(errors_df, errors_df.columns)
            sdf_keys.dataframe_to_file(df, df_.index)
            QApplication.restoreOverrideCursor()
            sdf_keys.exec_()
            raise ScenarioExchangeNotFoundError("A key provided in the scenario file is not valid for the available database, consult the respective output.")

    @staticmethod
    def check_duplicates(data: Optional[Union[pd.DataFrame, list]],
                         index: list = ['to key', 'from key', 'flow type']):
        """
        Checks three fields to identify whether a scenario difference file contains duplicate exchanges:
        'from key', 'to key' and 'flow type'
        Produces a warning

        Raises
        ------
        ImportCanceledError if the user cancels the import due to duplicate exchanges

        Parameters
        ----------
        data: a pandas dataframe or list of pandas dataframes that will be checked for containing duplicates
        index: nominally required, but probably best to avoid overwriting the default values. Used to indicate the
            columns to check for duplication of an exchange

        Returns
        -------
        A dataframe that contains only unique flow exchanges
        """
        if isinstance(data, pd.DataFrame):
            return SuperstructureManager._check_duplicate(data, index)
        else:
            # Each time the frames are gathered into a list
            # and we are always checking the last file
            # So only comparisons with the last file are required
            count = 1
            df = data[-count]
            duplicated = {}
            while count < len(data):
                count += 1
                popped = data[-count]
                duplicates = SuperstructureManager._check_duplicates(df, popped)
                if not duplicates.empty:
                    duplicated[count] = duplicates
            if duplicated:

                msg = "<p>Duplicates have been found, meaning that there are several rows in the scenario file describing"\
                "scenarios for the same flow. The AB can deal with this by discarding all but the last row for this "\
                "exchange.</p> <p>Press 'Ok' to proceed, press 'Cancel' to abort.</p>"
                for file, frame in duplicated.items():
                    frame.insert(0, 'File', file, allow_duplicates=True)
                warning = ABPopup.abWarning('Duplicate flow exchanges', msg, QPushButton('Ok'), QPushButton('Cancel'))
                warning.dataframe(pd.concat([file for file in duplicated.values()]), index)
                QApplication.restoreOverrideCursor()
                response = warning.exec_()
                QApplication.setOverrideCursor(Qt.WaitCursor)
                if response == warning.Rejected:
                    raise ImportCanceledError
            return data

    @staticmethod
    def _check_duplicates(dfp: pd.DataFrame, pdf: pd.DataFrame,
                          index: list = ['to key', 'from key', 'flow type']) -> pd.DataFrame:
        """ NOT TO BE USED OUTSIDE OF CALLING METHOD check_duplicates """
        # First save the original index and create a new one that can help the user identify duplicates in their files
        d_idx = dfp.index
        dfp.index = pd.Index([str(i) for i in range(dfp.shape[0])])
        p_idx = pdf.index
        pdf.index = pd.Index([str(i) for i in range(pdf.shape[0])])
        df = pd.concat([dfp, pdf], ignore_index=True)
        dfp.index = d_idx
        pdf.index = p_idx
        dfp.drop_duplicates(index, keep='last', inplace=True)
        #        pdf.drop_duplicates(index, keep='last', inplace=True)
        return df.loc[df.duplicated(index, keep=False)]

    @staticmethod
    def _check_duplicate(data: pd.DataFrame, index: list = ['to key', 'from key', 'flow type']) -> pd.DataFrame:
        """ NOT TO BE USED OUTSIDE OF CALLING METHOD check_duplicates """
        df = data.copy()
        df.index = pd.Index([str(i) for i in range(df.shape[0])])
        duplicates = df.duplicated(index, keep=False)
        if duplicates.any():
            msg = "<p>Duplicates have been found, meaning that there are several rows in the scenario file describing" \
                  "scenarios for the same flow. The AB can deal with this by discarding all but the last row for this " \
                  "exchange.</p> <p>Press 'Ok' to proceed, press 'Cancel' to abort.</p>"
            warning = ABPopup.abWarning('Duplicate flow exchanges', msg, QPushButton('Ok'), QPushButton('Cancel'))
            warning.dataframe(df.loc[duplicates], index)

            QApplication.restoreOverrideCursor()
            response = warning.exec_()
            QApplication.setOverrideCursor(Qt.WaitCursor)
            if response == warning.Rejected:
                raise ImportCanceledError
            data.drop_duplicates(index, keep='last', inplace=True)
        return data

