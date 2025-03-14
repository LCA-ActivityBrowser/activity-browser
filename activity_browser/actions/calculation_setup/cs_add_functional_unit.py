from logging import getLogger

from activity_browser import bwutils
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd

log = getLogger(__name__)


class CSAddFunctionalUnit(ABAction):
    text = "Add Functional Unit to Calculation Setup"

    @staticmethod
    @exception_dialogs
    def run(cs_name: str, activities: list[tuple | int | bd.Node]):
        activities = [bwutils.refresh_node(node) for node in activities]
        calculation_setup = bd.calculation_setups[cs_name]

        fus = [{act.key: 1.0} for act in activities]
        calculation_setup['inv'] += fus

        bd.calculation_setups[cs_name] = calculation_setup
        bd.calculation_setups.serialize()
