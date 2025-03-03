from typing import List, Tuple

from peewee import IntegrityError
from qtpy import QtWidgets

from activity_browser import application
from activity_browser.bwutils import refresh_node
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from bw2data.parameters import ActivityParameter
from activity_browser.ui.icons import qicons


class ParameterNewAutomatic(ABAction):
    """
    ABAction for the automatic creation of a new parameter.

    TODO: Remove this action as it is automatic and not user interaction, should be done through e.g. a signal but
    TODO: will actually need to be reworked together with the parameters.
    """

    icon = qicons.add
    text = "New parameter..."

    @staticmethod
    @exception_dialogs
    def run(activities: List[tuple | int | bd.Node]):
        activities = [refresh_node(x) for x in activities]

        for act in activities:
            if act.get("type", "process") not in bd.labels.lci_node_types:
                issue = f"Activity must be 'process' type, '{act.get('name')}' is type '{act.get('type')}'."
                QtWidgets.QMessageBox.warning(
                    application.main_window,
                    "Not allowed",
                    issue,
                    QtWidgets.QMessageBox.Ok,
                    QtWidgets.QMessageBox.Ok,
                )
                return

            group = act.id
            row = {
                "name": "dummy_parameter",
                "amount": act.get("amount", 1.0),
                "formula": act.get("formula", ""),
                "database": act.get("database", ""),
                "code": act.get("code", ""),
            }

            bd.parameters.new_activity_parameters([row], group)
