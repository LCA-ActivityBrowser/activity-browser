from logging import getLogger

import bw2data as bd

from activity_browser.actions.base import ABAction, exception_dialogs

log = getLogger(__name__)


class CSDeleteFunctionalUnit(ABAction):
    text = "Delete Functional Unit"

    @staticmethod
    @exception_dialogs
    def run(cs_name: str, indices: list[int]):
        calculation_setup = bd.calculation_setups[cs_name]

        for index in sorted(set(indices), reverse=True):
            del calculation_setup['inv'][index]

        bd.calculation_setups[cs_name] = calculation_setup
        bd.calculation_setups.serialize()
