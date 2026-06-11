# -*- coding: utf-8 -*-
"""Uncertainty column: same flow as ``FloatDelegate`` — dialog widget, then ``model.setData``."""
from qtpy import QtCore, QtWidgets
from stats_arrays import uncertainty_choices as uc

from activity_browser.bwutils.uncertainty import uncertainty_cell_summary
from activity_browser.ui.dialogs import UncertaintyDialog


class UncertaintyDelegate(QtWidgets.QStyledItemDelegate):
    """Delegate for uncertainty-type cells."""

    def displayText(self, value, locale):
        if isinstance(value, dict):
            return uncertainty_cell_summary(value)
        if isinstance(value, (int, float)) and int(value) in uc.id_dict:
            return uncertainty_cell_summary({"uncertainty type": int(value)})
        return "" if value is None else str(value)

    def createEditor(self, parent, option, index):
        from activity_browser import app

        # get existing (initial) values for the uncertainty dict
        model = index.model()
        getter = getattr(model, "uncertainty_editor_initial", None)
        if callable(getter):
            initial = getter(index)
        else:
            raw = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
            initial = raw if isinstance(raw, dict) else {}
        if not isinstance(initial, dict):
            initial = {}
        read_only = False
        ro_getter = getattr(model, "uncertainty_editor_read_only", None)
        if callable(ro_getter):
            read_only = bool(ro_getter(index))
        return UncertaintyDialog(
            parent=app.main_window, initial=initial, read_only=read_only
        )

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
        """Push accepted dialog values through the model like other delegates."""
        if editor is None:
            return
        if getattr(editor, "_read_only", False):
            return
        if not editor.result() == QtWidgets.QDialog.Accepted:
            return

        model.setData(index, editor.result_dict, QtCore.Qt.EditRole)
