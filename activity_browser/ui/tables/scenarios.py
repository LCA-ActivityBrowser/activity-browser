# -*- coding: utf-8 -*-
from typing import Iterable, List, Tuple

from PySide2.QtCore import Slot
from PySide2.QtWidgets import QComboBox

from activity_browser.bwutils import presamples as ps_utils
from activity_browser.signals import signals
from .models import ScenarioModel
from .views import ABDataFrameView


class PresamplesList(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._connect_signals()

    def _connect_signals(self):
        # If a calculation is run with presamples, catch the signal and
        # update all instances of PresamplesList.
        signals.lca_calculation.connect(self.sync)
        signals.presample_package_created.connect(self.sync)
        signals.presample_package_removed.connect(self.sync)
        signals.project_selected.connect(self.sync)

    @Slot(name="syncAll")
    @Slot(str, name="syncOnName")
    def sync(self, data: dict) -> None:
        name = data.get('cs_name')
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


class ScenarioTable(ABDataFrameView):
    """ Constructs an infinitely (horizontally) expandable table that is
    used to set specific amount for user-defined parameters.

    The two required columns in the dataframe for the table are 'Name',
    and 'Type'. all other columns are seen as scenarios containing N floats,
    where N is the number of rows found in the Name column.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.table_name = "scenario_table"
        self.model = ScenarioModel(self)
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)
        signals.project_selected.connect(self.group_column)

    @Slot(bool, name="showGroupColumn")
    def group_column(self, shown: bool = False) -> None:
        self.setColumnHidden(0, not shown)

    def iterate_scenarios(self) -> Iterable[Tuple[str, Iterable]]:
        return self.model.iterate_scenarios()
