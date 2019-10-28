# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal as Signal

from activity_browser.app.bwutils import commontasks as bc


PARAMETER_STRING_ENUM = {
    0: "Project: Available to all other parameters",
    # 1: "Database: Available to Database and Activity parameters of the same database",
    1: "Activity: Available to Activity and exchange parameters within the group",
}
PARAMETER_FIELDS_ENUM = {
    0: ("name", "amount"),
    # 1: ("name", "amount", "database"),
    1: ("name", "amount"),
}


class ParameterWizard(QtWidgets.QWizard):
    complete = Signal(str, str, str)

    def __init__(self, key: tuple, parent=None):
        super().__init__(parent)

        self.key = key
        self.pages = {
            0: SelectParameterTypePage(self),
            1: CompleteParameterPage(self),
        }
        for i in sorted(self.pages):
            self.setPage(i, self.pages[i])
        self.show()

    def accept(self) -> None:
        """ Here is where we create the actual parameter.
        """
        selected = [
            self.field("btn_project"), self.field("btn_database"),
            self.field("btn_activity")
        ].index(True)

        data = {
            field: self.field(field) for field in PARAMETER_FIELDS_ENUM[selected]
        }
        # Copy data here as it gets removed from during param creation
        name = data.get("name")
        amount = str(data.get("amount"))
        p_type = "project"
        if selected == 0:
            bw.parameters.new_project_parameters([data])
        # elif selected == 1:
        #     db = data.pop("database")
        #     bw.parameters.new_database_parameters([data], db)
        #     p_type = "database ({})".format(db)
        elif selected == 1:
            group = bc.build_activity_group_name(self.key)
            data["database"] = self.key[0]
            data["code"] = self.key[1]
            bw.parameters.new_activity_parameters([data], group)
            p_type = "activity ({})".format(group)

        # On completing parameter creation, emit the values.
        # Inspired by: https://stackoverflow.com/a/9195041
        self.complete.emit(name, amount, p_type)
        super().accept()


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
        buttons = [QtWidgets.QRadioButton(PARAMETER_STRING_ENUM[i])
                   for i in sorted(PARAMETER_STRING_ENUM)]
        for b in buttons:
            box_layout.addWidget(b)
        # If we have a complete key, pre-select the activity parameter btn.
        buttons[1].setChecked(True) if all(self.key) else buttons[0].setChecked(True)

        # If we don't have a complete key, we can't create an activity parameter
        if self.key[1] == "":
            buttons[-1].setEnabled(False)
        box.setLayout(box_layout)
        layout.addWidget(box)
        self.setLayout(layout)

        self.registerField("btn_project", buttons[0])
        # self.registerField("btn_database", buttons[1])
        self.registerField("btn_activity", buttons[1])


class CompleteParameterPage(QtWidgets.QWizardPage):
    def __init__(self, parent):
        super().__init__(parent)
        self.setTitle("Fill out required values for the parameter")

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        box = QtWidgets.QGroupBox("Data:")
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
        selected = [
            self.field("btn_project"), self.field("btn_database"),
            self.field("btn_activity")
        ].index(True)

        self.amount.setText("0.0")
        if selected == 0:
            self.name.clear()
            self.database.setHidden(True)
            self.database_label.setHidden(True)
        # elif selected == 1:
        #     self.name.clear()
        #     self.database.clear()
        #     dbs = bw.databases.list
        #     self.database.insertItems(0, dbs)
        #     if self.key[0] != "":
        #         self.database.setCurrentIndex(
        #             dbs.index(self.key[0])
        #         )
        #     self.database.setHidden(False)
        #     self.database_label.setHidden(False)
        elif selected == 1:
            self.name.clear()
            self.database.setHidden(True)
            self.database_label.setHidden(True)
