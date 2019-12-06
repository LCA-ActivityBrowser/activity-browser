# -*- coding: utf-8 -*-
from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd
from PySide2.QtCore import Slot
from PySide2.QtWidgets import QComboBox

from ...bwutils import presamples as ps_utils
from ...signals import signals
from .views import ABDataFrameSimpleCopy, dataframe_sync


class PresamplesList(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._connect_signals()

    def _connect_signals(self):
        # If a calculation is run with presamples, catch the signal and
        # update all instances of PresamplesList.
        signals.lca_presamples_calculation.connect(
            lambda _, ps: self.sync(ps)
        )
        signals.presample_package_created.connect(self.sync)
        signals.presample_package_removed.connect(self.sync)
        signals.project_selected.connect(self.sync)

    @Slot(name="syncAll")
    @Slot(str, name="syncOnName")
    def sync(self, name: str = None) -> None:
        self.blockSignals(True)
        self.clear()
        resources = self.get_package_names()
        self.insertItems(0, resources)
        self.blockSignals(False)
        if name and name in resources:
            self.setCurrentIndex(resources.index(name))

    @property
    def selection(self) -> str:
        return self.currentText()

    @property
    def has_packages(self) -> bool:
        return bool(ps_utils.count_presample_packages())

    @staticmethod
    def get_package_names() -> List[str]:
        return ps_utils.find_all_package_names()


class ScenarioTable(ABDataFrameSimpleCopy):
    """ Constructs an infinitely (horizontally) expandable table that is
    used to set specific amount for user-defined parameters.

    The two required columns in the dataframe for the table are 'Name',
    and 'Type'. all other columns are seen as scenarios containing N floats,
    where N is the number of rows found in the Name column.

    """
    HEADERS = ["Name", "Group", "default"]
    MATCH_COLS = ["Name", "Group"]

    def __init__(self, parent=None):
        super().__init__(parent)

    @dataframe_sync
    def sync(self, df: pd.DataFrame = None) -> None:
        """ Construct the dataframe from the existing parameters, if ``df``
        is given, perform a merge to possibly include additional columns.
        """
        data = ps_utils.process_brightway_parameters()
        self.dataframe = pd.DataFrame(data, columns=self.HEADERS)
        if df is not None:
            required = set(self.MATCH_COLS)
            if not required.issubset(df.columns):
                raise ValueError(
                    "The given dataframe does not contain required columns: {}".format(required.difference(df.columns))
                )
            assert df.columns.get_loc("Group") == 1
            if "default" in df.columns:
                df.drop(columns="default", inplace=True)
            self.dataframe = self._perform_merge(self.dataframe, df)
        self.dataframe.set_index("Name", inplace=True)

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

    @Slot(name="safeTableRebuild")
    def rebuild_table(self) -> None:
        """ Should be called when the `parameters_changed` signal is emitted.
        Will call sync with a copy of the current dataframe to ensure no
        user-imported data is lost.

        TODO: handle database parameter group changes correctly. Maybe a
         separate signal like rename?
        """
        self.sync(self.dataframe.reset_index())

    @Slot(bool, name="showGroupColumn")
    def group_column(self, shown: bool = False) -> None:
        self.setColumnHidden(0, not shown)

    @Slot(str, str, str, name="renameParameterIndex")
    def update_param_name(self, old: str, group: str, new: str) -> None:
        """ Kind of a cheat, but directly edit the dataframe.index to update
        the table whenever the user renames a parameter.
        """
        self.dataframe.index = pd.Index(np.where(
            (self.dataframe.index == old) & (self.dataframe["Group"] == group),
            new, self.dataframe.index
        ), name=self.dataframe.index.name)

    def get_scenario_columns(self) -> Iterable[str]:
        return self.dataframe.columns[1:]

    def iterate_scenarios(self) -> Iterable[Tuple[str, Iterable]]:
        """ Iterates through all of the non-description columns from left to right.

        Returns an iterator of tuples containing the scenario name and a dictionary
        of the parameter names and new amounts.

        TODO: Fix this so it returns the least amount of required information.
        """
        return (
            (scenario, self.dataframe[scenario])
            for scenario in self.get_scenario_columns()
        )

