from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.wizards import ProjectSetupWizard
from activity_browser.ui.icons import qicons


class DefaultInstall(ABAction):
    """
    ABAction to install all the default data: biosphere, IC's etcetera.
    """

    icon = qicons.import_db
    text = "Set up your project with default data"

    @staticmethod
    @exception_dialogs
    def run():
        ProjectSetupWizard(application.main_window).show()
