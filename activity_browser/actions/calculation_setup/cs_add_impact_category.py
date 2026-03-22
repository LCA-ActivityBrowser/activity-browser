from logging import getLogger

import bw2data as bd

from activity_browser.actions.base import ABAction, exception_dialogs

log = getLogger(__name__)


class CSAddImpactCategory(ABAction):
    text = "Add Impact Category to Calculation Setup"

    @staticmethod
    @exception_dialogs
    def run(cs_name: str, ic_names: list[str]):
        calculation_setup = bd.calculation_setups[cs_name]

        calculation_setup['ia'] += ic_names

        bd.calculation_setups[cs_name] = calculation_setup
        bd.calculation_setups.serialize()
