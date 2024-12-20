from uuid import uuid4

from qtpy.QtWidgets import QDialog

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from bw2data import Database, get_activity, labels
from activity_browser.ui.icons import qicons
from activity_browser.ui.widgets.new_node_dialog import NewNodeDialog

from .activity_open import ActivityOpen


class ActivityNewProduct(ABAction):
    """
    ABAction to create a new activity. Prompts the user to supply a name. Returns if no name is supplied or if the user
    cancels. Otherwise, instructs the ActivityController to create a new activity.
    """

    icon = qicons.add
    text = "New product"

    @staticmethod
    @exception_dialogs
    def run(process_key: tuple):
        # ask the user to provide a name for the new activity
        dialog = NewNodeDialog(process=False, parent=application.main_window)
        # if the user cancels, return
        if dialog.exec_() != QDialog.Accepted:
            return
        name, _, unit, location = dialog.get_new_process_data()
        # if no name is provided, return
        if not name:
            return

        # create product
        new_prod_data = {
            "name": name,
            "unit": unit,
            "location": location,
            "type": "product",
        }
        database = Database(process_key[0])
        new_product = database.new_activity(code=uuid4().hex, **new_prod_data)
        new_product.save()

        process = get_activity(process_key)

        new_exchange = process.new_edge(
            input=new_product,
            type=labels.production_edge_default,
            amount=1,
            functional=True
        )
        new_exchange.save()

        ActivityOpen.run([new_product.key])
