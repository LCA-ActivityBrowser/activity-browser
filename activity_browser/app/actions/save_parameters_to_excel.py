import os

import pandas as pd

from qtpy import QtCore, QtGui, QtWidgets

from activity_browser.app import application
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils.utils import Parameters


class SaveParametersToExcel(ABAction):
    """
    ABAction to export database(s) to Excel format (.xlsx).
    """
    text = "Save parameters to Excel (.xlsx)"
    tool_tip = "Save parameters to Excel format"

    @classmethod
    @exception_dialogs
    def run(cls, file_path: str = None):
        if file_path is None:
            suggestion = os.path.expanduser("~/parameters.xlsx")

            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                parent=application.main_window,
                caption=f'Export parameters to Excel',
                dir=suggestion,
                filter='Excel spreadsheet (*.xlsx);; All files (*.*)'
            )

        if not file_path:
            return

        data = [p[:3] for p in Parameters.from_bw_parameters()]
        df = pd.DataFrame(data, columns=["Name", "Group", "default"]).set_index("Name")
        df.to_excel(file_path)

        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(file_path))
