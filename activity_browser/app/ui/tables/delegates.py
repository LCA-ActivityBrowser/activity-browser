# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5.QtCore import QAbstractItemModel, QLocale, QModelIndex, Qt
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import (QApplication, QComboBox, QLineEdit, QStyle,
                             QStyledItemDelegate, QStyleOptionButton)


class FloatDelegate(QStyledItemDelegate):
    """ For managing and validating entered float values.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        locale = QLocale(QLocale.English)
        locale.setNumberOptions(QLocale.RejectGroupSeparator)
        validator = QDoubleValidator()
        validator.setLocale(locale)
        editor.setValidator(validator)
        return editor

    def setEditorData(self, editor: QLineEdit, index: QModelIndex):
        """ Populate the editor with data if editing an existing field.
        """
        data = index.data(Qt.DisplayRole)
        value = float(data) if data else 0
        editor.setText(str(value))

    def setModelData(self, editor: QLineEdit, model: QAbstractItemModel,
                     index: QModelIndex):
        """ Take the editor, read the given value and set it in the model
        """
        try:
            value = float(editor.text())
            model.setData(index, value, Qt.EditRole)
        except ValueError:
            pass


class StringDelegate(QStyledItemDelegate):
    """ For managing and validating entered string values.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        return editor

    def setEditorData(self, editor: QLineEdit, index: QModelIndex):
        """ Populate the editor with data if editing an existing field.
        """
        value = index.data(Qt.DisplayRole)
        # Avoid setting 'None' type value as a string
        value = str(value) if value else ""
        editor.setText(value)

    def setModelData(self, editor: QLineEdit, model: QAbstractItemModel,
                     index: QModelIndex):
        """ Take the editor, read the given value and set it in the model
        """
        value = editor.text()
        model.setData(index, value, Qt.EditRole)


class DatabaseDelegate(QStyledItemDelegate):
    """ Nearly the same as the string delegate, but presents as
    a combobox menu containing the databases of the current project.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.insertItems(0, bw.databases.list)
        return editor

    def setEditorData(self, editor: QComboBox, index: QModelIndex):
        """ Populate the editor with data if editing an existing field.
        """
        value = str(index.data(Qt.DisplayRole))
        editor.setCurrentText(value)

    def setModelData(self, editor: QComboBox, model: QAbstractItemModel,
                     index: QModelIndex):
        """ Take the editor, read the given value and set it in the model.
        """
        value = editor.currentText()
        model.setData(index, value, Qt.EditRole)


class CheckboxDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        return None

    def paint(self, painter, option, index):
        """ Paint the cell with a styled option button, showing a checkbox

        See links below for inspiration:
        https://stackoverflow.com/a/11778012
        https://stackoverflow.com/q/15235273
        """
        painter.save()
        value = bool(index.data(Qt.DisplayRole))
        button = QStyleOptionButton()
        button.state = QStyle.State_Enabled
        button.state |= QStyle.State_Off if not value else QStyle.State_On
        button.rect = option.rect
        # button.text = "False" if not value else "True"  # This also adds text
        QApplication.style().drawPrimitive(QStyle.PE_IndicatorCheckBox, button, painter)
        painter.restore()


class ViewOnlyDelegate(QStyledItemDelegate):
    """ Disable the editor functionality to allow specific columns of an
    editable table to be view-only.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        return None
