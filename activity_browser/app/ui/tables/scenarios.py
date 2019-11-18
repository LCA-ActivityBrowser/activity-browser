# -*- coding: utf-8 -*-
from typing import Iterable, List, Tuple

import pandas as pd
from presamples import PresampleResource
from PySide2.QtCore import Slot
from PySide2.QtWidgets import QComboBox

from ...bwutils.presamples import process_brightway_parameters
from ...signals import signals
from .delegates import FloatDelegate, ViewOnlyDelegate
from .views import ABDataFrameEdit, dataframe_sync


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
        return PresampleResource.select().exists()

    def get_package_names(self) -> List[str]:
        return [r.name for r in PresampleResource.select(PresampleResource.name)]


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

