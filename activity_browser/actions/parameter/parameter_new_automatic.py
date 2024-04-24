from typing import Union, Callable, List, Tuple

from PySide2 import QtCore, QtWidgets

from activity_browser import application

from activity_browser.bwutils import commontasks
from activity_browser.brightway import bd
from activity_browser.brightway.bw2data.parameters import ActivityParameter
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons

class ParameterNewAutomatic(ABAction):
    """
    ABAction for the automatic creation of a new parameter.

    TODO: Remove this action as it is automatic and not user interaction, should be done through e.g. a signal but
    TODO: will actually need to be reworked together with the parameters.
    """
    icon = qicons.add
    title = "New parameter..."
    activity_keys: List[Tuple]

    def __init__(self, activity_keys: Union[List[Tuple], Callable], parent: QtCore.QObject):
        super().__init__(parent, activity_keys=activity_keys)

    def onTrigger(self, toggled):
        for key in self.activity_keys:
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
            # Save the new parameter
            bd.parameters.new_activity_parameters([row], group)

