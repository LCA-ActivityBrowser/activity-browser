from qtpy import QtWidgets
from qtpy.QtCore import Signal, SignalInstance


class ABRadioButtonCollapser(QtWidgets.QWidget):
    """
    Composite that shows different 'views' depending on what radio button is clicked. After initialization you may
    add different options through the add_option method. These are displayed horizontally and only shown when the
    corresponding radiobutton is clicked.
    """
    buttonClicked: SignalInstance = Signal()
    buttonPressed: SignalInstance = Signal()
    buttonReleased: SignalInstance = Signal()
    buttonToggled: SignalInstance = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._options = {}
        self.button_group = QtWidgets.QButtonGroup()

        self.button_group.buttonClicked.connect(lambda: self.buttonClicked.emit())
        self.button_group.buttonPressed.connect(lambda: self.buttonPressed.emit())
        self.button_group.buttonReleased.connect(lambda: self.buttonReleased.emit())
        self.button_group.buttonToggled.connect(lambda: self.buttonToggled.emit())

        self.setLayout(QtWidgets.QVBoxLayout())

    def __getitem__(self, item):
        """Give option name, returns tuple of the corresponding button and view_widget"""
        return self._options[item]

    def addOption(self, name: str, label: str, w: QtWidgets.QWidget):
        """
        Add a collapsible option to the layout.

        Parameters
        ----------
            name : `str`
                Simple name that can be used to identify the option.
            label : `str`
                Label to be shown next to the radio button. Append a * to disable the button, a # to hide the button,
                or a ~ to select the button.
            view : `QtWidgets.QWidget`
                A QWidget that will be shown once the radio button is checked by the user
        """
        # set the view hidden by default
        w.setHidden(True)

        button = QtWidgets.QRadioButton()

        if '*' in label:
            # if * is in the label the radiobutton will be disabled by default
            label = label.replace('*', '')
            button.setDisabled(True)

        if '#' in label:
            # if # is in the label the button will be hidden by default
            label = label.replace('#', '')
            button.setHidden(True)

        if '~' in label:
            # if ~ is in the label the button wil be set as the default option
            label = label.replace('~', '')
            button.setDefault(True)

        # set up the button
        button.setText(label)
        button.setObjectName(name)
        button.clicked.connect(self.updateCollapse)

        # add the button and view to the correct locations
        self.button_group.addButton(button)
        self._options[name] = (button, w)

        self.layout().addWidget(button)
        self.layout().addWidget(w)

    def hideAll(self, uncheck=True):
        """
        Hides all the views, unchecking all the radio_buttons by default.
        """
        for button, view in self._options.values():
            view.setHidden(True)
        self.button_group.checkedButton().setChecked(not uncheck)

    def updateCollapse(self):
        """
        Slot that check what radio button is checked and only unhides the associated view
        """
        # first hide all
        self.hideAll(uncheck=False)

        # get the name of the checked button
        button_name = self.button_group.checkedButton().objectName()

        # show the associated view
        _, view_widget = self._options[button_name]
        view_widget.setHidden(False)

    def button(self, name: str) -> QtWidgets.QRadioButton:
        """Returns the button associated with the given name"""
        return self._options[name][0]

    def view(self, name: str) -> QtWidgets.QWidget | QtWidgets.QLayout:
        """Returns the view associated with the given name"""
        return self._options[name][1]

    def currentOption(self) -> None | str:
        """Returns the name of the currently checked option. Returns None if nothing is selected"""
        button = self.button_group.checkedButton()
        if not button:
            return None
        return button.objectName()
