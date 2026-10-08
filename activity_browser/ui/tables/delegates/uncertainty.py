# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets
from stats_arrays import uncertainty_choices as uc

from activity_browser.i18n import _

from ....signals import signals


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
            description = uc[int(value)].description
        except (IndexError, ValueError):
            description = uc[0].description
        return _(description)

    def createEditor(self, parent, option, index):
        """Simply use the wizard for updating uncertainties. Send a signal."""
        self.parent().modify_uncertainty_action.trigger()

    def setEditorData(self, editor: QtWidgets.QComboBox, index: QtCore.QModelIndex):
        """Simply use the wizard for updating uncertainties."""
        pass

    def setModelData(
        self,
        editor: QtWidgets.QComboBox,
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex,
    ):
        """Store the stable item ID, independent of its translated label."""
        uc_id = editor.currentData()
        if uc_id is None:
            # Compatibility with an older editor that stored only English text.
            uc_id = self.choices.get(editor.currentText(), 0)
        model.setData(index, uc_id, QtCore.Qt.EditRole)
