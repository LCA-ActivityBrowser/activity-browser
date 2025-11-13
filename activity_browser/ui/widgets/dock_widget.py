from qtpy import QtWidgets, QtGui
from qtpy.QtCore import Qt

from .buttons import ABCloseButton, ABMinimizeButton


class HideMode:
    Close = 1
    Hide = 2


class ABDockWidget(QtWidgets.QDockWidget):
    updatingTabBar = False
    HideMode = HideMode

    def __init__(self, title: str, parent: QtWidgets.QMainWindow, mode=HideMode.Close) -> None:
        super().__init__(title, parent)
        self.main = parent
        self.title = title

        self._updating_tab_bar = ""

        self._hide_mode = mode
        if self._hide_mode == HideMode.Close:
            self.setAttribute(Qt.WA_DeleteOnClose)

        self.title_bar = TitleBar(title, self.button(), self)
        self.setTitleBarWidget(self.title_bar)

    def setWidget(self, widget):
        super().setWidget(widget)
        widget.destroyed.connect(self.deleteLater)
        self.setObjectName(f"dockwidget-{widget.objectName()}")

    def button(self):
        if self._hide_mode == HideMode.Close:
            button = ABCloseButton(self)
            button.clicked.connect(self.close)
        else:
            button = ABMinimizeButton(self)
            button.clicked.connect(self.hide)
        return button


class TitleBar(QtWidgets.QWidget):
    def __init__(self, title: str, button, parent=None):
        super().__init__(parent)

        self.label = QtWidgets.QLabel(title, self)
        font = self.font()
        font.setPointSize(font.pointSize() + 1)
        self.label.setFont(font)
        self.label.setCursor(QtGui.QCursor(Qt.CursorShape.SizeAllCursor))

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(button)
        self.setLayout(layout)

    def set_button(self, button):
        layout = self.layout()
        w = layout.itemAt(2).widget()
        layout.replaceWidget(w, button)
        layout.update()
        w.deleteLater()


