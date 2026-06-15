from loguru import logger

import bw2data as bd

from activity_browser.app.actions.base import ABAction, exception_dialogs




class CSDeleteFunctionalUnit(ABAction):
    text = "Delete Functional Unit"

    @staticmethod
    @exception_dialogs
    def run(cs_name: str, indices: list[int]):
        calculation_setup = bd.calculation_setups[cs_name]

        from activity_browser.bwutils.calculation_setup import ensure_active_lists
        ensure_active_lists(calculation_setup)
        for index in sorted(set(indices), reverse=True):
            del calculation_setup['inv'][index]
            del calculation_setup['inv_active'][index]

        bd.calculation_setups[cs_name] = calculation_setup
        bd.calculation_setups.serialize()
