# -*- coding: utf-8 -*-
from qtpy import QtCore, QtWidgets
from stats_arrays import uncertainty_choices as uc

from activity_browser import actions

from activity_browser.signals import signals


class UncertaintyDelegate(QtWidgets.QStyledItemDelegate):
    """A combobox containing the sorted list of possible uncertainties
    `setModelData` stores the integer id of the selected uncertainty
    distribution.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        uc.check_id_uniqueness()
        self.choices = {u.description: u.id for u in uc.choices}

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
        """Simply use the wizard for updating uncertainties. Send a signal."""
        if hasattr(self.parent(), "modify_uncertainty_action"):
            self.parent().modify_uncertainty_action.trigger()
        elif hasattr(index.internalPointer(), "exchange"):
            item = index.internalPointer()
            actions.ExchangeUncertaintyModify.run([item.exchange])

    def setEditorData(self, editor: QtWidgets.QComboBox, index: QtCore.QModelIndex):
        """Simply use the wizard for updating uncertainties."""
        pass

    def setModelData(
        self,
        editor: QtWidgets.QComboBox,
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex,
    ):
        """Read the current text and look up the actual ID of that uncertainty type."""
        uc_id = self.choices.get(editor.currentText(), 0)
        model.setData(index, uc_id, QtCore.Qt.EditRole)
