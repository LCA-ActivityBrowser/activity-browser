# -*- coding: utf-8 -*-
from qtpy import QtCore, QtWidgets
from stats_arrays import uncertainty_choices as uc

from activity_browser.ui.dialogs import UncertaintyDialog


class UncertaintyDelegate(QtWidgets.QStyledItemDelegate):
    """A combobox containing the sorted list of possible uncertainties
    `setModelData` stores the integer id of the selected uncertainty
    distribution.
    """
    def displayText(self, value, locale):
        """Take the given integer id and return the description.

        Will return the 'Unknown' uncertainty description if the given id
        either cannot be found or the value is 'nan' (when id is not set)
        """
        if isinstance(value, (int, float)) and int(value) in uc.id_dict:
            return uc.id_dict[int(value)].description
        elif isinstance(value, dict) and value.get("uncertainty type") in uc.id_dict:
            return uc[value["uncertainty type"]].description
        return uc[0].description

    def createEditor(self, parent, option, index):
        """Simply use the wizard for updating uncertainties. Send a signal."""
        from activity_browser import app

        item = index.internalPointer()
        item_name = item.__class__.__name__

        if item_name == "ParametersItem" or item_name == "ProjectParametersItem":
            app.actions.ParameterUncertaintyModify.run(item["_parameter"].to_peewee_model())
        elif item_name == "ExchangesItem":
            app.actions.ExchangeUncertaintyModify.run([item.exchange])
        elif item_name == "CharacterizationFactorsItem":
            app.actions.CFUncertaintyModify.run(
                item["_impact_category_name"], [(item["_id"], item["_cf"]),]
            )
        else:
            return UncertaintyDialog(parent=app.main_window, initial=index.data())

    def setEditorData(self, editor, index: QtCore.QModelIndex):
        pass

    def updateEditorGeometry(self, editor, option, index):
        pass

    def setModelData(
        self,
        editor: UncertaintyDialog,
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex,
    ):
        """Read the current text and look up the actual ID of that uncertainty type."""
        if not editor.result() == QtWidgets.QDialog.Accepted:
            return
        
        model.setData(index, editor.result_dict, QtCore.Qt.EditRole)
