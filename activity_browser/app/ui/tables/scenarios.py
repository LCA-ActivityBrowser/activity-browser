# -*- coding: utf-8 -*-
import itertools
from typing import Iterable, Tuple

import pandas as pd

from ...bwutils.presamples import process_brightway_parameters
from .delegates import FloatDelegate, ViewOnlyDelegate
from .views import ABDataFrameEdit, dataframe_sync


class ScenarioTable(ABDataFrameEdit):
    """ Constructs an infinitely (horizontally) expandable table that is
    used to set specific amount for user-defined parameters.

    The two required columns in the dataframe for the table are 'Name',
    and 'Type'. all other columns are seen as scenarios containing N floats,
    where N is the number of rows found in the Name column.

    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegate(FloatDelegate(self))
        self.setItemDelegateForColumn(0, ViewOnlyDelegate(self))

    @dataframe_sync
    def sync(self, df: pd.DataFrame = None) -> None:
        if df is not None:
            required = {"Name", "Group"}
            if not required.issubset(df.columns):
                raise ValueError(
                    "The given dataframe does not contain required columns: {}".format(required.difference(df.columns))
                )
            assert df.columns.get_loc("Group") == 1
            self.dataframe = df.set_index("Name")
            return
        data = process_brightway_parameters()
        self.dataframe = pd.DataFrame(data, columns=["Name", "Group", "default"])
        self.dataframe.set_index("Name", inplace=True)

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

