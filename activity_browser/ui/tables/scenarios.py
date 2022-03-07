# -*- coding: utf-8 -*-
#from typing import Iterable, List, Tuple
from typing import Iterable, Tuple

from PySide2.QtCore import Slot
#from PySide2.QtWidgets import QComboBox

from activity_browser.signals import signals
from .models import ScenarioModel
from .views import ABDataFrameView


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
