from qtpy.QtWidgets import QProgressDialog

from activity_browser import application
from activity_browser.mod.tqdm import qt_tqdm
from activity_browser.mod.pyprind import qt_pyprind


class ABProgressDialog(QProgressDialog):

    @classmethod
    def get_connected_dialog(cls, title: str) -> "ABProgressDialog":
        dialog = cls(application.main_window)
        dialog.setWindowTitle(title)
        dialog.setLabelText("Initializing")
        dialog.setAutoReset(False)
        dialog.setCancelButton(None)

        qt_tqdm.updated.connect(dialog._receive_update)
        qt_pyprind.updated.connect(dialog._receive_update)

        return dialog

    def _receive_update(self, title: str, value: int):
        self.setLabelText(title)
        self.setValue(value)
