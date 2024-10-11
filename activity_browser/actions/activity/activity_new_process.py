from uuid import uuid4

from PySide2.QtWidgets import QDialog

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod.bw2data import Database, labels
from activity_browser.ui.icons import qicons
from activity_browser.ui.widgets.new_node_dialog import NewNodeDialog

from .activity_open import ActivityOpen


class ActivityNewProcess(ABAction):
    """
    ABAction to create a new activity. Prompts the user to supply a name. Returns if no name is supplied or if the user
    cancels. Otherwise, instructs the ActivityController to create a new activity.
    """

    icon = qicons.add
    text = "New process"

    @staticmethod
    @exception_dialogs
    def run(database_name: str):
        # ask the user to provide a name for the new activity
        dialog = NewNodeDialog(application.main_window)
        # if the user cancels, return
        if dialog.exec_() != QDialog.Accepted:
            return
        name, ref_product, unit, location = dialog.get_new_process_data()
        # if no name is provided, return
        if not name:
            return
        if ref_product == "":
            ref_product = name

        # create process
        new_proc_data = {
            "name": name,
            "reference product": ref_product,
            "unit": unit,
            "location": location,
            "type": "process",
        }
        database = Database(database_name)
        new_process = database.new_activity(code=uuid4().hex, **new_proc_data)
        new_process.save()

        # create reference product
        new_ref_prod_data = {
            "name": ref_product,
            "unit": unit,
            "location": location,
            "type": "product",
        }
        database = Database(database_name)
        new_ref_prod = database.new_activity(code=uuid4().hex, **new_ref_prod_data)
        new_ref_prod.save()

        # create new exchange
        new_exchange = new_process.new_edge(
            input = new_ref_prod,
            type = labels.production_edge_default,
            amount = 1,
            functional = True
        )
        new_exchange.save()

        ActivityOpen.run([new_process.key])
