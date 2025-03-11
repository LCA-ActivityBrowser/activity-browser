from qtpy import QtWidgets


class ABComposite(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)

    def setLayout(self, layout):
        layout.setContentsMargins(0, 0, 0, 0)
        super().setLayout(layout)
