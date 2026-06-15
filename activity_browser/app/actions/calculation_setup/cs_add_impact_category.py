from loguru import logger

import bw2data as bd

from activity_browser.app.actions.base import ABAction, exception_dialogs




class CSAddImpactCategory(ABAction):
    text = "Add Impact Category to Calculation Setup"

    @staticmethod
    @exception_dialogs
    def run(cs_name: str, ic_names: list[str]):
        calculation_setup = bd.calculation_setups[cs_name]

        calculation_setup['ia'] += ic_names
        from activity_browser.bwutils.calculation_setup import ensure_active_lists
        ensure_active_lists(calculation_setup)
        calculation_setup['ia_active'] += [True] * len(ic_names)

        bd.calculation_setups[cs_name] = calculation_setup
        bd.calculation_setups.serialize()
