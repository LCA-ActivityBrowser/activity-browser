# -*- coding: utf-8 -*-
from os import devnull

from asteval import Interpreter
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Signal, Slot

from activity_browser import actions, signals


class CalculatorButtons(QtWidgets.QWidget):
    """A custom layout containing calculator buttons, emits a signal
    for each button pressed.
    """

    button_press = Signal(str)
    clear = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.explain_text = """
In addition to the other buttons on this calculator, the parameter formula
can make use of a large number of Python and Numpy functions, with Numpy
overriding Python where the function names are the same.

For a more complete list see the `math` module in the Python documentation
or `ufuncs` in de Numpy documentation.

Keep in mind that the result of a formula must be a scalar value!
"""
        rows = [
            [
                ("+", "Add", lambda: self.button_press.emit(" + ")),
                ("-", "Subtract", lambda: self.button_press.emit(" - ")),
                ("*", "Multiply", lambda: self.button_press.emit(" * ")),
            ],
            [
                ("/", "Divide", lambda: self.button_press.emit(" / ")),
                ("x²", "X to the power of 2", lambda: self.button_press.emit(" ** 2 ")),
                ("More...", "Additional functions", self.explanation),
            ],
        ]
        # Construct the layout from the list of lists above.
        layout = QtWidgets.QHBoxLayout()
        layout.addStretch(1)
        for row in rows:
            bar = QtWidgets.QToolBar()
            bar.setOrientation(QtCore.Qt.Vertical)
            for btn in row:
                w = QtWidgets.QPushButton(btn[0])
                w.setToolTip(btn[1])
                w.pressed.connect(btn[2])
                w.setFixedSize(50, 50)
                bar.addWidget(w)
            layout.addWidget(bar)
        layout.addStretch(1)
        self.setLayout(layout)

    @Slot()
    def explanation(self):
        return QtWidgets.QMessageBox.question(
            self,
            "More...",
            self.explain_text,
            QtWidgets.QMessageBox.Ok,
            QtWidgets.QMessageBox.Ok,
        )


class FormulaDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, flags=QtCore.Qt.Window):
        super().__init__(parent=parent, f=flags)
        self.setWindowTitle("Build a formula")
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.interpreter = None
        self.key = ("", "")

        # 6 broad by 6 deep.
        grid = QtWidgets.QGridLayout(self)
        self.text_field = QtWidgets.QLineEdit(self)
        self.text_field.textChanged.connect(self.validate_formula)
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        self.buttons.setSizePolicy(
            QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Preferred,
                QtWidgets.QSizePolicy.ButtonBox,
            )
        )
        self.parameters = QtWidgets.QTableView(self)
        model = QtGui.QStandardItemModel(self)
        self.parameters.setModel(model)
        completer = QtWidgets.QCompleter(model, self)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.text_field.setCompleter(completer)
        self.parameters.doubleClicked.connect(self.append_parameter_name)

        self.new_parameter_button = actions.ParameterNew.get_QButton(self.get_key)

        self.calculator = CalculatorButtons(self)
        self.calculator.button_press.connect(self.text_field.insert)
        self.calculator.clear.connect(self.text_field.clear)

        grid.addWidget(self.text_field, 0, 0, 5, 1)
        grid.addWidget(self.buttons, 5, 0, 1, 1)
        grid.addWidget(self.calculator, 0, 1, 5, 1)
        grid.addWidget(self.parameters, 0, 2, 5, 1)
        grid.addWidget(self.new_parameter_button, 5, 2, 1, 1)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        signals.added_parameter.connect(self.append_parameter)
        self.show()

    def insert_parameters(self, items) -> None:
        """Take the given list of parameter names, amounts and types, insert
        them into the model.
        """
        model = self.parameters.model()
        model.clear()
        model.setHorizontalHeaderLabels(["Name", "Amount", "Type"])
        for x, item in enumerate(items):
            for y, value in enumerate(item):
                model_item = QtGui.QStandardItem(str(value))
                model_item.setEditable(False)
                model.setItem(x, y, model_item)
        self.parameters.resizeColumnsToContents()

    @Slot(str, str, str, name="appendParameter")
    def append_parameter(self, name: str, amount: str, p_type: str) -> None:
        """Catch new parameters from the wizard and add them to the list."""
        model = self.parameters.model()
        x = model.rowCount()
        for y, i in enumerate([name, amount, p_type]):
            item = QtGui.QStandardItem(i)
            item.setEditable(False)
            model.setItem(x, y, item)

        # Also include the new parameter in the interpreter.
        if self.interpreter:
            self.interpreter.symtable.update({name: float(amount)})

    def insert_interpreter(self, interpreter: Interpreter) -> None:
        self.interpreter = interpreter

    def insert_key(self, key: tuple) -> None:
        """The key consists of two strings, no more, no less."""
        self.key = key

    def get_key(self) -> tuple:
        return self.key

    @property
    def formula(self) -> str:
        """Look into the text_field and return the formula."""
        return self.text_field.text().strip()

    @formula.setter
    def formula(self, value) -> None:
        """Take the formula and set it to the text_field widget."""
        if value is None:
            self.text_field.clear()
        else:
            self.text_field.setText(str(value))

    @Slot(QtCore.QModelIndex)
    def append_parameter_name(self, index: QtCore.QModelIndex) -> None:
        """Take the index from the parameters table and append the parameter
        name to the formula.
        """
        param_name = self.parameters.model().index(index.row(), 0).data()
        self.text_field.insert(param_name)

    @Slot()
    def validate_formula(self) -> None:
        """Qt slot triggered whenever a change is detected in the text_field."""
        self.text_field.blockSignals(True)
        if self.interpreter:
            formula = self.text_field.text().strip()
            # Do not write massive amounts of errors to stderr if the user
            # is busy writing.
            with open(devnull, "w") as errfile:
                self.interpreter.err_writer = errfile
                self.interpreter(formula)
                if len(self.interpreter.error) > 0:
                    self.buttons.button(QtWidgets.QDialogButtonBox.Save).setEnabled(
                        False
                    )
                else:
                    self.buttons.button(QtWidgets.QDialogButtonBox.Save).setEnabled(
                        True
                    )
        self.text_field.blockSignals(False)


class FormulaDelegate(QtWidgets.QStyledItemDelegate):
    """An extensive delegate to allow users to build and validate formulas
    The delegate spawns a dialog containing:
      - An editable textfield for the formula.
      - A listview containing parameter names that can be used in the formula
      - Ok and Cancel buttons, on Ok, validate the formula before saving
    For hardmode: also allow the user to create a new parameter from WITHIN
    the delegate dialog itself. Requiring us to also include refreshing
    for the parameter list.
    """

    ACCEPTED_TABLES = {
        "project_parameter",
        "database_parameter",
        "activity_parameter",
        "product",
        "technosphere",
        "biosphere",
    }

    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QWidget(parent)
        dialog = FormulaDialog(editor, QtCore.Qt.Window)
        dialog.accepted.connect(lambda: self.commitData.emit(editor))
        # dialog.rejected.connect(signals.parameters_changed.emit)
        return editor

    def setEditorData(self, editor: QtWidgets.QWidget, index: QtCore.QModelIndex):
        """Populate the editor with data if editing an existing field."""
        dialog = editor.findChild(FormulaDialog)
        data = index.data(QtCore.Qt.DisplayRole)

        parent = self.parent()
        # Check which table is asking for a list
        if getattr(parent, "table_name", "") in self.ACCEPTED_TABLES:
            items = parent.get_usable_parameters()
            dialog.insert_parameters(items)
            dialog.formula = data
            interpreter = parent.get_interpreter()
            dialog.insert_interpreter(interpreter)
            # Now see if we can construct a (partial) key
            if hasattr(parent, "key"):
                # This works for exchange tables.
                dialog.insert_key(parent.key)
            elif hasattr(parent, "get_key"):
                dialog.insert_key(parent.get_key())

    def setModelData(
        self,
        editor: QtWidgets.QWidget,
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex,
    ):
        """Take the editor, read the given value and set it in the model.

        If the new formula is the same as the existing one, do not call setData
        """
        dialog = editor.findChild(FormulaDialog)
        if dialog.result() == QtWidgets.QDialog.Rejected:
            # Cancel was clicked, do not store anything.
            return
        model.setData(index, dialog.formula, QtCore.Qt.EditRole)
