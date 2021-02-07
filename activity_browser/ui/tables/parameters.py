# -*- coding: utf-8 -*-
from asteval import Interpreter
import brightway2 as bw
from bw2data.parameters import (ActivityParameter, DatabaseParameter,
                                ProjectParameter)
from PySide2.QtCore import Slot
from PySide2.QtGui import QContextMenuEvent, QDragMoveEvent, QDropEvent
from PySide2.QtWidgets import QAction, QMenu

from ...bwutils import commontasks as bc
from ...settings import project_settings
from ...signals import signals
from ..icons import qicons
from ..widgets import simple_warning_box
from .delegates import *
from .models import (
    BaseParameterModel, ProjectParameterModel, DatabaseParameterModel,
    ActivityParameterModel, ParameterTreeModel,
)
from .views import ABDataFrameEdit, ABDictTreeView, tree_model_decorate


class BaseParameterTable(ABDataFrameEdit):
    MODEL = BaseParameterModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(ABDataFrameEdit.SingleSelection)

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

    def sync(self) -> None:
        self.model.sync()
        self._resize()

    def _resize(self) -> None:
        super()._resize()
        self.setColumnHidden(self.model.param_col, True)

    def contextMenuEvent(self, event: QContextMenuEvent):
        """ Have the parameter test to see if it can be deleted safely.
        """
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

    def rename_parameter(self, proxy, new_name: str, update: bool = True) -> None:
        self.model.rename_parameter(proxy, new_name, update)

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


class ProjectParameterTable(BaseParameterTable):
    MODEL = ProjectParameterModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.table_name = "project_parameter"

        # Set delegates for specific columns
        self.setItemDelegateForColumn(0, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(1, FloatDelegate(self))
        self.setItemDelegateForColumn(2, FormulaDelegate(self))
        self.setItemDelegateForColumn(3, ViewOnlyUncertaintyDelegate(self))
        self.setItemDelegateForColumn(4, ViewOnlyFloatDelegate(self))
        self.setItemDelegateForColumn(5, ViewOnlyFloatDelegate(self))
        self.setItemDelegateForColumn(6, ViewOnlyFloatDelegate(self))
        self.setItemDelegateForColumn(7, ViewOnlyFloatDelegate(self))
        self.setItemDelegateForColumn(8, ViewOnlyFloatDelegate(self))

    def uncertainty_columns(self, show: bool):
        for i in range(3, 9):
            self.setColumnHidden(i, not show)

    def add_parameter(self):
        self.model.add_parameter()

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
        self.setItemDelegateForColumn(0, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(1, FloatDelegate(self))
        self.setItemDelegateForColumn(2, FormulaDelegate(self))
        self.setItemDelegateForColumn(3, DatabaseDelegate(self))
        self.setItemDelegateForColumn(4, ViewOnlyUncertaintyDelegate(self))
        self.setItemDelegateForColumn(5, ViewOnlyFloatDelegate(self))
        self.setItemDelegateForColumn(6, ViewOnlyFloatDelegate(self))
        self.setItemDelegateForColumn(7, ViewOnlyFloatDelegate(self))
        self.setItemDelegateForColumn(8, ViewOnlyFloatDelegate(self))
        self.setItemDelegateForColumn(9, ViewOnlyFloatDelegate(self))

    def uncertainty_columns(self, show: bool):
        for i in range(4, 10):
            self.setColumnHidden(i, not show)

    def get_key(self) -> tuple:
        return self.model.get_key(self.currentIndex())

    def add_parameter(self):
        self.model.add_parameter()

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
        self.setItemDelegateForColumn(0, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(1, FloatDelegate(self))
        self.setItemDelegateForColumn(2, FormulaDelegate(self))
        self.setItemDelegateForColumn(3, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(4, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(5, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(6, StringDelegate(self))
        self.setItemDelegateForColumn(7, ListDelegate(self))
        self.setItemDelegateForColumn(8, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(9, ViewOnlyUncertaintyDelegate(self))
        self.setItemDelegateForColumn(10, ViewOnlyFloatDelegate(self))
        self.setItemDelegateForColumn(11, ViewOnlyFloatDelegate(self))
        self.setItemDelegateForColumn(12, ViewOnlyFloatDelegate(self))
        self.setItemDelegateForColumn(13, ViewOnlyFloatDelegate(self))
        self.setItemDelegateForColumn(14, ViewOnlyFloatDelegate(self))

        # Set dropEnabled
        self.setDragDropMode(ABDataFrameEdit.DropOnly)
        self.setAcceptDrops(True)

    def _resize(self) -> None:
        super()._resize()
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
            simple_warning_box(
                self, "Not allowed",
                "Cannot set activity parameters on read-only databases"
            )
            return

        keys = [db_table.get_key(i) for i in db_table.selectedIndexes()]
        event.accept()
        self.model.add_parameters(keys)

    def add_parameter(self, key: tuple) -> None:
        self.model.add_parameter(key)

    def contextMenuEvent(self, event: QContextMenuEvent):
        """ Override and activate QTableView.contextMenuEvent()

        All possible menu events should be added and wired up here
        """
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
            signals.open_activity_tab.emit(key)

    def uncertainty_columns(self, show: bool):
        for i in range(9, 15):
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
    def _connect_signals(self):
        super()._connect_signals()
        signals.exchange_formula_changed.connect(self.parameterize_exchanges)

    @tree_model_decorate
    def sync(self) -> None:
        self.data.update({
            "project": ProjectParameter.select().iterator(),
            "database": DatabaseParameter.select().iterator(),
            "activity": ActivityParameter.select().iterator(),
        })

    def _select_model(self):
        return ParameterTreeModel(self.data)

    @Slot(tuple, name="parameterizeExchangesForKey")
    def parameterize_exchanges(self, key: tuple) -> None:
        """ Used whenever a formula is set on an exchange in an activity.

        If no `ActivityParameter` exists for the key, generate one immediately
        """
        group = bc.build_activity_group_name(key)
        if not (ActivityParameter.select()
                .where(ActivityParameter.group == group).count()):
            ActivityParameterTable.add_parameter(key)

        act = bw.get_activity(key)
        with bw.parameters.db.atomic():
            bw.parameters.remove_exchanges_from_group(group, act)
            bw.parameters.add_exchanges_to_group(group, act)
            ActivityParameter.recalculate_exchanges(group)
        signals.parameters_changed.emit()
