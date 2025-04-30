from logging import getLogger

from qtpy import QtWidgets

import bw2data as bd

from activity_browser import application, actions
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils import refresh_node
from activity_browser.ui.icons import qicons

log = getLogger(__name__)


class CSNew(ABAction):
    """
    Create a new Calculation Setup.

    This method prompts the user for a name for the new Calculation Setup (CS) if not provided.
    It validates the name to ensure it is unique within the project and creates a new CS
    with the specified functional units and impact categories.

    Args:
        name (str, optional): The name of the new Calculation Setup. If not provided, the user is prompted.
        functional_units (list[dict[tuple | int | bd.Node, float]], optional): A list of functional units to include in the CS.
        impact_categories (list[tuple], optional): A list of impact categories to include in the CS.

    Returns:
        None: Returns early if the user cancels, provides no name, or if the name already exists.

    Raises:
        None: This method does not raise exceptions but logs errors and shows warnings for invalid inputs.
    """

    icon = qicons.add
    text = "New calculation setup..."

    @staticmethod
    @exception_dialogs
    def run(name: str = None,
            functional_units: list[dict[tuple | int | bd.Node, float]] = None,
            impact_categories: list[tuple] = None
            ):

        name = name or CSNew.get_cs_name()

        # return if the user cancels or gives no name
        if not name:
            return

        # throw error if the name is already present, and return
        if name in bd.calculation_setups:
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "Not possible",
                "A calculation setup with this name already exists.",
            )
            return

        inv = functional_units or []
        for i, fu in enumerate(inv):
            if not isinstance(fu, dict):
                raise TypeError("Functional units must be a list of dictionaries.")
            refreshed = {refresh_node(key).key: amount for key, amount in fu.items()}
            inv[i] = refreshed

        ia = impact_categories or []

        # instruct the CalculationSetupController to create a CS with the new name
        bd.calculation_setups[name] = {"inv": inv, "ia": ia}

        log.info(f"New calculation setup: {name}")

        actions.CSOpen.run(name)

    @staticmethod
    def get_cs_name() -> str | None:
        """
        Prompt the user for a name for the new calculation setup.
        """
        # prompt the user to give a name for the new calculation setup
        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Create new calculation setup",
            "Name of new calculation setup:" + " " * 10,
        )

        # return if the user cancels or gives no name
        if not ok or not name:
            return None
        return name
