from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt


class ABCloseButton(QtWidgets.QWidget):
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


class ABMinimizeButton(QtWidgets.QWidget):
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
