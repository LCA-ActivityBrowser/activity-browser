# -*- coding: utf-8 -*-
from bw2calc.errors import BW2CalcError
from PySide2.QtWidgets import QApplication

from activity_browser import log

from ..bwutils import (MLCA, Contributions, MonteCarloLCA,
                       SuperstructureContributions, SuperstructureMLCA)
from .errors import CriticalCalculationError, ScenarioExchangeNotFoundError


def do_LCA_calculations(data: dict):
    """Perform the MLCA calculation."""
    cs_name = data.get("cs_name", "new calculation")
    calculation_type = data.get("calculation_type", "simple")

    if calculation_type == "simple":
        try:
            mlca = MLCA(cs_name)
            contributions = Contributions(mlca)
        except KeyError as e:
            raise BW2CalcError("LCA Failed", str(e)).with_traceback(e.__traceback__)
    elif calculation_type == "scenario":
        try:
            df = data.get("data")
            mlca = SuperstructureMLCA(cs_name, df)
            contributions = SuperstructureContributions(mlca)
        except AssertionError as e:
            # This occurs if the superstructure itself detects something is wrong.
            QApplication.restoreOverrideCursor()
            raise BW2CalcError("Scenario LCA failed.", str(e)).with_traceback(
                e.__traceback__
            )
        except ValueError as e:
            # This occurs if the LCA matrix does not contain any of the
            # exchanges mentioned in the superstructure data.
            QApplication.restoreOverrideCursor()
            raise BW2CalcError(
                "Scenario LCA failed.",
                "Constructed LCA matrix does not contain any exchanges from the superstructure",
            ).with_traceback(e.__traceback__)
        except KeyError as e:
            QApplication.restoreOverrideCursor()
            raise BW2CalcError("LCA Failed", str(e)).with_traceback(e.__traceback__)
        except CriticalCalculationError as e:
            QApplication.restoreOverrideCursor()
            raise Exception(e)
        except ScenarioExchangeNotFoundError as e:
            QApplication.restoreOverrideCursor()
            raise CriticalCalculationError
    else:
        log.error("Calculation type must be: simple or scenario. Given:", cs_name)
        raise ValueError

    mlca.calculate()
    mc = MonteCarloLCA(cs_name)

    return mlca, contributions, mc
