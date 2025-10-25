from logging import getLogger

from qtpy import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons
from activity_browser.ui import widgets

from .method_open import MethodOpen

log = getLogger(__name__)


class MethodNew(ABAction):
    """
    ABAction to create a new, empty impact category and open it in edit mode.
    
    This action prompts the user for a new method name using a list edit dialog,
    validates the input, creates an empty method in Brightway2, and opens it
    in the ImpactCategoryDetails page in edit mode so the user can start adding
    characterization factors.
    
    Steps:
    - Open a dialog to prompt the user for the new method name (as a tuple).
    - Validate the new name to ensure it is not empty and does not already exist.
    - Create and register a new empty method in Brightway2.
    - Open the method in the ImpactCategoryDetails page.
    - Set the page to edit mode so the user can add characterization factors.
    """

    icon = qicons.add
    text = "New impact category"

    @staticmethod
    @exception_dialogs
    def run():
        # Open dialog to get new method name
        dialog = widgets.ABListEditDialog(("New Impact Category",), parent=application.main_window)
        dialog.setWindowTitle("New Impact Category")
        
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        new_name = dialog.get_data(as_tuple=True)

        # Validate new name
        if len(new_name) == 0:
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "Invalid Name",
                "Impact category name cannot be empty.",
            )
            return

        if new_name in bd.methods:
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "Name Already Exists",
                f"An impact category with the name '{' | '.join(new_name)}' already exists.",
            )
            return

        # Create new empty method
        method = bd.Method(new_name)
        method.register()
        method.write([])  # Write empty list of characterization factors
        
        log.info(f"Created new impact category: {new_name}")

        # Open the method in the ImpactCategoryDetails page
        from activity_browser.layouts import pages
        
        page = pages.ImpactCategoryDetailsPage(new_name)
        central = application.main_window.centralWidget()
        central.addToGroup("Characterization Factors", page)
        
        # Set the page to edit mode
        page.is_editable = True
        page.sync()
