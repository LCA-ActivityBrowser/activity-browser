from logging import getLogger

import pandas as pd

from activity_browser import application, signals
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons

log = getLogger(__name__)


class CSCalculate(ABAction):
    """
    ABAction to calculate a calculation setup. First asks the user for confirmation and returns if cancelled. Otherwise,
    passes the csname to the CalculationSetupController for calculation. Finally, displays confirmation that it succeeded.
    """

    icon = qicons.calculate
    text = "Calculate"

    @staticmethod
    @exception_dialogs
    def run(cs_name: str, scenario_data: pd.DataFrame = None):
        if scenario_data is None:
            signals.lca_calculation.emit({"cs_name": cs_name, "calculation_type": "simple"})
        else:
            signals.lca_calculation.emit({"cs_name": cs_name, "calculation_type": "scenario", "data": scenario_data})

