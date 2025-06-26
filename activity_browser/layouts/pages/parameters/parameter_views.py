from asteval import Interpreter
from qtpy.QtCore import Slot
from qtpy.QtGui import QContextMenuEvent, QDragMoveEvent, QDropEvent
from qtpy.QtWidgets import QAction, QMenu

import bw2data as bd
import bw_functional as bf

from activity_browser import actions, signals
from activity_browser.ui import icons, delegates

from .parameter_models import (
    BaseParameterModel,
    ProjectParameterModel,
    DatabaseParameterModel,
    ActivityParameterModel,
    ParameterTreeModel,
    ScenarioModel
)
from .base import ABDataFrameView, ABDictTreeView


class ScenarioTable(ABDataFrameView):
    """Constructs an infinitely (horizontally) expandable table that is
    used to set specific amount for user-defined parameters.

    The two required columns in the dataframe for the table are 'Name',
    and 'Type'. all other columns are seen as scenarios containing N floats,
    where N is the number of rows found in the Name column.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.table_name = "scenario_table"

        self.horizontalHeader().setStretchLastSection(False)
        self.verticalHeader().setVisible(True)

        self.model = ScenarioModel(self)
        self.model.updated.connect(self.update_proxy_model)
        signals.project.changed.connect(self.group_column)

    @Slot(bool, name="showGroupColumn")
    def group_column(self, shown: bool = False) -> None:
        self.setColumnHidden(0, not shown)

    def iterate_scenarios(self) -> list[tuple[str, list]]:
        return self.model.iterate_scenarios()


class BaseParameterTable(ABDataFrameView):
    MODEL = BaseParameterModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(ABDataFrameView.SingleSelection)

        self.model = self.MODEL(self)
        self.doubleClicked.connect(
            lambda: self.model.handle_double_click(self.currentIndex())
        )
        self.delete_action = QAction(icons.qicons.delete, "Delete parameter", None)
        self.delete_action.triggered.connect(
            lambda: self.model.delete_parameter(self.currentIndex())
        )
        self.rename_action = QAction(icons.qicons.edit, "Rename parameter", None)
        self.rename_action.triggered.connect(
            lambda: self.model.handle_parameter_rename(self.currentIndex())
        )
        self.modify_uncertainty_action = QAction(
            icons.qicons.edit, "Modify uncertainty", None
        )
        self.modify_uncertainty_action.triggered.connect(self.modify_uncertainty)
        self.remove_uncertainty_action = QAction(
            icons.qicons.delete, "Remove uncertainty", None
        )
        self.remove_uncertainty_action.triggered.connect(self.remove_uncertainty)
        self.model.updated.connect(self.update_proxy_model)

        # hide raw parameter column
        self.model.updated.connect(
            lambda: self.setColumnHidden(self.model.param_col, True)
        )
        self.model.updated.connect(lambda: self.resizeColumnToContents(0))

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Have the parameter test to see if it can be deleted safely."""
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
        self.resizeColumnsToContents()
        self.resizeRowsToContents()


class ProjectParameterTable(BaseParameterTable):
    MODEL = ProjectParameterModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.table_name = "project_parameter"

        # Set delegates for specific columns
        self.setItemDelegateForColumn(1, delegates.FloatDelegate(self))
        self.setItemDelegateForColumn(2, delegates.FormulaDelegate(self))
        self.setItemDelegateForColumn(3, delegates.StringDelegate(self))
        self.setItemDelegateForColumn(4, delegates.ViewOnlyUncertaintyDelegate(self))

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
        self.setItemDelegateForColumn(1, delegates.FloatDelegate(self))
        self.setItemDelegateForColumn(2, delegates.FormulaDelegate(self))
        self.setItemDelegateForColumn(3, delegates.DatabaseDelegate(self))
        self.setItemDelegateForColumn(4, delegates.StringDelegate(self))
        self.setItemDelegateForColumn(5, delegates.ViewOnlyUncertaintyDelegate(self))

    def uncertainty_columns(self, show: bool):
        for i in range(5, 11):
            self.setColumnHidden(i, not show)

    def get_key(self) -> tuple:
        return self.model.get_key(self.currentIndex())

    @staticmethod
    def get_usable_parameters():
        return DatabaseParameterModel.get_usable_parameters()

    def get_interpreter(self) -> Interpreter:
        """Take the interpreter from the ProjectParameterTable and add
        (potentially overwriting) all database symbols for the selected index.
        """
        return self.model.get_interpreter()


class ActivityParameterTable(BaseParameterTable):
    MODEL = ActivityParameterModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.table_name = "activity_parameter"

        # Set delegates for specific columns
        self.setItemDelegateForColumn(1, delegates.FloatDelegate(self))
        self.setItemDelegateForColumn(2, delegates.FormulaDelegate(self))
        self.setItemDelegateForColumn(6, delegates.StringDelegate(self))
        self.setItemDelegateForColumn(7, delegates.ListDelegate(self))
        self.setItemDelegateForColumn(9, delegates.StringDelegate(self))
        self.setItemDelegateForColumn(10, delegates.ViewOnlyUncertaintyDelegate(self))

        # Set dropEnabled
        self.setDragDropMode(ABDataFrameView.DragDropMode.DropOnly)
        self.setAcceptDrops(True)

    def dragMoveEvent(self, event, /):
        pass

    def dragEnterEvent(self, event: QDragMoveEvent) -> None:
        """Check that the dragged row is from the databases table"""
        if event.mimeData().hasFormat("application/bw-nodekeylist"):
            event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        """If the user drops an activity into the activity parameters table
        read the relevant data from the database and generate a new row.

        Also, create a warning if the activity is from a read-only database
        """
        keys: list = event.mimeData().retrievePickleData("application/bw-nodekeylist")
        processes = set()

        for key in keys:
            act = bd.get_node(key=key)
            if isinstance(act, bf.Product):
                continue
            processes.add(key)
        event.accept()
        actions.ParameterNewAutomatic.run(processes)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Override and activate QTableView.contextMenuEvent()

        All possible menu events should be added and wired up here
        """
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QMenu(self)
        menu.addAction(icons.qicons.add, "Open activities", self.open_activity_tab)
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
        """Triggers the activity tab to open one or more activities."""
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
        """Retrieve the group of the activity currently selected."""
        return self.model.get_group(proxy or self.currentIndex())

    def get_interpreter(self) -> Interpreter:
        return self.model.get_interpreter()


class ExchangesTable(ABDictTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = ParameterTreeModel(parent=self)
        self.setModel(self.model)
