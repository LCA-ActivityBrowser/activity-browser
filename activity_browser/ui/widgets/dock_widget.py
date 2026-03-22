from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt


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
            button = CloseButton(self)
            button.clicked.connect(self.close)
        else:
            button = MinimizeButton(self)
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


class CloseButton(QtWidgets.QWidget):
    """Custom close button with hover effect."""
    clicked: QtCore.SignalInstance = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)


        self.label = QtWidgets.QLabel("×", self)

        self.label.setFont(QtGui.QFont("Arial", 12, QtGui.QFont.Bold))
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFixedSize(16, 16)
        self.label.mousePressEvent = lambda event: self.clicked.emit()

        self.label.setStyleSheet("""
            QLabel {
                border-radius: 8px;
                background-color: transparent;
            }
            QLabel:hover {
                background-color: rgba(255, 0, 0, 0.5);
            }
        """)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(5, 0, 0, 0)
        layout.addWidget(self.label)
        self.setLayout(layout)


class MinimizeButton(QtWidgets.QWidget):
    """Custom close button with hover effect."""
    clicked: QtCore.SignalInstance = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.label = QtWidgets.QLabel("-", self)

        self.label.setFont(QtGui.QFont("Arial", 12, QtGui.QFont.Bold))
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFixedSize(16, 16)
        self.label.mousePressEvent = lambda event: self.clicked.emit()

        self.setStyleSheet("""
            QLabel {
                border-radius: 8px;
                background-color: transparent;
            }
            QLabel:hover {
                background-color: rgba(42, 157, 244, 0.5);
            }
        """)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(5, 0, 0, 0)
        layout.addWidget(self.label)
        self.setLayout(layout)


def mousePressEvent(self, event):
    if event.button() == Qt.LeftButton:
        self.drag_start_pos = event.pos()


def mouseMoveEvent(self, event):
    if not self.drag_start_pos:
        return

    # Check if mouse moved beyond threshold
    if (event.pos() - self.drag_start_pos).manhattanLength() > QtWidgets.QApplication.startDragDistance():
        index = self.tabAt(self.drag_start_pos)
        if index >= 0:
            startDrag(self, index)

def startDrag(self, index):
    """Start dragging a tab."""
    print("Dragging success")
