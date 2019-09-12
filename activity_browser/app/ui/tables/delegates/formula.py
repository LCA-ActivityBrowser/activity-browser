# -*- coding: utf-8 -*-
from os import devnull

from asteval import Interpreter
from PyQt5 import QtCore, QtGui, QtWidgets

from ...icons import qicons


class CalculatorButtons(QtWidgets.QWidget):
    """ A custom layout containing calculator buttons, emits a signal
    for each button pressed.
    """
    button_press = QtCore.pyqtSignal(str)
    clear = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.explain_text = """
In addition to the other buttons on this calculator, the parameter formula
can include a large amount of Python and Numpy functions, with Numpy
overriding Python where the function names are the same. Below are some examples:

sqrt(x)
    Return the square root of x.

sin(x)
    Return the sine of x (measured in radians).

arange([start,] stop[, step,])
    Return evenly spaced values within a given interval.
    eg. arange(3) = [0, 1, 2]

max(x)
    Returns the maximum of an array.

For a more complete list see the `math` module in the Python documentation
or the `ufuncs` in de Numpy documentation.
"""
        rows = [
            [
                ("+", "Add", lambda: self.button_press.emit(" + ")),
                ("-", "Subtract", lambda: self.button_press.emit(" - ")),
                ("X", "Multiply", lambda: self.button_press.emit(" * ")),
                ("%", "Divide", lambda: self.button_press.emit(" / ")),
            ],
            [
                ("x²", "X to the power of 2", lambda: self.button_press.emit(" ** 2 ")),
                ("Xⁿ", "X to the power of N", lambda: self.button_press.emit(" ** ")),
                ("mod", "Modulo", lambda: self.button_press.emit(" % ")),
                ("C", "Clear Formula", lambda: self.clear.emit()),
            ],
            [
                ("More...", "Additional functions", self.explanation),
            ],
        ]
        # Construct the layout from the list of lists above.
        layout = QtWidgets.QVBoxLayout()
        layout.addStretch(1)
        for row in rows:
            bar = QtWidgets.QToolBar()
            for btn in row:
                w = QtWidgets.QPushButton(btn[0])
                w.setToolTip(btn[1])
                w.pressed.connect(btn[2])
                w.setFixedSize(50, 50)
                bar.addWidget(w)
            layout.addWidget(bar)
        layout.addStretch(1)
        self.setLayout(layout)

    @QtCore.pyqtSlot()
    def explanation(self):
        return QtWidgets.QMessageBox.question(
            self, "More...", self.explain_text, QtWidgets.QMessageBox.Ok,
            QtWidgets.QMessageBox.Ok
        )


class FormulaDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, flags=QtCore.Qt.Window):
        super().__init__(parent=parent, flags=flags)
        self.setWindowTitle("Build a formula")
        self.interpreter = None

        # 6 broad by 6 deep.
        grid = QtWidgets.QGridLayout(self)
        self.text_field = QtWidgets.QPlainTextEdit(self)
        self.text_field.textChanged.connect(self.validate_formula)
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        self.buttons.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.ButtonBox
        ))
        self.parameters = QtWidgets.QTableView(self)
        model = QtGui.QStandardItemModel(self)
        self.parameters.setModel(model)
        self.parameters.doubleClicked.connect(self.append_parameter_name)
        self.new_parameter = QtWidgets.QPushButton(
            qicons.add, "New parameter", self
        )
        self.new_parameter.setEnabled(False)

        self.calculator = CalculatorButtons(self)
        self.calculator.button_press.connect(self.append_calculator)
        self.calculator.clear.connect(self.clear_formula)

        grid.addWidget(self.text_field, 0, 0, 5, 1)
        grid.addWidget(self.buttons, 5, 0, 1, 1)
        grid.addWidget(self.calculator, 0, 1, 5, 1)
        grid.addWidget(self.parameters, 0, 2, 5, 1)
        grid.addWidget(self.new_parameter, 5, 2, 1, 1)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.show()

    def insert_parameters(self, items: list) -> None:
        """ Take the given list of parameter names, amounts and types, insert
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

    def insert_interpreter(self, interpreter: Interpreter) -> None:
        self.interpreter = interpreter

    @property
    def formula(self) -> str:
        """ Look into the text_field and return the formula.
        """
        return self.text_field.toPlainText().strip()

    @formula.setter
    def formula(self, value) -> None:
        """ Take the formula and set it to the text_field widget.
        """
        if value is None:
            self.text_field.clear()
        else:
            self.text_field.setPlainText(str(value))

    def append_parameter_name(self, index: QtCore.QModelIndex) -> None:
        """ Take the index from the parameters table and append the parameter
        name to the formula.
        """
        param_name = self.parameters.model().index(index.row(), 0).data()
        self.formula += param_name

    @QtCore.pyqtSlot(str)
    def append_calculator(self, value: str) -> None:
        """ Takes signals from the calculator and adds them into the formula.
        """
        self.formula += value

    @QtCore.pyqtSlot()
    def clear_formula(self) -> None:
        self.formula = None

    @QtCore.pyqtSlot()
    def validate_formula(self) -> None:
        """ Qt slot triggered whenever a change is detected in the text_field.
        """
        self.text_field.blockSignals(True)
        if self.interpreter:
            formula = self.text_field.toPlainText().strip()
            # Do not write massive amounts of errors to stderr if the user
            # is busy writing.
            with open(devnull, "w") as errfile:
                self.interpreter.err_writer = errfile
                self.interpreter(formula)
                if len(self.interpreter.error) > 0:
                    self.buttons.button(QtWidgets.QDialogButtonBox.Save).setEnabled(False)
                else:
                    self.buttons.button(QtWidgets.QDialogButtonBox.Save).setEnabled(True)
        self.text_field.blockSignals(False)


class FormulaDelegate(QtWidgets.QStyledItemDelegate):
    """ An extensive delegate to allow users to build and validate formulas
    The delegate spawns a dialog containing:
      - An editable textfield for the formula.
      - A listview containing parameter names that can be used in the formula
      - Ok and Cancel buttons, on Ok, validate the formula before saving
    For hardmode: also allow the user to create a new parameter from WITHIN
    the delegate dialog itself. Requiring us to also include refreshing
    for the parameter list.
    """
    ACCEPTED_TABLES = {"project_parameter", "database_parameter",
                       "activity_parameter", "product", "technosphere",
                       "biosphere"}

    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QWidget(parent)
        dialog = FormulaDialog(editor, QtCore.Qt.Window)
        dialog.setModal(True)
        dialog.accepted.connect(lambda: self.commitData.emit(editor))
        return editor

    def setEditorData(self, editor: QtWidgets.QWidget, index: QtCore.QModelIndex):
        """ Populate the editor with data if editing an existing field.
        """
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

    def setModelData(self, editor: QtWidgets.QWidget, model: QtCore.QAbstractItemModel,
                     index: QtCore.QModelIndex):
        """ Take the editor, read the given value and set it in the model.

        If the new formula is the same as the existing one, do not call setData
        """
        dialog = editor.findChild(FormulaDialog)
        if dialog.result() == QtWidgets.QDialog.Rejected:
            # Cancel was clicked, do not store anything.
            return
        if model.data(index, QtCore.Qt.DisplayRole) == dialog.formula:
            # The text in the dialog is the same as what is already there.
            return
        model.setData(index, dialog.formula, QtCore.Qt.EditRole)
