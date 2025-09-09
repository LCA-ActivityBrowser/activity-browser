from logging import getLogger

from activity_browser import bwutils
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd

log = getLogger(__name__)


class CSChangeFunctionalUnit(ABAction):
    """
    Updates the functional unit amount for a specific inventory item in a calculation setup.

    This method modifies the amount of a functional unit in the inventory of a given calculation setup
    and saves the updated setup.

    Args:
        cs_name (str): The name of the calculation setup to modify.
        index (int): The index of the inventory item within the calculation setup.
        amount (float): The new amount to set for the functional unit.

    Steps:
    - Retrieve the calculation setup by its name.
    - Extract the key of the inventory item at the specified index.
    - Update the amount for the specified inventory item.
    - Serialize and save the updated calculation setup.

    Raises:
        Exception: If an error occurs during the process, it is handled by the `exception_dialogs` decorator.
    """
    text = "Add Functional Unit to Calculation Setup"

    @staticmethod
    @exception_dialogs
    def run(cs_name: str, index: int, amount: float):
        calculation_setup = bd.calculation_setups[cs_name]

        key = list(calculation_setup['inv'][index].keys())[0]
        calculation_setup['inv'][index][key] = amount

        bd.calculation_setups.serialize()
