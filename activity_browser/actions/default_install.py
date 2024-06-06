from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.widgets import DefaultBiosphereDialog, EcoinventVersionDialog
from activity_browser.ui.icons import qicons


class DefaultInstall(ABAction):
    """
    ABAction to install all the default data: biosphere, IC's etcetera.
    """
    icon = qicons.import_db
    text = "Add default data (biosphere flows and impact categories)"

    @staticmethod
    @exception_dialogs
    def run():
        version_dialog = EcoinventVersionDialog(application.main_window)
        if version_dialog.exec_() != EcoinventVersionDialog.Accepted: return
        version = version_dialog.options.currentText()

        DefaultBiosphereDialog(version[:3], application.main_window).show()  # only read Major/Minor part of version
