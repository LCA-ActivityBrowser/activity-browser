from uuid import uuid4

from qtpy.QtWidgets import QDialog
import bw2data as bd

from activity_browser import application, bwutils
from activity_browser.actions.base import ABAction, exception_dialogs
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

        database = bd.Database(database_name)
        legacy_backend = bwutils.database_is_legacy(database_name)

        # create process
        new_proc_data = {
            "name": name,
            "location": location,
            "type": "process" if not legacy_backend else "processwithreferenceproduct",
        }

        if legacy_backend:
            new_proc_data["reference product"] = ref_product
            new_proc_data["unit"] = unit

        new_process: bd.Node = database.new_activity(code=uuid4().hex, **new_proc_data)
        new_process.save()

        if legacy_backend:
            new_process.new_exchange(
                input=new_process.key,
                type="production",
                amount=1.0,
            ).save()

        if not legacy_backend:
            # create reference product
            new_ref_prod_data = {
                "name": ref_product,
                "unit": unit,
                "location": location,
                "type": "product",
            }
            prod = new_process.new_product(code=uuid4().hex, **new_ref_prod_data)
            prod.save()

        ActivityOpen.run([new_process.key])
