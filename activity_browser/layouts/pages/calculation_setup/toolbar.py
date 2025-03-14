from qtpy import QtWidgets


class Toolbar(QtWidgets.QToolBar):
    def __init__(self, parent=None):
        super().__init__(parent)

        stretch = QtWidgets.QWidget(self)
        stretch.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.addWidget(stretch)
        self.addWidget(QtWidgets.QPushButton("Run calculation"))

