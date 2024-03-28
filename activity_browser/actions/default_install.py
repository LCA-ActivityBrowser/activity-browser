from activity_browser import application
from .base import ABAction
from ..ui.widgets import DefaultBiosphereDialog, EcoinventVersionDialog
from ..ui.icons import qicons


class DefaultInstall(ABAction):
    """
    ABAction to install all the default data: biosphere, IC's etcetera.
    """
    icon = qicons.import_db
    title = "Add default data (biosphere flows and impact categories)"

    dialog: DefaultBiosphereDialog

    def onTrigger(self, toggled):
        version_dialog = EcoinventVersionDialog(application.main_window)
        if version_dialog.exec_() != EcoinventVersionDialog.Accepted: return
        version = version_dialog.options.currentText()

        self.dialog = DefaultBiosphereDialog(version[:3], application.main_window)  # only read Major/Minor part of version
        self.dialog.show()
