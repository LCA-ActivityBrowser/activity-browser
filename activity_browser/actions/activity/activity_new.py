from uuid import uuid4

from PySide2 import QtWidgets

from activity_browser import application
from activity_browser.mod.bw2data import Database
from activity_browser.ui.icons import qicons
from activity_browser.actions.base import ABAction, exception_dialogs

from .activity_open import ActivityOpen


class ActivityNew(ABAction):
    """
    ABAction to create a new activity. Prompts the user to supply a name. Returns if no name is supplied or if the user
    cancels. Otherwise, instructs the ActivityController to create a new activity.
    """
    icon = qicons.add
    text = "New activity"

    @staticmethod
    @exception_dialogs
    def run(database_name: str):
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
        database = Database(database_name)
        new_act = database.new_activity(code=uuid4().hex, **data)
        new_act.save()

        # create the production exchange
        production_exchange = new_act.new_exchange(input=new_act, amount=1, type="production")
        production_exchange.save()

        ActivityOpen.run([new_act.key])
