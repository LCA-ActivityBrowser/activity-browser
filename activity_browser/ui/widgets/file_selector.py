from qtpy import QtWidgets
from qtpy.QtCore import Signal, SignalInstance


class ABFileSelector(QtWidgets.QWidget):
    textChanged: SignalInstance = Signal(str)

    def __init__(self, parent=None, filter=""):
        super().__init__(parent)

        self.filter = filter

        self.line_edit = QtWidgets.QLineEdit(self)
        self.line_edit.textChanged.connect(self.textChanged.emit)

        self.button = QtWidgets.QPushButton("Browse", self)
        self.button.clicked.connect(self.select_file)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.line_edit)
        layout.addWidget(self.button)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def select_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select File", filter=self.filter)
        if file_path:
            self.line_edit.setText(file_path)

    def text(self):
        return self.line_edit.text()

    def setText(self, text):
        self.line_edit.setText(text)
