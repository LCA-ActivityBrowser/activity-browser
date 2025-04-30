from logging import getLogger

import pandas as pd
import bw2data as bd

from activity_browser import application, bwutils
from activity_browser.actions.base import ABAction, exception_dialogs
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
        from activity_browser.layouts import pages

        # Check if the calculation setup is complete
        if cs_name not in bd.calculation_setups:
            raise Exception(f"Calculation setup '{cs_name}' not found.")
        cs = bd.calculation_setups[cs_name]
        if not cs.get("inv"):
            raise Exception(f"Calculation setup '{cs_name}' has no functional units.")
        if not cs.get("ia"):
            raise Exception(f"Calculation setup '{cs_name}' has no impact assessment methods.")

        if scenario_data is None:
            mlca = bwutils.MLCA(cs_name)
            contributions = bwutils.Contributions(mlca)
        else:
            mlca = bwutils.SuperstructureMLCA(cs_name, scenario_data)
            contributions = bwutils.SuperstructureContributions(mlca)

        mlca.calculate()
        mc = bwutils.MonteCarloLCA(cs_name)

        page = pages.LCAResultsPage(cs_name, mlca, contributions, mc)
        central = application.main_window.centralWidget()

        central.addToGroup("LCA Results", page)
