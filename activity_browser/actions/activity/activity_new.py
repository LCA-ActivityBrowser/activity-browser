from uuid import uuid4
from typing import Union, Callable

from PySide2 import QtWidgets, QtCore

from activity_browser import application, database_controller
from activity_browser.ui.icons import qicons
from activity_browser.actions.base import ABAction


class ActivityNew(ABAction):
    """
    ABAction to create a new activity. Prompts the user to supply a name. Returns if no name is supplied or if the user
    cancels. Otherwise, instructs the ActivityController to create a new activity.
    """
    icon = qicons.add
    title = "New activity"
    database_name: str

    def __init__(self, database_name: Union[str, Callable], parent: QtCore.QObject):
        super().__init__(parent, database_name=database_name)

    def onTrigger(self, toggled):
        # ask the user to provide a name for the new activity
        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Create new technosphere activity",
            "Please specify an activity name:" + " " * 10,
            QtWidgets.QLineEdit.Normal
        )

        # if no name is provided, or the user cancels, return
        if not ok or not name: return

        # create activity
        data = {
            "name": name,
            "reference product": name,
            "unit": "unit",
            "type": "process"
        }
        database = database_controller.get(self.database_name)
        new_act = database.new_activity(code=uuid4().hex, **data)

        # create the production exchange
        production_exchange = new_act.new_exchange(input=new_act, amount=1, type="production")
        production_exchange.save()
