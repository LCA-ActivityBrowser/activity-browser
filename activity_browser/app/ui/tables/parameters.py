# -*- coding: utf-8 -*-
from ast import literal_eval
from typing import Optional

from asteval import Interpreter
import brightway2 as bw
import numpy as np
import pandas as pd
from bw2data.parameters import (ActivityParameter, DatabaseParameter, Group,
                                ProjectParameter)
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt
from PyQt5.QtGui import QContextMenuEvent, QDragMoveEvent, QDropEvent
from PyQt5.QtWidgets import QAction, QMenu, QMessageBox

from activity_browser.app.settings import project_settings
from activity_browser.app.signals import signals

from ..icons import qicons
from ..widgets import parameter_save_errorbox, simple_warning_box
from .delegates import (DatabaseDelegate, FloatDelegate, FormulaDelegate,
                        ListDelegate, StringDelegate, UncertaintyDelegate,
                        ViewOnlyDelegate)
from .inventory import ActivitiesBiosphereTable
from .models import ParameterTreeModel
from .views import (ABDataFrameEdit, ABDictTreeView, dataframe_sync,
                    tree_model_decorate)


class BaseParameterTable(ABDataFrameEdit):
    COLUMNS = []
    UNCERTAINTY = [
        "uncertainty type", "loc", "scale", "shape", "minimum", "maximum"
    ]
    new_parameter = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.param_column = self.combine_columns().index("parameter")

    def dataChanged(self, topLeft, bottomRight, roles=None) -> None:
        """ Handle updating the parameters whenever the user changes a value.
        """
        if topLeft == bottomRight and topLeft.isValid():
            if self.get_parameter(topLeft) is None:
                # (not) Dealing with a new parameter not yet saved to db.
                return
            error = self.edit_single_parameter(topLeft)
            if error:
                if error == QMessageBox.Discard:
                    # Undo changes in the table.
                    self.sync(self.build_df())
                if error == QMessageBox.Cancel:
                    # Leave incorrect value in the table.
                    return
        else:
            super().dataChanged(topLeft, bottomRight, roles)

    @dataframe_sync
    def sync(self, df):
        self.dataframe = df

    @classmethod
    def build_df(cls) -> pd.DataFrame:
        raise NotImplementedError

    @classmethod
    def parse_parameter(cls, parameter) -> dict:
        """ Take the given Parameter object and extract data for a single
        row in the table dataframe

        If the parameter has uncertainty data, include this as well.
        """
        row = {key: getattr(parameter, key, "") for key in cls.COLUMNS}
        data = getattr(parameter, "data", {})
        row.update(cls.extract_uncertainty_data(data))
        row["parameter"] = parameter
        return row

    @classmethod
    def combine_columns(cls) -> list:
        """ Combine COLUMNS, UNCERTAINTY and add 'parameter'.
        """
        return cls.COLUMNS + cls.UNCERTAINTY + ["parameter"]

    @classmethod
    def extract_uncertainty_data(cls, data: dict) -> dict:
        """ This helper function can be used to extract specific uncertainty
        columns from the parameter data

        See:
        https://docs.brightwaylca.org/intro.html#storing-uncertain-values
        https://stats-arrays.readthedocs.io/en/latest/#mapping-parameter-array-columns-to-uncertainty-distributions
        """
        row = {key: data.get(key) for key in cls.UNCERTAINTY}
        return row

    def save_parameters(self, overwrite: bool = True) -> Optional[int]:
        """ Take the data from the model and call the correct brightway
        parameters helper method to store it.
        """
        raise NotImplementedError

    def get_parameter(self, proxy):
        """ Reach into the model and return the `parameter` object.
        """
        index = self.get_source_index(proxy)
        return self.model.index(index.row(), self.param_column).data()

    def get_key(self) -> tuple:
        """ Use this to build a (partial) key for the current index.
        """
        return "", ""

    def edit_single_parameter(self, proxy) -> Optional[int]:
        """ Take the proxy index and update the underlying brightway Parameter.

        Note that this method expects the parameter to exist, and will
        raise an error if this is not the case.
        """
        param = self.get_parameter(proxy)
        try:
            field = self.model.headerData(proxy.column(), Qt.Horizontal)
            setattr(param, field, proxy.data())
            param.save()
            # Saving the parameter expires the related group, so recalculate.
            bw.parameters.recalculate()
            signals.parameters_changed.emit()
        except Exception as e:
            return parameter_save_errorbox(self, e)

    def delete_parameter(self, proxy) -> None:
        param = self.get_parameter(proxy)
        if param:
            param.delete_instance()
            df = self.build_df()
        else:
            # Remove the parameter before it is stored in the database
            index = self.get_source_index(proxy)
            row_index = self.dataframe.iloc[index.row()].name
            df = self.dataframe.drop(row_index)
            df.reset_index(drop=True, inplace=True)
        self.sync(df)

    def uncertainty_columns(self, show: bool):
        """ Given a boolean, iterates over the uncertainty columns and either
        shows or hides them.
        """
        raise NotImplementedError

    @staticmethod
    def get_usable_parameters() -> list:
        """ Builds a simple list of parameters that can be used in `this`
        table for use in delegates
        """
        raise NotImplementedError

    @staticmethod
    def get_interpreter() -> Interpreter:
        raise NotImplementedError


class ProjectParameterTable(BaseParameterTable):
    """ Table widget for project parameters

    Using parts of https://stackoverflow.com/a/47021620
    and https://doc.qt.io/qt-5/model-view-programming.html

    NOTE: Currently no good way to delete project parameters due to
    requiring recursive dependency cleanup. Either leave the parameters
    in or delete the entire project.
    """
    COLUMNS = ["name", "amount", "formula"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.table_name = "project_parameter"

        # Set delegates for specific columns
        self.setItemDelegateForColumn(0, StringDelegate(self))
        self.setItemDelegateForColumn(1, FloatDelegate(self))
        self.setItemDelegateForColumn(2, FormulaDelegate(self))
        self.setItemDelegateForColumn(3, UncertaintyDelegate(self))
        self.setItemDelegateForColumn(4, FloatDelegate(self))
        self.setItemDelegateForColumn(5, FloatDelegate(self))
        self.setItemDelegateForColumn(6, FloatDelegate(self))
        self.setItemDelegateForColumn(7, FloatDelegate(self))
        self.setItemDelegateForColumn(8, FloatDelegate(self))

        # context menu
        self.setSelectionMode(BaseParameterTable.SingleSelection)
        self.delete_action = QAction(qicons.delete, "Delete parameter", None)
        self.delete_action.triggered.connect(
            lambda: self.delete_parameter(self.currentIndex())
        )

    def contextMenuEvent(self, event: QContextMenuEvent):
        """ Override and activate QTableView.contextMenuEvent()

        All possible menu events should be added and wired up here
        """
        menu = QMenu(self)
        menu.addAction(self.delete_action)
        param = self.get_parameter(self.indexAt(event.pos()))
        if param is None or self.parameter_is_deletable(param):
            self.delete_action.setEnabled(True)
        else:
            self.delete_action.setEnabled(False)
        menu.exec(event.globalPos())

    def _resize(self) -> None:
        super()._resize()
        self.setColumnHidden(self.param_column, True)

    @classmethod
    def build_df(cls):
        """ Build a dataframe using the ProjectParameters set in brightway
        """
        data = [
            cls.parse_parameter(p) for p in ProjectParameter.select()
        ]
        df = pd.DataFrame(data, columns=cls.combine_columns())
        return df

    def add_parameter(self) -> None:
        """ Take the given row and append it to the dataframe.

        NOTE: Any new parameters are only stored in memory until
        `save_project_parameters` is called in the tab
        """
        row = {"name": None, "amount": 0.0, "formula": ""}
        row.update({key: None for key in self.UNCERTAINTY})
        row["parameter"] = None
        self.dataframe = self.dataframe.append(row, ignore_index=True)
        self.sync(self.dataframe)
        self.new_parameter.emit()

    def save_parameters(self, overwrite: bool=True) -> Optional[int]:
        """ Attempts to store all of the parameters in the dataframe
        as new (or updated) brightway project parameters
        """
        if self.rowCount() == 0:
            return

        data = self.dataframe.to_dict(orient='records')
        try:
            bw.parameters.new_project_parameters(data, overwrite)
            signals.parameters_changed.emit()
        except Exception as e:
            return parameter_save_errorbox(self, e)

    def uncertainty_columns(self, show: bool):
        for i in range(3, 9):
            self.setColumnHidden(i, not show)

    @staticmethod
    def parameter_is_deletable(parameter: ProjectParameter) -> bool:
        """ Take a ProjectParameter and determine if it can be deleted.

        Iterate through all of the database and activity parameters,
        return False if any of them use the parameter, otherwise return True.
        """
        possibles = (DatabaseParameter
                     .select(DatabaseParameter.database)
                     .distinct())
        for param in possibles:
            chain = DatabaseParameter.dependency_chain(param.database)
            data = next((x for x in chain if x.get("kind") == "project"), None)
            if data and parameter.name in data.get("names", set()):
                return False

        possibles = (ActivityParameter
                     .select(ActivityParameter.group)
                     .distinct())
        for param in possibles:
            chain = ActivityParameter.dependency_chain(param.group)
            data = next((x for x in chain if x.get("kind") == "project"), None)
            if data and parameter.name in data.get("names", set()):
                return False
        return True

    @staticmethod
    def get_usable_parameters() -> list:
        return [
            [k, v, "project"] for k, v in ProjectParameter.static().items()
        ]

    @staticmethod
    def get_interpreter() -> Interpreter:
        interpreter = Interpreter()
        interpreter.symtable.update(ProjectParameter.static())
        return interpreter


class DataBaseParameterTable(BaseParameterTable):
    """ Table widget for database parameters

    NOTE: Currently no good way to delete database parameters due to
    requiring recursive dependency cleanup. Either leave the parameters
    in or delete the entire project.
    """
    COLUMNS = ["name", "amount", "formula", "database"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.table_name = "database_parameter"

        # Set delegates for specific columns
        self.setItemDelegateForColumn(0, StringDelegate(self))
        self.setItemDelegateForColumn(1, FloatDelegate(self))
        self.setItemDelegateForColumn(2, FormulaDelegate(self))
        self.setItemDelegateForColumn(3, DatabaseDelegate(self))
        self.setItemDelegateForColumn(4, UncertaintyDelegate(self))
        self.setItemDelegateForColumn(5, FloatDelegate(self))
        self.setItemDelegateForColumn(6, FloatDelegate(self))
        self.setItemDelegateForColumn(7, FloatDelegate(self))
        self.setItemDelegateForColumn(8, FloatDelegate(self))
        self.setItemDelegateForColumn(9, FloatDelegate(self))

        # context menu
        self.setSelectionMode(BaseParameterTable.SingleSelection)
        self.delete_action = QAction(qicons.delete, "Delete parameter", None)
        self.delete_action.triggered.connect(
            lambda: self.delete_parameter(self.currentIndex())
        )

    def contextMenuEvent(self, event: QContextMenuEvent):
        """ Override and activate QTableView.contextMenuEvent()

        All possible menu events should be added and wired up here
        """
        menu = QMenu(self)
        menu.addAction(self.delete_action)
        param = self.get_parameter(self.indexAt(event.pos()))
        if param is None or self.parameter_is_deletable(param):
            self.delete_action.setEnabled(True)
        else:
            self.delete_action.setEnabled(False)
        menu.exec(event.globalPos())

    def _resize(self) -> None:
        super()._resize()
        self.setColumnHidden(self.param_column, True)

    @classmethod
    def build_df(cls) -> pd.DataFrame:
        """ Build a dataframe using the DatabaseParameters set in brightway
        """
        data = [
            cls.parse_parameter(p) for p in DatabaseParameter.select()
        ]
        df = pd.DataFrame(data, columns=cls.combine_columns())
        return df

    def add_parameter(self) -> None:
        """ Add a new database parameter to the dataframe

        NOTE: Any new parameters are only stored in memory until
        `save_project_parameters` is called
        """
        row = {"database": None, "name": None, "amount": 0.0, "formula": ""}
        row.update({key: None for key in self.UNCERTAINTY})
        row["parameter"] = None
        self.dataframe = self.dataframe.append(row, ignore_index=True)
        self.sync(self.dataframe)
        self.new_parameter.emit()

    def save_parameters(self, overwrite: bool=True) -> Optional[int]:
        """ Separates the database parameters by db_name and attempts
        to save each chunk of parameters separately.
        """
        if self.rowCount() == 0:
            return

        used_db_names = self.dataframe["database"].unique()
        for db_name in used_db_names:
            data = (self.dataframe
                    .loc[self.dataframe["database"] == db_name]
                    .to_dict(orient="records"))
            try:
                bw.parameters.new_database_parameters(data, db_name, overwrite)
                signals.parameters_changed.emit()
            except Exception as e:
                return parameter_save_errorbox(self, e)

    def uncertainty_columns(self, show: bool):
        for i in range(4, 10):
            self.setColumnHidden(i, not show)

    @staticmethod
    def parameter_is_deletable(parameter: DatabaseParameter) -> bool:
        """ Take a DatabaseParameter and determine if it can be deleted.

        Iterate through all of the activity parameters, return False if any
        of them use the parameter, otherwise return True.
        """
        possibles = (ActivityParameter
                     .select(ActivityParameter.group)
                     .distinct())
        for param in possibles:
            chain = ActivityParameter.dependency_chain(param.group)
            data = next((x for x in chain if x.get("kind") == "database"), None)
            if data and parameter.name in data.get("names", set()):
                return False
        return True

    @staticmethod
    def get_usable_parameters() -> list:
        """ Include the project parameters, and generate database parameters.
        """
        project = ProjectParameterTable.get_usable_parameters()
        return project + [
            [p.name, p.amount, "database ({})".format(p.database)]
            for p in DatabaseParameter.select()
        ]

    def get_current_database(self) -> str:
        """ Return the database name of the parameter currently selected.
        """
        index = self.get_source_index(self.currentIndex())
        return self.model.index(index.row(), self.COLUMNS.index("database")).data()

    def get_interpreter(self) -> Interpreter:
        """ Take the interpreter from the ProjectParameterTable and add
        (potentially overwriting) all database symbols for the selected index.
        """
        interpreter = ProjectParameterTable.get_interpreter()
        db_name = self.get_current_database()
        interpreter.symtable.update(DatabaseParameter.static(db_name))
        return interpreter

    def get_key(self) -> tuple:
        return self.get_current_database(), ""


class ActivityParameterTable(BaseParameterTable):
    """ Table widget for activity parameters
    """
    COLUMNS = [
        "name", "amount", "formula", "activity", "group", "order", "key"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.table_name = "activity_parameter"

        # Set delegates for specific columns
        self.setItemDelegateForColumn(0, StringDelegate(self))
        self.setItemDelegateForColumn(1, FloatDelegate(self))
        self.setItemDelegateForColumn(2, FormulaDelegate(self))
        self.setItemDelegateForColumn(3, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(4, StringDelegate(self))
        self.setItemDelegateForColumn(5, ListDelegate(self))
        self.setItemDelegateForColumn(6, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(7, UncertaintyDelegate(self))
        self.setItemDelegateForColumn(8, FloatDelegate(self))
        self.setItemDelegateForColumn(9, FloatDelegate(self))
        self.setItemDelegateForColumn(10, FloatDelegate(self))
        self.setItemDelegateForColumn(11, FloatDelegate(self))
        self.setItemDelegateForColumn(12, FloatDelegate(self))

        # Set dropEnabled
        self.setDragDropMode(ABDataFrameEdit.DropOnly)
        self.setAcceptDrops(True)
        self._connect_signals()

    def _connect_signals(self):
        signals.add_activity_parameter.connect(self.add_simple_parameter)

    def _resize(self) -> None:
        super()._resize()
        self.setColumnHidden(self.param_column, True)

    @classmethod
    def build_df(cls):
        """ Build a dataframe using the ActivityParameters set in brightway
        """
        data = [
            cls.parse_parameter(p)
            for p in (ActivityParameter
                      .select(ActivityParameter, Group.order)
                      .join(Group, on=(ActivityParameter.group == Group.name)).dicts())
        ]
        df = pd.DataFrame(data, columns=cls.combine_columns())
        # Convert the 'order' column from list into string
        df["order"] = df["order"].apply(", ".join)
        return df

    @classmethod
    def parse_parameter(cls, parameter) -> dict:
        """ Override the base method to instead use dictionaries.
        """
        row = {key: parameter.get(key, "") for key in cls.COLUMNS}
        # Combine the 'database' and 'code' fields of the parameter into a 'key'
        row["key"] = (parameter.get("database"), parameter.get("code"))
        act = bw.get_activity(row["key"])
        row["activity"] = act.get("name")
        data = parameter.get("data", {})
        row.update(cls.extract_uncertainty_data(data))
        # Cheating because we have the ID of the ActivityParameter
        row["parameter"] = ActivityParameter.get_by_id(parameter["id"])
        return row

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """ Check that the dragged row is from the databases table
        """
        if isinstance(event.source(), ActivitiesBiosphereTable):
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

        for key in keys:
            act = bw.get_activity(key)
            if act.get("type", "process") != "process":
                simple_warning_box(
                    self, "Not allowed",
                    "Activity must be 'process' type, '{}' is type '{}'.".format(
                        act.get("name"), act.get("type")
                    )
                )
                continue
            row = self._build_parameter(key)
            self.dataframe = self.dataframe.append(row, ignore_index=True)

        self.sync(self.dataframe)
        self.new_parameter.emit()

    @pyqtSlot(tuple)
    def add_simple_parameter(self, key: tuple) -> None:
        """ Given the activity key, generate a new row with data from
        the activity and immediately call `new_activity_parameters`.

        NOTE: This is a shortcut to sidestep the functioning of the model
        """
        if key in self.dataframe["key"]:
            return
        row = self._build_parameter(key)
        row["database"], row["code"] = key
        del row["key"], row["parameter"]
        # Save the new parameter immediately.
        bw.parameters.new_activity_parameters([row], row["group"])
        signals.parameters_changed.emit()

    @classmethod
    def _build_parameter(cls, key: tuple) -> dict:
        act = bw.get_activity(key)

        prep_name = act.get("reference product", "")
        if prep_name == "":
            prep_name = act.get("name")
        prep_name = cls.clean_parameter_name(prep_name)

        row = {
            "group": "{}_group".format(prep_name),
            "name": prep_name,
            "amount": act.get("amount", 0.0),
            "formula": act.get("formula", ""),
            "order": "",
            "key": key,
            "parameter": None,
        }
        row.update({key: None for key in cls.UNCERTAINTY})
        return row

    @staticmethod
    def clean_parameter_name(param_name: str) -> str:
        """ Takes a given parameter name and remove or replace all characters
        not allowed to be in there.

        These are ' -,.%[]' and all integers
        """
        remove = ",.%[]0123456789"
        replace = " -"
        for char in remove:
            if char in param_name:
                param_name = param_name.replace(char, "")
        for char in replace:
            if char in param_name:
                param_name = param_name.replace(char, "_")

        return param_name

    def contextMenuEvent(self, event: QContextMenuEvent):
        """ Override and activate QTableView.contextMenuEvent()

        All possible menu events should be added and wired up here
        """
        menu = QMenu(self)
        menu.addAction(
            qicons.add, "Open activity/activities", self.open_activity_tab
        )
        menu.addAction(
            qicons.delete, "Remove parameter(s)", self.delete_parameters
        )
        menu.addAction(
            qicons.delete, "Remove order from group(s)", self.unset_group_order
        )
        menu.exec(event.globalPos())

    @pyqtSlot()
    def open_activity_tab(self):
        """ Triggers the activity tab to open one or more activities.
        """
        for index in self.selectedIndexes():
            source_index = self.get_source_index(index)
            row = self.dataframe.iloc[source_index.row(), ]
            signals.open_activity_tab.emit(row["key"])

    def save_parameters(self, overwrite: bool = True) -> Optional[int]:
        """ Separates the activity parameters by group name and saves each
        chunk of parameters separately.
        """
        if self.rowCount() == 0:
            return

        # Unpack 'key' into 'database' and 'code' for the ParameterManager
        df = self.dataframe.copy()
        df["database"], df["code"] = zip(*df["key"].apply(lambda x: (x[0], x[1])))
        df.drop(["key", "parameter"], axis=1, inplace=True)

        groups = df["group"].str.strip().unique()
        if "" in groups:
            return parameter_save_errorbox(
                self, "Cannot use an empty string as group name."
            )

        for group in groups:
            data = df.loc[df["group"] == group].to_dict(orient="records")
            try:
                bw.parameters.new_activity_parameters(data, group, overwrite)
                self._store_group_order(group)
            except Exception as e:
                return parameter_save_errorbox(self, e)

        signals.parameters_changed.emit()

    def uncertainty_columns(self, show: bool):
        for i in range(7, 13):
            self.setColumnHidden(i, not show)

    def _store_group_order(self, group_name: str) -> None:
        """Checks if anywhere in the 'group'-sliced dataframe the user has
        set the order field. Update the Group object if so.

        Also, if the user has set two different orders in the same group,
        raise a ValueError
        """
        df = self.dataframe.loc[self.dataframe["group"] == group_name]
        orders = df["order"].replace("", np.nan).dropna().unique()
        if orders.size == 1:
            # If any order is given, update the Group object
            order = [i.lstrip() for i in orders[0].split(",")]
            if group_name in order:
                order.remove(group_name)
            group = Group.get(name=group_name)
            group.order = order
            group.save()
        elif orders.size > 1:
            raise ValueError(
                "Multiple different orders given for group {}".format(group_name)
            )

    @pyqtSlot()
    def delete_parameters(self) -> None:
        """ Handle event to delete the given activities and related exchanges.
        """
        deletable = set()
        for proxy in self.selectedIndexes():
            index = self.get_source_index(proxy)
            row = self.dataframe.iloc[index.row(), ]
            act = bw.get_activity(row["key"])
            bw.parameters.remove_from_group(row["group"], act)
            # Also remove the group if there are no more ActivityParameters
            if ActivityParameter.get_or_none(group=row["group"]) is None:
                deletable.add(row["group"])

        # Remove empty groups
        query = Group.delete().where(Group.name.in_(deletable))
        query.execute()

        # Recalculate everything and emit `parameters_changed` signal
        bw.parameters.recalculate()
        signals.parameters_changed.emit()

    @pyqtSlot()
    def unset_group_order(self) -> None:
        """ Removes the set Group.order from all given rows
        """
        groups = set()
        altered = False
        for proxy in self.selectedIndexes():
            index = self.get_source_index(proxy)
            group = self.model.index(index.row(), self.COLUMNS.index("group")).data()
            groups.add(group)

        for group in groups:
            if group == "":
                continue
            try:
                obj = Group.get(name=group)
                obj.order = []
                obj.fresh = False
                obj.save()
                altered = True
            except Group.DoesNotExist:
                continue

        if altered:
            bw.parameters.recalculate()
            signals.parameters_changed.emit()

    @staticmethod
    def get_activity_groups(ignore_groups: list = None) -> list:
        """ Helper method to look into the Group and determine which if any
        other groups the current activity can depend on
        """
        ignore_groups = [] if ignore_groups is None else ignore_groups
        return list(set([
            param.group for param in ActivityParameter.select()
            if param.group not in ignore_groups
        ]))

    @staticmethod
    def get_usable_parameters() -> list:
        """ Include all types of parameters.

        NOTE: This method does not take into account which formula is being
        edited, and therefore does not restrict which database or activity
        parameters are returned.
        """
        project = ProjectParameterTable.get_usable_parameters()
        database = DataBaseParameterTable.get_usable_parameters()
        return project + database + [
            [p.name, p.amount, "activity ({})".format(p.group)]
            for p in ActivityParameter.select()
        ]

    def get_current_group(self) -> str:
        """ Retrieve the group of the activity currently selected.
        """
        index = self.get_source_index(self.currentIndex())
        return self.model.index(index.row(), self.COLUMNS.index("group")).data()

    def get_interpreter(self) -> Interpreter:
        interpreter = Interpreter()
        group = self.get_current_group()
        interpreter.symtable.update(ActivityParameter.static(group, full=True))
        return interpreter

    def get_key(self) -> tuple:
        index = self.get_source_index(self.currentIndex())
        key = self.model.index(index.row(), self.COLUMNS.index("key")).data()
        return literal_eval(key)


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

    @pyqtSlot(tuple)
    def parameterize_exchanges(self, key: tuple) -> None:
        """ Used whenever a formula is set on an exchange in an activity.

        NOTE: this will only work if the activity itself is also parameterized.
        """
        try:
            param = (ActivityParameter.select()
                     .where(ActivityParameter.database == key[0],
                            ActivityParameter.code == key[1])
                     .limit(1)
                     .get())
        except ActivityParameter.DoesNotExist:
            signals.add_activity_parameter.emit(key)
            param = ActivityParameter.get(database=key[0], code=key[1])

        act = bw.get_activity(key)
        bw.parameters.add_exchanges_to_group(param.group, act)
        ActivityParameter.recalculate_exchanges(param.group)
        signals.parameters_changed.emit()

    @staticmethod
    @pyqtSlot()
    def recalculate_exchanges():
        """ Will iterate through all activity parameters and rerun the
        formula interpretation for all exchanges.
        """
        for param in ActivityParameter.select().iterator():
            act = bw.get_activity((param.database, param.code))
            bw.parameters.add_exchanges_to_group(param.group, act)
            ActivityParameter.recalculate_exchanges(param.group)
        signals.parameters_changed.emit()
