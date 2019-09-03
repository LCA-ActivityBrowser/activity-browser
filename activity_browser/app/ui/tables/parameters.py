# -*- coding: utf-8 -*-
from typing import Optional

import brightway2 as bw
import numpy as np
import pandas as pd
from bw2data.parameters import (ActivityParameter, DatabaseParameter, Group,
                                ProjectParameter)
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtGui import QContextMenuEvent, QDragMoveEvent, QDropEvent
from PyQt5.QtWidgets import QMenu

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
        return row

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

    @classmethod
    def build_df(cls):
        """ Build a dataframe using the ProjectParameters set in brightway
        """
        data = [
            cls.parse_parameter(p) for p in ProjectParameter.select()
        ]
        df = pd.DataFrame(data, columns=cls.COLUMNS + cls.UNCERTAINTY)
        return df

    def add_parameter(self) -> None:
        """ Take the given row and append it to the dataframe.

        NOTE: Any new parameters are only stored in memory until
        `save_project_parameters` is called in the tab
        """
        row = {"name": None, "amount": 0.0, "formula": ""}
        row.update({key: None for key in self.UNCERTAINTY})
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
    def get_usable_parameters() -> list:
        return [
            [p.name, p.amount, "project"] for p in ProjectParameter.select()
        ]


class DataBaseParameterTable(BaseParameterTable):
    """ Table widget for database parameters

    NOTE: Currently no good way to delete database parameters due to
    requiring recursive dependency cleanup. Either leave the parameters
    in or delete the entire project.
    """
    COLUMNS = ["database", "name", "amount", "formula"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.table_name = "database_parameter"

        # Set delegates for specific columns
        self.setItemDelegateForColumn(0, DatabaseDelegate(self))
        self.setItemDelegateForColumn(1, StringDelegate(self))
        self.setItemDelegateForColumn(2, FloatDelegate(self))
        self.setItemDelegateForColumn(3, FormulaDelegate(self))
        self.setItemDelegateForColumn(4, UncertaintyDelegate(self))
        self.setItemDelegateForColumn(5, FloatDelegate(self))
        self.setItemDelegateForColumn(6, FloatDelegate(self))
        self.setItemDelegateForColumn(7, FloatDelegate(self))
        self.setItemDelegateForColumn(8, FloatDelegate(self))
        self.setItemDelegateForColumn(9, FloatDelegate(self))

    @classmethod
    def build_df(cls) -> pd.DataFrame:
        """ Build a dataframe using the DatabaseParameters set in brightway
        """
        data = [
            cls.parse_parameter(p) for p in DatabaseParameter.select()
        ]
        df = pd.DataFrame(data, columns=cls.COLUMNS + cls.UNCERTAINTY)
        return df

    def add_parameter(self) -> None:
        """ Add a new database parameter to the dataframe

        NOTE: Any new parameters are only stored in memory until
        `save_project_parameters` is called
        """
        row = {"database": None, "name": None, "amount": 0.0, "formula": ""}
        row.update({key: None for key in self.UNCERTAINTY})
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
    def get_usable_parameters() -> list:
        """ Include the project parameters, and generate database parameters.
        """
        project = ProjectParameterTable.get_usable_parameters()
        return project + [
            [p.name, p.amount, "database ({})".format(p.database)]
            for p in DatabaseParameter.select()
        ]


class ActivityParameterTable(BaseParameterTable):
    """ Table widget for activity parameters
    """
    COLUMNS = [
        "group", "name", "amount", "formula", "order", "key"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.table_name = "activity_parameter"

        # Set delegates for specific columns
        self.setItemDelegateForColumn(0, StringDelegate(self))
        self.setItemDelegateForColumn(1, StringDelegate(self))
        self.setItemDelegateForColumn(2, FloatDelegate(self))
        self.setItemDelegateForColumn(3, FormulaDelegate(self))
        self.setItemDelegateForColumn(4, ListDelegate(self))
        self.setItemDelegateForColumn(5, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(6, UncertaintyDelegate(self))
        self.setItemDelegateForColumn(7, FloatDelegate(self))
        self.setItemDelegateForColumn(8, FloatDelegate(self))
        self.setItemDelegateForColumn(9, FloatDelegate(self))
        self.setItemDelegateForColumn(10, FloatDelegate(self))
        self.setItemDelegateForColumn(11, FloatDelegate(self))

        # Set dropEnabled
        self.viewport().setAcceptDrops(True)
        self._connect_signals()

    def _connect_signals(self):
        signals.add_activity_parameter.connect(self.add_simple_parameter)

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
        df = pd.DataFrame(data, columns=cls.COLUMNS + cls.UNCERTAINTY)
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
        data = parameter.get("data", {})
        row.update(cls.extract_uncertainty_data(data))
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
        the activity and immediately call `save_parameters`.
        """
        if key in self.dataframe["key"]:
            return
        row = self._build_parameter(key)
        self.dataframe = self.dataframe.append(row, ignore_index=True)
        self.sync(self.dataframe)
        self.new_parameter.emit()

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
        menu.popup(event.globalPos())
        menu.exec()

    @pyqtSlot()
    def open_activity_tab(self):
        """ Triggers the activity tab to open one or more activities.
        """
        for index in self.selectedIndexes():
            source_index = self.get_source_index(index)
            row = self.dataframe.iloc[source_index.row(), ]
            signals.open_activity_tab.emit(row["key"])

    def save_parameters(self, overwrite: bool=True) -> Optional[int]:
        """ Separates the activity parameters by group name and saves each
        chunk of parameters separately.
        """
        if self.rowCount() == 0:
            return

        # Unpack 'key' into 'database' and 'code' for the ParameterManager
        df = self.dataframe.copy()
        df["database"], df["code"] = zip(*df["key"].apply(lambda x: (x[0], x[1])))
        df.drop("key", axis=1, inplace=True)

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
        for i in range(6, 12):
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
        for index in self.selectedIndexes():
            source_index = self.get_source_index(index)
            row = self.dataframe.iloc[source_index.row(), ]
            act = bw.get_activity(row["key"])
            bw.parameters.remove_from_group(row["group"], act)
        self.recalculate()

    @pyqtSlot()
    def unset_group_order(self) -> None:
        """ Removes the set Group.order from all given rows
        """
        groups = set()
        altered = False
        for proxy in self.selectedIndexes():
            index = self.get_source_index(proxy)
            row = self.dataframe.iloc[index.row(), ]
            groups.add(row["group"])

        for group in groups:
            if group == "":
                continue
            try:
                obj = Group.get(name=group)
                obj.order = []
                obj.save()
                altered = True
            except Group.DoesNotExist:
                continue

        if altered:
            self.recalculate()

    def recalculate(self) -> None:
        """ Triggers general parameter recalculation and table sync
        """
        # Recalculate everything
        bw.parameters.recalculate()
        # Reload activities table and trigger reload of exchanges table
        self.sync(self.build_df())
        signals.parameters_changed.emit()

    @staticmethod
    def get_activity_groups(ignore_groups: list=None) -> list:
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
            return

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
