# -*- coding: utf-8 -*-
from typing import Iterable, Tuple

import numpy as np
import pandas as pd
from PySide2.QtCore import Slot

from activity_browser.bwutils.utils import Parameters
from activity_browser.signals import signals
from .base import PandasModel


class ScenarioModel(PandasModel):
    HEADERS = ["Name", "Group", "default"]
    MATCH_COLS = ["Name", "Group"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        signals.project_selected.connect(self.sync)
        signals.parameters_changed.connect(self.rebuild_table)
        signals.parameter_renamed.connect(self.update_param_name)

    @Slot(name="doCleanSync")
    def sync(self, df: pd.DataFrame = None, include_default: bool = True) -> None:
        """ Construct the dataframe from the existing parameters, if ``df``
        is given, perform a merge to possibly include additional columns.
        """
        data = [p[:3] for p in Parameters.from_bw_parameters()]
        if df is None:
            self._dataframe = pd.DataFrame(
                data, columns=self.HEADERS).set_index("Name")
        else:
            required = set(self.MATCH_COLS)
            if not required.issubset(df.columns):
                raise ValueError(
                    "The given dataframe does not contain required columns: {}".format(required.difference(df.columns))
                )
            assert df.columns.get_loc("Group") == 1
            if include_default:
                new_df = pd.DataFrame(data, columns=self.HEADERS)
                if "default" in df.columns:
                    df.drop(columns="default", inplace=True)
                self._dataframe = self._perform_merge(new_df, df).set_index("Name")
            else:
                # Now we're gonna need to ensure that the dataframe is of
                # the same size
                assert len(data) >= df.shape[0], "Too many parameters found, not possible."
                missing = len(data) - df.shape[0]
                if missing != 0:
                    nan_data = pd.DataFrame(index=pd.RangeIndex(missing), columns=df.columns)
                    df = pd.concat([df, nan_data], ignore_index=True)
                self._dataframe = df.set_index("Name")
        self.updated.emit()

    @classmethod
    def _perform_merge(cls, left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
        """ There are three kinds of actions that can occur: adding new columns,
        updating values in matching columns, and a combination of the two.

        ``left`` dataframe always determines the row-size of the resulting
        dataframe.
        Any `NaN` values in the new columns in ``right`` will be replaced
        with values from the `default` column from ``left``.
        """
        right_columns = right.drop(columns=cls.MATCH_COLS).columns
        matching = right_columns.intersection(left.columns)
        if not matching.empty:
            # Replace values and drop the matching columns
            left[matching] = right[matching]
            right.drop(columns=matching, inplace=True)
            if right.drop(columns=cls.MATCH_COLS).columns.any():
                # Merge the remaining columns
                df = left.merge(right, how="left", on=cls.MATCH_COLS)
            else:
                df = left
        else:
            df = left.merge(right, how="left", on=cls.MATCH_COLS)
        # Now go over the non-standard columns and see if there are any
        # missing values.
        new_cols = df.drop(columns=cls.HEADERS).columns
        missing = new_cols[df[new_cols].isna().any()]
        if not missing.empty:
            idx = missing.append(pd.Index(["default"]))
            df[idx] = df[idx].apply(lambda x: x.fillna(x["default"]), axis=1)
        return df

    @Slot(name="resetDataIndex")
    def rebuild_table(self) -> None:
        """ Should be called when the `parameters_changed` signal is emitted.
        Will call sync with a copy of the current dataframe to ensure no
        user-imported data is lost.

        TODO: handle database parameter group changes correctly. Maybe a
         separate signal like rename?
        """
        self.sync(self._dataframe.reset_index())

    @Slot(str, str, str, name="renameParameterIndex")
    def update_param_name(self, old: str, group: str, new: str) -> None:
        """ Kind of a cheat, but directly edit the dataframe.index to update
        the table whenever the user renames a parameter.
        """
        new_idx = pd.Index(np.where(
            (self._dataframe.index == old) & (self._dataframe["Group"] == group),
            new, self._dataframe.index
        ), name=self._dataframe.index.name)
        self._dataframe.index = new_idx
        self.updated.emit()

    def iterate_scenarios(self) -> Iterable[Tuple[str, Iterable]]:
        """ Iterates through all of the non-description columns from left to right.

        Returns an iterator of tuples containing the scenario name and a dictionary
        of the parameter names and new amounts.

        TODO: Fix this so it returns the least amount of required information.
        """
        return (
            (scenario, self._dataframe[scenario])
            for scenario in self._dataframe.columns[1:]
        )
