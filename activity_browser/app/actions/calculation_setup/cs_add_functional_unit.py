from loguru import logger

from activity_browser.bwutils.commontasks import refresh_node
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd




class CSAddFunctionalUnit(ABAction):
    text = "Add Functional Unit to Calculation Setup"

    @staticmethod
    @exception_dialogs
    def run(cs_name: str, activities: list[tuple | int | bd.Node]):
        activities = [refresh_node(node) for node in activities]
        calculation_setup = bd.calculation_setups[cs_name]

        fus = [{act.key: -1.0 if act.get("type") == "waste" else 1.0} for act in activities]
        calculation_setup['inv'] += fus
        from activity_browser.bwutils.calculation_setup import ensure_active_lists
        ensure_active_lists(calculation_setup)
        calculation_setup['inv_active'] += [True] * len(fus)

        bd.calculation_setups[cs_name] = calculation_setup
        bd.calculation_setups.serialize()
