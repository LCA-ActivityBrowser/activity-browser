from logging import getLogger

import pandas as pd

from activity_browser import application, signals, bwutils
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
        from activity_browser.layouts.pages import LCAResultsPage

        if scenario_data is None:
            mlca = bwutils.MLCA(cs_name)
            contributions = bwutils.Contributions(mlca)
        else:
            mlca = bwutils.SuperstructureMLCA(cs_name, scenario_data)
            contributions = bwutils.SuperstructureContributions(mlca)

        mlca.calculate()
        mc = bwutils.MonteCarloLCA(cs_name)

        page = LCAResultsPage(cs_name, mlca, contributions, mc)

        tab = application.main_window.centralWidget().tabs["LCA results"]
        tab.open_results(page)

