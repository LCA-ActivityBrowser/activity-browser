from typing import List, Tuple

from PySide2 import QtWidgets
from peewee import IntegrityError

from activity_browser import application

from activity_browser.mod import bw2data as bd
from activity_browser.mod.bw2data.parameters import ActivityParameter
from activity_browser.actions.base import ABAction, exception_dialogs
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
    def run(activity_keys: List[Tuple]):
        for key in activity_keys:
            act = bd.get_activity(key)
            if act.get("type", "process") != "process":
                issue = f"Activity must be 'process' type, '{act.get('name')}' is type '{act.get('type')}'."
                QtWidgets.QMessageBox.warning(
                    application.main_window,
                    "Not allowed",
                    issue,
                    QtWidgets.QMessageBox.Ok,
                    QtWidgets.QMessageBox.Ok
                )
                return

            group = act._document.id
            count = ActivityParameter.select().where(ActivityParameter.group == group).count()

            row = {
                "name": "dummy_parameter",
                "amount": act.get("amount", 1.0),
                "formula": act.get("formula", ""),
                "database": key[0],
                "code": key[1],
            }

            bd.parameters.new_activity_parameters([row], group)


