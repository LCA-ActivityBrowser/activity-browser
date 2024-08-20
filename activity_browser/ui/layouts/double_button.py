from PySide2 import QtWidgets
from PySide2.QtCore import Signal, SignalInstance


class HorizontalButtonsLayout(QtWidgets.QHBoxLayout):
    clicked: SignalInstance = Signal(str)

    def __init__(self, *args: str):
        super().__init__()

        self._buttons = {}

        for button_name in args:
            button = QtWidgets.QPushButton()

            if '*' in button_name:
                button_name = button_name.replace('*', '')
                button.setDisabled(True)

            if '#' in button_name:
                button_name = button_name.replace('#', '')
                button.setHidden(True)

            if '~' in button_name:
                button_name = button_name.replace('~', '')
                button.setDefault(True)

            button.setText(button_name)
            button.setObjectName(button_name)

            self._buttons[button_name] = button
            self.addWidget(button)

    def __getitem__(self, item):
        return self._buttons[item]
