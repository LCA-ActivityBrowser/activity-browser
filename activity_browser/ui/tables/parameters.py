# -*- coding: utf-8 -*-
from asteval import Interpreter
from PySide2.QtCore import Slot
from PySide2.QtGui import QContextMenuEvent, QDragMoveEvent, QDropEvent
from PySide2.QtWidgets import QAction, QMenu, QMessageBox

from ...settings import project_settings
from ...signals import signals
from ..icons import qicons
from .delegates import *
from .models import (
    BaseParameterModel, ProjectParameterModel, DatabaseParameterModel,
    ActivityParameterModel, ParameterTreeModel,
)
from .views import ABDataFrameView, ABDictTreeView


class BaseParameterTable(ABDataFrameView):
    MODEL = BaseParameterModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(ABDataFrameView.SingleSelection)

        self.model = self.MODEL(self)

        self.delete_action = QAction(qicons.delete, "Delete parameter", None)
        self.delete_action.triggered.connect(
            lambda: self.model.delete_parameter(self.currentIndex())
        )
        self.rename_action = QAction(qicons.edit, "Rename parameter", None)
        self.rename_action.triggered.connect(
            lambda: self.model.handle_parameter_rename(self.currentIndex())
        )
        self.modify_uncertainty_action = QAction(
            qicons.edit, "Modify uncertainty", None
        )
        self.modify_uncertainty_action.triggered.connect(self.modify_uncertainty)
        self.remove_uncertainty_action = QAction(
            qicons.delete, "Remove uncertainty", None
        )
        self.remove_uncertainty_action.triggered.connect(self.remove_uncertainty)
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)

    @Slot(name="resizeView")
    def custom_view_sizing(self) -> None:
        super().custom_view_sizing()
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        self.setColumnHidden(self.model.param_col, True)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """ Have the parameter test to see if it can be deleted safely.
        """
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QMenu(self)
        menu.addAction(self.rename_action)
        menu.addAction(self.modify_uncertainty_action)
        menu.addSeparator()
        menu.addAction(self.delete_action)
        menu.addAction(self.remove_uncertainty_action)
        proxy = self.indexAt(event.pos())
        if proxy.isValid():
            param = self.get_parameter(proxy)
            if param.is_deletable():
                self.delete_action.setEnabled(True)
            else:
                self.delete_action.setEnabled(False)
            menu.exec_(event.globalPos())

    def get_parameter(self, proxy):
        return self.model.get_parameter(proxy)

    def get_key(self, *args) -> tuple:
        return self.model.get_key()

    def delete_parameter(self, proxy) -> None:
        self.model.delete_parameter(proxy)

    @Slot(name="modifyParameterUncertainty")
    def modify_uncertainty(self) -> None:
        proxy = next(p for p in self.selectedIndexes())
        self.model.modify_uncertainty(proxy)

    @Slot(name="unsetParameterUncertainty")
    def remove_uncertainty(self) -> None:
        proxy = next(p for p in self.selectedIndexes())
        self.model.remove_uncertainty(proxy)

    def comment_column(self, show: bool):
        self.setColumnHidden(self.model.comment_col, not show)

        super().custom_view_sizing()
        self.resizeColumnsToContents()
        self.resizeRowsToContents()


class ProjectParameterTable(BaseParameterTable):
    MODEL = ProjectParameterModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.table_name = "project_parameter"

        # Set delegates for specific columns
        self.setItemDelegateForColumn(1, FloatDelegate(self))
        self.setItemDelegateForColumn(2, FormulaDelegate(self))
        self.setItemDelegateForColumn(3, StringDelegate(self))
        self.setItemDelegateForColumn(4, ViewOnlyUncertaintyDelegate(self))

    def uncertainty_columns(self, show: bool):
        for i in range(4, 10):
            self.setColumnHidden(i, not show)

    @staticmethod
    def get_usable_parameters():
        return ProjectParameterModel.get_usable_parameters()

    @staticmethod
    def get_interpreter() -> Interpreter:
        return ProjectParameterModel.get_interpreter()


class DataBaseParameterTable(BaseParameterTable):
    MODEL = DatabaseParameterModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.table_name = "database_parameter"

        # Set delegates for specific columns
        self.setItemDelegateForColumn(1, FloatDelegate(self))
        self.setItemDelegateForColumn(2, FormulaDelegate(self))
        self.setItemDelegateForColumn(3, DatabaseDelegate(self))
        self.setItemDelegateForColumn(4, StringDelegate(self))
        self.setItemDelegateForColumn(5, ViewOnlyUncertaintyDelegate(self))


    def uncertainty_columns(self, show: bool):
        for i in range(5, 11):
            self.setColumnHidden(i, not show)

    def get_key(self) -> tuple:
        return self.model.get_key(self.currentIndex())

    @staticmethod
    def get_usable_parameters():
        return DatabaseParameterModel.get_usable_parameters()

    def get_interpreter(self) -> Interpreter:
        """ Take the interpreter from the ProjectParameterTable and add
        (potentially overwriting) all database symbols for the selected index.
        """
        return self.model.get_interpreter()


class ActivityParameterTable(BaseParameterTable):
    MODEL = ActivityParameterModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.table_name = "activity_parameter"

        # Set delegates for specific columns
        self.setItemDelegateForColumn(1, FloatDelegate(self))
        self.setItemDelegateForColumn(2, FormulaDelegate(self))
        self.setItemDelegateForColumn(6, StringDelegate(self))
        self.setItemDelegateForColumn(7, ListDelegate(self))
        self.setItemDelegateForColumn(9, StringDelegate(self))
        self.setItemDelegateForColumn(10, ViewOnlyUncertaintyDelegate(self))

        # Set dropEnabled
        self.setDragDropMode(ABDataFrameView.DropOnly)
        self.setAcceptDrops(True)

    @Slot(name="resizeView")
    def custom_view_sizing(self) -> None:
        super().custom_view_sizing()
        self.setColumnHidden(self.model.group_col, True)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """ Check that the dragged row is from the databases table
        """
        if hasattr(event.source(), "technosphere"):
            event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        """ If the user drops an activity into the activity parameters table
        read the relevant data from the database and generate a new row.

        Also, create a warning if the activity is from a read-only database
        """
        db_table = event.source()

        if project_settings.settings["read-only-databases"].get(
                db_table.database_name, True):
            QMessageBox.warning(
                self, "Not allowed",
                "Cannot set activity parameters on read-only databases",
                QMessageBox.Ok, QMessageBox.Ok
            )
            return

        keys = [db_table.get_key(i) for i in db_table.selectedIndexes()]
        event.accept()
        signals.add_activity_parameters.emit(keys)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """ Override and activate QTableView.contextMenuEvent()

        All possible menu events should be added and wired up here
        """
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QMenu(self)
        menu.addAction(
            qicons.add, "Open activities", self.open_activity_tab
        )
        menu.addAction(self.rename_action)
        menu.addAction(self.delete_action)
        menu.addAction(self.modify_uncertainty_action)
        proxy = self.indexAt(event.pos())
        if proxy.isValid():
            param = self.get_parameter(proxy)
            if param.is_deletable():
                self.delete_action.setEnabled(True)
            else:
                self.delete_action.setEnabled(False)
            menu.exec_(event.globalPos())

    @Slot()
    def open_activity_tab(self):
        """ Triggers the activity tab to open one or more activities.
        """
        for proxy in self.selectedIndexes():
            key = self.get_key(proxy)
            signals.safe_open_activity_tab.emit(key)

    def uncertainty_columns(self, show: bool):
        for i in range(10, 16):
            self.setColumnHidden(i, not show)

    def get_key(self, proxy=None) -> tuple:
        proxy = proxy or self.currentIndex()
        return self.model.get_key(proxy)

    def get_activity_groups(self, proxy, ignore_groups: list = None):
        return self.model.get_activity_groups(proxy, ignore_groups)

    @staticmethod
    def get_usable_parameters():
        return ActivityParameterModel.get_usable_parameters()

    def get_current_group(self, proxy=None) -> str:
        """ Retrieve the group of the activity currently selected.
        """
        return self.model.get_group(proxy or self.currentIndex())

    def get_interpreter(self) -> Interpreter:
        return self.model.get_interpreter()


class ExchangesTable(ABDictTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = ParameterTreeModel(parent=self)
        self.setModel(self.model)
        self.model.updated.connect(self.custom_view_sizing)
