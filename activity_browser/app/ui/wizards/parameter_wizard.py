# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5 import QtCore, QtGui, QtWidgets

from activity_browser.app.bwutils import commontasks as bc


PARAMETER_STRING_ENUM = {
    0: "Project: Available to all other parameters",
    1: "Database: Available to Database and Activity parameters of the same database",
    2: "Activity: Available to Activity parameters within the same Group",
}
PARAMETER_FIELDS_ENUM = {
    0: ("name", "amount"),
    1: ("name", "amount", "database"),
    2: ("name", "amount", "group"),
}


class ParameterWizard(QtWidgets.QWizard):
    complete = QtCore.pyqtSignal(str, str, str)

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
        """ Here is where we create the actual parameter."""
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
        elif selected == 1:
            db = data.pop("database")
            bw.parameters.new_database_parameters([data], db)
            p_type = "database ({})".format(db)
        elif selected == 2:
            group = data.pop("group")
            data["database"] = self.key[0]
            data["code"] = self.key[1]
            bw.parameters.new_activity_parameters([data], group)
            p_type = "activity ({})".format(group)

        self.complete.emit(name, amount, p_type)
        super().accept()


class SelectParameterTypePage(QtWidgets.QWizardPage):
    def __init__(self, parent):
        super().__init__(parent)
        self.setTitle("Select the type of parameter to create.")

        self.key = parent.key

        layout = QtWidgets.QVBoxLayout()
        box = QtWidgets.QGroupBox("Types:")
        box_layout = QtWidgets.QVBoxLayout()
        buttons = [QtWidgets.QRadioButton(PARAMETER_STRING_ENUM[i])
                   for i in sorted(PARAMETER_STRING_ENUM)]
        for b in buttons:
            box_layout.addWidget(b)
        buttons[0].setChecked(True)
        # If we don't have a complete key, we can't create an activity parameter
        if self.key[1] == "":
            buttons[-1].setEnabled(False)
        box.setLayout(box_layout)
        layout.addWidget(box)
        self.setLayout(layout)

        self.registerField("btn_project", buttons[0])
        self.registerField("btn_database", buttons[1])
        self.registerField("btn_activity", buttons[2])


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
        self.group_label = QtWidgets.QLabel("Group:")
        self.group = QtWidgets.QLineEdit()
        grid.addWidget(self.group_label, 3, 0)
        grid.addWidget(self.group, 3, 1)

        # Register fields for all possible values
        self.registerField("name*", self.name)
        self.registerField("amount", self.amount)
        self.registerField("database", self.database, "currentText")
        self.registerField("group", self.group)

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
            self.group.setHidden(True)
            self.group_label.setHidden(True)
        elif selected == 1:
            self.name.clear()
            self.database.clear()
            dbs = bw.databases.list
            self.database.insertItems(0, dbs)
            if self.key[0] != "":
                self.database.setCurrentIndex(
                    dbs.index(self.key[0])
                )
            self.database.setHidden(False)
            self.database_label.setHidden(False)
            self.group.setHidden(True)
            self.group_label.setHidden(True)
        elif selected == 2:
            act = bw.get_activity(self.key)
            prep = bc.clean_activity_name(act.get("name"))
            self.name.clear()
            self.group.setText("{}_group".format(prep))
            self.database.setHidden(True)
            self.database_label.setHidden(True)
            self.group.setHidden(False)
            self.group_label.setHidden(False)
