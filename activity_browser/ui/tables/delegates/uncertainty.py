# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets
from stats_arrays import uncertainty_choices as uc


class UncertaintyDelegate(QtWidgets.QStyledItemDelegate):
    """A combobox containing the sorted list of possible uncertainties
    `setModelData` stores the integer id of the selected uncertainty
    distribution.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        uc.check_id_uniqueness()
        self.choices = {
            u.description: u.id for u in uc.choices
        }

    def displayText(self, value, locale):
        """Take the given integer id and return the description.

        Will return the 'Unknown' uncertainty description if the given id
        either cannot be found or the value is 'nan' (when id is not set)
        """
        try:
            return uc[int(value)].description
        except (IndexError, ValueError):
            return uc[0].description

    def createEditor(self, parent, option, index):
        """Create a list of descriptions of the uncertainties we have.

        Note that the `choices` attribute of uncertainty_choices is already
        sorted by id.
        """
        editor = QtWidgets.QComboBox(parent)
        items = sorted(self.choices, key=self.choices.get)
        editor.insertItems(0, items)
        return editor

    def setEditorData(self, editor: QtWidgets.QComboBox, index: QtCore.QModelIndex):
        """Lookup the description text set in the model using the reverse
        dictionary for the uncertainty choices.

        Note that the model presents the integer value as a string (the
        description of the uncertainty distribution), so we cannot simply
        take the value and set the index in that way.
        """
        value = index.data(QtCore.Qt.DisplayRole)
        try:
            value = int(value) if value is not None else 0
        except ValueError as e:
            print("{}, using 0 instead".format(str(e)))
            value = 0
        editor.setCurrentIndex(uc.choices.index(uc[value]))

    def setModelData(self, editor: QtWidgets.QComboBox, model: QtCore.QAbstractItemModel,
                     index: QtCore.QModelIndex):
        """ Read the current text and look up the actual ID of that uncertainty type.
        """
        uc_id = self.choices.get(editor.currentText(), 0)
        model.setData(index, uc_id, QtCore.Qt.EditRole)
