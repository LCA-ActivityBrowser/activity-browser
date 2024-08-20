from PySide2 import QtWidgets


class RadioButtonCollapseLayout(QtWidgets.QVBoxLayout):
    """
    Layout that shows different 'views' depending on what radio button is clicked. After initialization you may
    add different options through the add_option method. These are displayed horizontally and only shown when the
    corresponding radiobutton is clicked.
    """

    def __init__(self):
        super().__init__()

        self._options = {}
        self.button_group = QtWidgets.QButtonGroup()

    def __getitem__(self, item):
        """Give option name, returns tuple of the corresponding button and view_widget"""
        return self._options[item]

    def add_option(self, name: str, label: str, view: QtWidgets.QWidget | QtWidgets.QLayout):
        """
        Add a collapsible option to the layout.

        Parameters
        ----------
            name : `str`
                Simple name that can be used to identify the option.
            label : `str`
                Label to be shown next to the radio button. Append a * to disable the button, a # to hide the button,
                or a ~ to select the button.
            view : `QtWidgets.QWidget | QtWidgets.QLayout`
                Either a QWidget or a QLayout that will be shown once the radio button is checked by the user
        """
        # QLayouts cannot be hidden, so we need to wrap it into a QtWidget (Or ViewWidget in this case)
        if isinstance(view, QtWidgets.QLayout):
            widget = ViewWidget()
            widget.setLayout(view)
            view = widget

        # set the view hidden by default
        view.setHidden(True)

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
        button.clicked.connect(self.update_collapse)

        # add the button and view to the correct locations
        self.button_group.addButton(button)
        self._options[name] = (button, view)
        self.addWidget(button)
        self.addWidget(view)

    def hide_all(self, uncheck=True):
        """
        Hides all the views, unchecking all the radio_buttons by default.
        """
        for button, view in self._options.values():
            view.setHidden(True)
        self.button_group.checkedButton().setChecked(not uncheck)

    def update_collapse(self):
        """
        Slot that check what radio button is checked and only unhides the associated view
        """
        # first hide all
        self.hide_all(uncheck=False)

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
        view = self._options[name][1]

        # if the instance is a ViewWidget, return the associated layout
        if isinstance(view, ViewWidget):
            view = view.layout()
        return view

    def current_option(self) -> None | str:
        """Returns the name of the currently checked option. Returns None if nothing is selected"""
        button = self.button_group.checkedButton()
        if not button:
            return None
        return button.objectName()


class ViewWidget(QtWidgets.QWidget):
    """Only exists to differentiate between normal QWidgets and Widgets that exist to contain a layout"""
    def setLayout(self, layout):
        """This will remove any unwanted margins that come from packing the layout inside another widget"""
        layout.setContentsMargins(0, 0, 0, 0)
        super().setLayout(layout)

