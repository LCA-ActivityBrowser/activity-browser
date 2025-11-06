from loguru import logger

import pandas as pd
import bw2data as bd

from qtpy import QtCore, QtWidgets

from activity_browser import app
from activity_browser.bwutils.multilca import MLCA, Contributions
from activity_browser.bwutils.superstructure import SuperstructureMLCA, SuperstructureContributions
from activity_browser.bwutils.montecarlo import MonteCarloLCA
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons




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
        from activity_browser.app import pages

        # Check if the calculation setup is complete
        if cs_name not in bd.calculation_setups:
            raise Exception(f"Calculation setup '{cs_name}' not found.")
        cs = bd.calculation_setups[cs_name]
        if not cs.get("inv"):
            raise Exception(f"Calculation setup '{cs_name}' has no functional units.")
        if not cs.get("ia"):
            raise Exception(f"Calculation setup '{cs_name}' has no impact assessment methods.")

        dialog = CalculationDialog(cs_name, app.main_window)
        dialog.show()
        app.application.thread().eventDispatcher().processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents)

        try:
            if scenario_data is None:
                mlca = MLCA(cs_name)
                contributions = Contributions(mlca)
            else:
                mlca = SuperstructureMLCA(cs_name, scenario_data)
                contributions = SuperstructureContributions(mlca)

            mlca.calculate()
            mc = MonteCarloLCA(cs_name)

            page = pages.LCAResultsPage(cs_name, mlca, contributions, mc)
            central = app.main_window.centralWidget()
        except:
            dialog.close()
            raise

        dialog.close()
        central.addToGroup("LCA Results", page)


class CalculationDialog(QtWidgets.QDialog):
    def __init__(self, cs_name: str, parent=None):
        super().__init__(parent, QtCore.Qt.WindowTitleHint)
        self.setWindowTitle(f"Running Calculations")
        self.setModal(True)

        self.label = QtWidgets.QLabel(f"Running calculations for setup: <b>{cs_name}</b>", self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.label)
        self.setLayout(layout)
