from qtpy import QtWidgets
from activity_browser import actions


class Toolbar(QtWidgets.QToolBar):
    def __init__(self, cs_name: str, parent=None):
        super().__init__(parent)

        stretch = QtWidgets.QWidget(self)
        stretch.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.run_action = actions.CSCalculate.get_QButton(cs_name)

        self.addWidget(stretch)
        self.addWidget(self.run_action)

