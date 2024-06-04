from typing import Iterable, Tuple

from PySide2.QtCore import Slot

from activity_browser.mod import bw2data as bd
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

        self.horizontalHeader().setStretchLastSection(False)
        self.verticalHeader().setVisible(True)

        self.model = ScenarioModel(self)
        self.model.updated.connect(self.update_proxy_model)
        bd.projects.current_changed.connect(self.group_column)

    @Slot(bool, name="showGroupColumn")
    def group_column(self, shown: bool = False) -> None:
        self.setColumnHidden(0, not shown)

    def iterate_scenarios(self) -> Iterable[Tuple[str, Iterable]]:
        return self.model.iterate_scenarios()
