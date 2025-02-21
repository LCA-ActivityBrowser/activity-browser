from uuid import uuid4

from qtpy.QtWidgets import QDialog

from bw2data import Database, get_activity, labels

from bw_functional import Process

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.ui.widgets.new_node_dialog import NewNodeDialog

from .activity_open import ActivityOpen


class ActivityNewProduct(ABAction):
    """
    ABAction to create a new activity. Prompts the user to supply a name. Returns if no name is supplied or if the user
    cancels. Otherwise, instructs the ActivityController to create a new activity.
    """

    icon = qicons.add
    text = "New function"

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

        process = get_activity(key=process_key)
        assert isinstance(process, Process), "Cannot create new product for non-process type"

        # create product
        new_prod_data = {
            "name": name,
            "unit": unit,
            "location": location,
            "type": "product",
        }
        new_product = process.new_product(code=uuid4().hex, **new_prod_data)
        new_product.save()
