from typing import Tuple

from qtpy import QtCore, QtGui, QtWidgets

from activity_browser import actions, application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils import commontasks as bc
from activity_browser.mod import bw2data as bd
from bw2data.parameters import ActivityParameter
from activity_browser.ui.icons import qicons

PARAMETER_STRINGS = (
    "Project: Available to all other parameters",
    "Database: Available to Database and Activity parameters of the same database",
    "Activity: Available to Activity and exchange parameters within the group",
)
PARAMETER_FIELDS = (
    ("name", "amount"),
    ("name", "amount", "database"),
    ("name", "amount"),
)


class ParameterNew(ABAction):
    """
    ABAction to create a new Parameter. Opens the ParameterWizard, returns if the wizard is canceled. Else,
    checks whether the name is valid, and then instructs the ParameterController to put the new parameter in the
    right group.
    """

    icon = qicons.add
    text = "New parameter..."

    @staticmethod
    @exception_dialogs
    def run(activity_key: Tuple[str, str]):
        # instantiate the ParameterWizard
        wizard = ParameterWizard(activity_key, application.main_window)

        # return if the wizard is canceled
        if wizard.exec_() != QtWidgets.QWizard.Accepted:
            return

        # gather wizard variables
        selection = wizard.selected
        data = wizard.param_data

        # check whether the name is valid, otherwise return
        name = data.get("name")
        if name[0] in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "-", "#"):
            error = QtWidgets.QErrorMessage()
            error.showMessage(
                "<p>Parameter names must not start with a digit, hyphen, or hash character</p>"
            )
            error.exec_()
            return

        # select the right group and instruct the controller to create the parameter there
        if selection == 0:
            bd.parameters.new_project_parameters([data])
        elif selection == 1:
            db = data.pop("database")
            bd.parameters.new_database_parameters([data], db)
        elif selection == 2:
            group = data.pop("group")
            bd.parameters.new_activity_parameters([data], group)


class ParameterWizard(QtWidgets.QWizard):
    complete = QtCore.Signal(str, str, str)

    def __init__(self, key: tuple, parent=None):
        super().__init__(parent)

        self.key = key
        self.pages = (
            SelectParameterTypePage(self),
            CompleteParameterPage(self),
        )
        for i, p in enumerate(self.pages):
            self.setPage(i, p)

    @property
    def selected(self) -> int:
        return self.pages[0].selected

    @property
    def param_data(self) -> dict:
        data = {field: self.field(field) for field in PARAMETER_FIELDS[self.selected]}
        if self.selected == 2:
            data["group"] = self._get_group()
            data["database"] = self.key[0]
            data["code"] = self.key[1]
        return data

    def _get_group(self):
        query = (ActivityParameter.database == self.key[0]) & (
            ActivityParameter.code == self.key[1]
        )

        if not ActivityParameter.select().where(query).count():
            actions.ParameterNewAutomatic.run([self.key])

        return ActivityParameter.get(query).group


class SelectParameterTypePage(QtWidgets.QWizardPage):
    def __init__(self, parent):
        super().__init__(parent)
        self.setTitle("Select the type of parameter to create.")

        self.key = parent.key

        layout = QtWidgets.QVBoxLayout()
        box = QtWidgets.QGroupBox("Types:")
        # Explicitly set the stylesheet to avoid parent classes overriding
        box.setStyleSheet(
            "QGroupBox {border: 1px solid gray; border-radius: 5px; margin-top: 7px; margin-bottom: 7px; padding: 0px}"
            "QGroupBox::title {top:-7 ex;left: 10px; subcontrol-origin: border}"
        )
        box_layout = QtWidgets.QVBoxLayout()
        self.button_group = QtWidgets.QButtonGroup()
        self.button_group.setExclusive(True)
        for i, s in enumerate(PARAMETER_STRINGS):
            button = QtWidgets.QRadioButton(s)
            self.button_group.addButton(button, i)
            box_layout.addWidget(button)
        # If we have a complete key, pre-select the activity parameter btn.
        if all(self.key):
            self.button_group.button(2).setChecked(True)
        elif self.key[0] != "":
            # default to database parameter is we have something.
            self.button_group.button(2).setEnabled(False)
            self.button_group.button(1).setChecked(True)
        else:
            # If we don't have a complete key, we can't create an activity parameter
            self.button_group.button(2).setEnabled(False)
            self.button_group.button(0).setChecked(True)
        box.setLayout(box_layout)
        layout.addWidget(box)
        self.setLayout(layout)

    @property
    def selected(self) -> int:
        return self.button_group.checkedId()


class CompleteParameterPage(QtWidgets.QWizardPage):
    def __init__(self, parent):
        super().__init__(parent)
        self.setTitle("Fill out required values for the parameter")
        self.parent = parent

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        box = QtWidgets.QGroupBox("Data:")
        box.setStyleSheet(
            "QGroupBox {border: 1px solid gray; border-radius: 5px; margin-top: 7px; margin-bottom: 7px; padding: 0px}"
            "QGroupBox::title {top:-7 ex;left: 10px; subcontrol-origin: border}"
        )
        grid = QtWidgets.QGridLayout()
        box.setLayout(grid)
        layout.addWidget(box)

        self.key = parent.key

        self.name_label = QtWidgets.QLabel("Name:")
        self.name = QtWidgets.QLineEdit()
        grid.addWidget(self.name_label, 0, 0)
        grid.addWidget(self.name, 0, 1)
        self.amount_label = QtWidgets.QLabel("Amount:")
        self.amount = QtWidgets.QLineEdit()
        locale = QtCore.QLocale(QtCore.QLocale.English)
        locale.setNumberOptions(QtCore.QLocale.RejectGroupSeparator)
        validator = QtGui.QDoubleValidator()
        validator.setLocale(locale)
        self.amount.setValidator(validator)
        grid.addWidget(self.amount_label, 1, 0)
        grid.addWidget(self.amount, 1, 1)
        self.database_label = QtWidgets.QLabel("Database:")
        self.database = QtWidgets.QComboBox()
        grid.addWidget(self.database_label, 2, 0)
        grid.addWidget(self.database, 2, 1)

        # Register fields for all possible values
        self.registerField("name*", self.name)
        self.registerField("amount", self.amount)
        self.registerField("database", self.database, "currentText")

    def initializePage(self) -> None:
        self.amount.setText("1.0")
        if self.parent.selected == 0:
            self.name.clear()
            self.database.setHidden(True)
            self.database_label.setHidden(True)
        elif self.parent.selected == 1:
            self.name.clear()
            self.database.clear()
            dbs = list(bd.databases)
            self.database.insertItems(0, dbs)
            if self.key[0] in dbs:
                self.database.setCurrentIndex(dbs.index(self.key[0]))
            self.database.setHidden(False)
            self.database_label.setHidden(False)
        elif self.parent.selected == 2:
            self.name.clear()
            self.database.setHidden(True)
            self.database_label.setHidden(True)
