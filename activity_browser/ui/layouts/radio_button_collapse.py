from PySide2 import QtWidgets
from PySide2.QtCore import Signal, SignalInstance


class RadioButtonCollapseLayout(QtWidgets.QVBoxLayout):
    clicked: SignalInstance = Signal(str)

    def __init__(self):
        super().__init__()

        self._options = {}
        self.button_group = QtWidgets.QButtonGroup()

    def __getitem__(self, item):
        return self._options[item]

    def add_option(self, name: str, label: str, view: QtWidgets.QWidget | QtWidgets.QLayout):
        if isinstance(view, QtWidgets.QLayout):
            widget = ViewWidget()
            widget.setLayout(view)
            view = widget

        view.setHidden(True)

        button = QtWidgets.QRadioButton()

        if '*' in label:
            label = label.replace('*', '')
            button.setDisabled(True)

        if '#' in label:
            label = label.replace('#', '')
            button.setHidden(True)

        if '~' in label:
            label = label.replace('~', '')
            button.setDefault(True)

        button.setText(label)
        button.setObjectName(name)
        button.clicked.connect(self.update_collapse)

        self.button_group.addButton(button)
        self._options[name] = (button, view)
        self.addWidget(button)
        self.addWidget(view)

    def hide_all(self, uncheck=True):
        for button, view in self._options.values():
            view.setHidden(True)
        self.button_group.checkedButton().setChecked(not uncheck)

    def update_collapse(self):
        self.hide_all(uncheck=False)
        button_name = self.button_group.checkedButton().objectName()
        _, view_widget = self._options[button_name]
        view_widget.setHidden(False)

    def button(self, name: str) -> QtWidgets.QRadioButton:
        return self._options[name][0]

    def view(self, name: str) -> QtWidgets.QWidget | QtWidgets.QLayout:
        view = self._options[name][1]
        if isinstance(view, ViewWidget):
            view = view.layout()
        return view

    def current_option(self) -> None | str:
        button = self.button_group.checkedButton()
        if not button:
            return None
        return button.objectName()



class ViewWidget(QtWidgets.QWidget):
    """Only exists to differentiate between normal QWidgets and Widgets that exist to contain a layout"""
    def setLayout(self, layout):
        layout.setContentsMargins(0, 0, 0, 0)
        super().setLayout(layout)

