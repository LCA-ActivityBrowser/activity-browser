# -*- coding: utf-8 -*-
import brightway2 as bw
from PySide2.QtCore import Slot
from PySide2 import QtWidgets

from activity_browser.signals import signals
from ..icons import qicons
from .delegates import FloatDelegate, ViewOnlyDelegate
from .impact_categories import MethodsTable, MethodsTree
from .models import CSMethodsModel, CSActivityModel, ScenarioImportModel
from .views import ABDataFrameEdit, ABDataFrameView


class CSList(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(CSList, self).__init__(parent)
        # Runs even if selection doesn't change
        self.activated['QString'].connect(self.set_cs)
        signals.calculation_setup_selected.connect(self.sync)

    def sync(self, name):
        self.blockSignals(True)
        self.clear()
        keys = sorted(bw.calculation_setups)
        self.insertItems(0, keys)
        self.blockSignals(False)
        self.setCurrentIndex(keys.index(name))

    @staticmethod
    def set_cs(name: str):
        signals.calculation_setup_selected.emit(name)

    @property
    def name(self) -> str:
        return self.currentText()


class CSActivityTable(ABDataFrameEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QTableView.DropOnly)
        self.model = CSActivityModel(self)
        self.setItemDelegateForColumn(0, FloatDelegate(self))
        self.setItemDelegateForColumn(1, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(2, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(3, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(4, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(5, ViewOnlyDelegate(self))

        signals.calculation_setup_selected.connect(self.sync)
        signals.databases_changed.connect(self.sync)
        # after editing the model, signal that the calculation setup has changed.
        self.model.dataChanged.connect(lambda: signals.calculation_setup_changed.emit())

    def _resize(self):
        self.setColumnHidden(6, True)
        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def sync(self, name: str = None):
        self.model.sync(name)
        self._resize()

    @Slot(name="openActivities")
    def open_activities(self) -> None:
        for proxy in self.selectedIndexes():
            act = self.model.get_key(proxy)
            signals.open_activity_tab.emit(act)
            signals.add_activity_to_history.emit(act)

    @Slot(name="deleteRows")
    def delete_rows(self):
        self.model.delete_rows(self.selectedIndexes())
        self._resize()

    def to_python(self) -> list:
        return self.model.activities

    def contextMenuEvent(self, a0) -> None:
        menu = QtWidgets.QMenu()
        menu.addAction(qicons.right, "Open activity", self.open_activities)
        menu.addAction(qicons.delete, "Remove row", self.delete_rows)
        menu.exec_(a0.globalPos())

    def dragEnterEvent(self, event):
        if getattr(event.source(), "technosphere", False):
            event.accept()

    def dragMoveEvent(self, event) -> None:
        pass

    def dropEvent(self, event):
        event.accept()
        source = event.source()
        print('Dropevent from:', source)
        self.model.include_activities(
            {source.get_key(p): 1.0} for p in source.selectedIndexes()
        )
        self._resize()


class CSMethodsTable(ABDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QTableView.DropOnly)
        self.model = CSMethodsModel(self)
        signals.calculation_setup_selected.connect(self.sync)

    def _resize(self):
        self.setColumnHidden(3, True)
        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def sync(self, name: str = None):
        self.model.sync(name)
        self._resize()

    @Slot(name="deleteRows")
    def delete_rows(self):
        self.model.delete_rows(self.selectedIndexes())
        self._resize()

    def to_python(self):
        return self.model.methods

    def contextMenuEvent(self, a0) -> None:
        menu = QtWidgets.QMenu()
        menu.addAction(qicons.delete, "Remove row", self.delete_rows)
        menu.exec_(a0.globalPos())

    def dragEnterEvent(self, event):
        if isinstance(event.source(), (MethodsTable, MethodsTree)):
            event.accept()

    def dragMoveEvent(self, event) -> None:
        pass

    def dropEvent(self, event):
        event.accept()
        self.model.include_methods(event.source().selected_methods())
        self._resize()


class ScenarioImportTable(ABDataFrameView):
    """Self-contained widget that shows the scenario headers for a given
    scenario template dataframe.
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.model = ScenarioImportModel(self)

    def sync(self, names: list):
        self.model.sync(names)
        self._resize()
