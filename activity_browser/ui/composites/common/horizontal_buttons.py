from PySide2 import QtWidgets
from PySide2.QtCore import Signal, SignalInstance

from activity_browser.ui.composites import ABComposite


class HorizontalButtonsComposite(ABComposite):
    """
    Layout that will display buttons horizontally. Will signal clicked together with the button name when a button is
    clicked
    """
    clicked: SignalInstance = Signal(str)

    def __init__(self, *args: str):
        """
        Construct any number of buttons given string-names as arguments. Append an * to set the button disabled by
        default, a # to hide the button by default or a ~ to set the button to be the default.
        """
        super().__init__()

        self._buttons = {}
        layout = QtWidgets.QHBoxLayout()

        # for each button_name in args, create a button and connect accordingly
        for button_name in args:
            button = QtWidgets.QPushButton()

            if '*' in button_name:
                # if * is in the label the button will be disabled by default
                button_name = button_name.replace('*', '')
                button.setDisabled(True)

            if '#' in button_name:
                # if # is in the label the button will be hidden by default
                button_name = button_name.replace('#', '')
                button.setHidden(True)

            if '~' in button_name:
                # if ~ is in the label the button wil be set as the default option
                button_name = button_name.replace('~', '')
                button.setDefault(True)

            # set up the button
            button.setText(button_name)
            button.setObjectName(button_name)

            # add the button accordingly
            self._buttons[button_name] = button

            layout.addWidget(button)

        self.setLayout(layout)

    def __getitem__(self, item) -> QtWidgets.QPushButton:
        """Buttons can be indexed based on their provided name"""
        return self._buttons[item]


if __name__ == '__main__':
    import sys
    from activity_browser import application

    comp = HorizontalButtonsComposite("Test", "*Test", "#Test", "~Test")
    comp.show()

    sys.exit(application.exec_())


