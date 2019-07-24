# -*- coding: utf-8 -*-
from typing import List, Optional

import brightway2 as bw
import numpy as np
import pandas as pd
from bw2data.backends.peewee.proxies import Exchange
from bw2data.parameters import (ActivityParameter, DatabaseParameter, Group,
                                ProjectParameter)
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtGui import QContextMenuEvent, QCursor, QDragMoveEvent, QDropEvent
from PyQt5.QtWidgets import QAction, QMenu

from activity_browser.app.settings import project_settings
from activity_browser.app.signals import signals

from ..icons import qicons
from ..widgets import parameter_save_errorbox, simple_warning_box
from .delegates import (DatabaseDelegate, FloatDelegate, ListDelegate,
                        StringDelegate, ViewOnlyDelegate)
from .inventory import ActivitiesBiosphereTable
from .views import ABDataFrameEdit


class BaseParameterTable(ABDataFrameEdit):
    new_parameter = pyqtSignal()

    @ABDataFrameEdit.decorated_sync
    def sync(self, df):
        self.dataframe = df


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

        # Set delegates for specific columns
        self.setItemDelegateForColumn(0, StringDelegate(self))
        self.setItemDelegateForColumn(1, FloatDelegate(self))
        self.setItemDelegateForColumn(2, StringDelegate(self))

    @classmethod
    def build_parameter_df(cls):
        """ Build a dataframe using the ProjectParameters set in brightway
        """
        data = [
            {key: getattr(p, key, "") for key in cls.COLUMNS}
                for p in ProjectParameter.select()
        ]
        df = pd.DataFrame(data, columns=cls.COLUMNS)
        return df

    def add_parameter(self) -> None:
        """ Take the given row and append it to the dataframe.

        NOTE: Any new parameters are only stored in memory until
        `save_project_parameters` is called in the tab
        """
        self.dataframe = self.dataframe.append(
            {"name": None, "amount": 0.0, "formula": ""},
            ignore_index=True
        )
        self.sync(self.dataframe)
        self.new_parameter.emit()

    def save_parameters(self, overwrite: bool=True) -> Optional[int]:
        """ Attempts to store all of the parameters in the dataframe
        as new (or updated) brightway project parameters
        """
        if not self.has_data:
            return

        data = self.dataframe.to_dict(orient='records')
        try:
            bw.parameters.new_project_parameters(data, overwrite)
            signals.parameters_changed.emit()
        except Exception as e:
            return parameter_save_errorbox(self, e)


class DataBaseParameterTable(BaseParameterTable):
    """ Table widget for database parameters

    NOTE: Currently no good way to delete database parameters due to
    requiring recursive dependency cleanup. Either leave the parameters
    in or delete the entire project.
    """
    COLUMNS = ["database", "name", "amount", "formula"]

    def __init__(self, parent=None):
        super().__init__(parent)

        # Set delegates for specific columns
        self.setItemDelegateForColumn(0, DatabaseDelegate(self))
        self.setItemDelegateForColumn(1, StringDelegate(self))
        self.setItemDelegateForColumn(2, FloatDelegate(self))
        self.setItemDelegateForColumn(3, StringDelegate(self))

    @classmethod
    def build_parameter_df(cls) -> pd.DataFrame:
        """ Build a dataframe using the DatabaseParameters set in brightway
        """
        data = [
            {key: getattr(p, key, "") for key in cls.COLUMNS}
                for p in DatabaseParameter.select()
        ]
        df = pd.DataFrame(data, columns=cls.COLUMNS)
        return df

    def add_parameter(self) -> None:
        """ Add a new database parameter to the dataframe

        NOTE: Any new parameters are only stored in memory until
        `save_project_parameters` is called
        """
        self.dataframe = self.dataframe.append(
            {"database": None, "name": None, "amount": 0.0, "formula": ""},
            ignore_index=True
        )
        self.sync(self.dataframe)
        self.new_parameter.emit()

    def save_parameters(self, overwrite: bool=True) -> Optional[int]:
        """ Separates the database parameters by db_name and attempts
        to save each chunk of parameters separately.
        """
        if not self.has_data:
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


class ActivityParameterTable(BaseParameterTable):
    """ Table widget for activity parameters
    """
    COLUMNS = [
        "group", "database", "code", "name", "amount", "formula", "order"
    ]
    expand_activity = pyqtSignal(tuple)
    reload_exchanges = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Set delegates for specific columns
        self.setItemDelegateForColumn(0, StringDelegate(self))
        self.setItemDelegateForColumn(1, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(2, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(3, StringDelegate(self))
        self.setItemDelegateForColumn(4, FloatDelegate(self))
        self.setItemDelegateForColumn(5, StringDelegate(self))
        self.setItemDelegateForColumn(6, ListDelegate(self))

        # Set dropEnabled
        self.viewport().setAcceptDrops(True)

        self._connect_signals()

    def _connect_signals(self):
        if self.parent() and hasattr(self.parent(), 'add_exchanges_action'):
            self.expand_activity.connect(self.parent().add_exchanges_action)
        if self.parent() and hasattr(self.parent(), 'reload_exchanges'):
            self.reload_exchanges.connect(self.parent().reload_exchanges)

    @classmethod
    def build_parameter_df(cls):
        """ Build a dataframe using the ActivityParameters set in brightway
        """
        data = [
            {key: p.get(key, "") for key in cls.COLUMNS}
            for p in (ActivityParameter
                      .select(ActivityParameter, Group.order)
                      .join(Group, on=(ActivityParameter.group == Group.name)).dicts())
        ]
        df = pd.DataFrame(data, columns=cls.COLUMNS)
        # Convert the 'order' column from list into string
        df["order"] = df["order"].apply(", ".join)
        return df

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
            row = {key: act.get(key, "") for key in self.COLUMNS}
            if row["amount"] == "":
                row["amount"] = 0.0
            self.dataframe = self.dataframe.append(
                row, ignore_index=True
            )

        self.sync(self.dataframe)

    def contextMenuEvent(self, event: QContextMenuEvent):
        """ Override and activate QTableView.contextMenuEvent()

        All possible menu events should be added and wired up here
        """
        menu = QMenu(self)
        load_exchanges_action = QAction(
            qicons.add, "Load all exchanges", None
        )
        load_exchanges_action.triggered.connect(self.add_activity_exchanges)
        delete_row_action = QAction(
            qicons.delete, "Remove parameter(s)", None
        )
        delete_row_action.triggered.connect(self.delete_parameters)
        unset_order_action = QAction(
            qicons.delete, "Remove order from group(s)", None
        )
        unset_order_action.triggered.connect(self.unset_group_order)
        menu.addAction(load_exchanges_action)
        menu.addAction(delete_row_action)
        menu.addAction(unset_order_action)
        menu.popup(QCursor.pos())
        menu.exec()

    @pyqtSlot()
    def add_activity_exchanges(self) -> None:
        """ Receive an event to add exchanges to the exchange table
        for the selected activities

        For each selected activity, emit the key of that activity
        as a signal to the parent of the table.
        """
        for index in self.selectedIndexes():
            source_index = self.get_source_index(index)
            row = self.dataframe.iloc[source_index.row(), ]

            if project_settings.settings["read-only-databases"].get(
                    row.database, True):
                simple_warning_box(
                    self, "Not allowed",
                    "'{}' is a read-only database".format(row.database)
                )
                continue

            self.expand_activity.emit((row.database, row.code))

    def save_parameters(self, overwrite: bool=True) -> Optional[int]:
        """ Separates the activity parameters by group name and saves each
        chunk of parameters separately.
        """
        if not self.has_data:
            return

        groups = self.dataframe["group"].str.strip().unique()
        if "" in groups:
            return parameter_save_errorbox(
                self, "Cannot use an empty string as group name."
            )

        for group in groups:
            data = (self.dataframe
                    .loc[self.dataframe["group"] == group]
                    .to_dict(orient="records"))
            try:
                bw.parameters.new_activity_parameters(data, group, overwrite)
                self._store_group_order(group)
                signals.parameters_changed.emit()
            except Exception as e:
                return parameter_save_errorbox(self, e)

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
            act = bw.get_activity((row["database"], row["code"]))
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
        self.sync(self.build_parameter_df())
        signals.parameters_changed.emit()
        self.reload_exchanges.emit()

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


class ExchangeParameterTable(BaseParameterTable):
    """ Table widget for exchange parameters

    NOTE: These exchanges are not retrieved through the ParamaterizedExchange
    class but by scanning the activity exchanges for 'formula' fields.
    """
    COLUMNS = ["group", "name",  "input", "output", "amount", "formula"]

    def __init__(self, parent=None):
        super().__init__(parent)

        # Set delegates for specific columns
        self.setItemDelegateForColumn(0, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(1, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(2, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(3, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(4, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(5, StringDelegate(self))

    @classmethod
    def build_parameter_df(cls):
        """ Build a dataframe using the ActivityParameters set in brightway

        Lookup the activity in the database itself and generate rows using
        exchanges which have a formula set.
        """
        data = []
        for p in ActivityParameter.select():
            row = {"group": p.group, "name": p.name}
            for exc in cls._collect_activity_exchanges((p.database, p.code)):
                data.append(cls._construct_exchange_row(row, exc))

        df = pd.DataFrame(data, columns=cls.COLUMNS)
        return df

    def contextMenuEvent(self, event: QContextMenuEvent):
        """ Override and activate QTableView.contextMenuEvent()

        All possible menu events should be added and wired up here
        """
        menu = QMenu(self)
        delete_row_action = QAction(
            qicons.delete, "Remove parameter(s)", None
        )
        delete_row_action.triggered.connect(self.delete_parameters)
        menu.addAction(delete_row_action)
        menu.popup(QCursor.pos())
        menu.exec()

    @classmethod
    def build_activity_exchange_df(cls, key: tuple) -> pd.DataFrame:
        """ Given an activity key, build a dataframe of all the activity
        exchanges
        """
        param = (ActivityParameter
                 .select(ActivityParameter.group, ActivityParameter.name)
                 .where(ActivityParameter.database == key[0],
                        ActivityParameter.code == key[1])
                 .limit(1)
                 .get())
        act_data = {"group": param.group, "name": param.name}

        data = [
            cls._construct_exchange_row(act_data, exc)
            for exc in cls._collect_activity_exchanges(key, only_formula=False)
        ]

        df = pd.DataFrame(data, columns=cls.COLUMNS)
        return df

    @staticmethod
    def combine_exchange_tables(old: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
        """ Combine two exchange dataframe tables, replacing rows in `old`
        with `new` if they match on specific columns.
        """
        result = (pd.concat([old, new])
                  .drop_duplicates(
                    ["group", "name", "input", "output"], keep="last"
                  )
                  .sort_values(by=["group", "name"]))
        return result

    def extend_exchange_df(self, key: tuple) -> Optional[int]:
        """ Update the owned dataframe with exchanges from the given activity
        key
        """
        try:
            new_exchanges = self.build_activity_exchange_df(key)
            self.dataframe = self.combine_exchange_tables(
                self.dataframe, new_exchanges
            )
            self.sync(self.dataframe)
        except ActivityParameter.DoesNotExist as e:
            return simple_warning_box(
                self, "Data missing",
                "Cannot retrieve exchanges of unsaved activity parameters"
            )

    @staticmethod
    def _collect_activity_exchanges(key: tuple, only_formula: bool=True) -> list:
        """ Given an activity key, retrieve row data for the exchange table
        """
        act = bw.get_activity(key)
        if only_formula:
            return [exc for exc in act.exchanges() if 'formula' in exc]
        else:
            return act.exchanges()

    @staticmethod
    def _construct_exchange_row(act_data: dict, exc) -> dict:
        exc_in = (exc.input.get("database"), exc.input.get("code"))
        exc_out = (exc.output.get("database"), exc.output.get("code"))
        row = {k: v for k, v in act_data.items()}
        row.update({
            "input": exc_in, "output": exc_out,
            "amount": exc.amount, "formula": exc.get("formula", "")
        })
        return row

    def save_parameters(self, overwrite: bool=True) -> Optional[int]:
        """ Iterates over all of the activities for which there are exchanges
         in the table, if a formula is given store the current amount under
         'original_amount', then set the formula.

         In addition, also consider if the
        """
        if not self.has_data:
            return

        edited_activities = self.dataframe.drop_duplicates(["group", "name"])
        for act_param in edited_activities.itertuples(index=False):
            # Retrieve the activity
            act = self._get_activity_from_group_name(
                act_param.group, act_param.name
            )
            # We don't know if the edited exchanges are those with or without
            # formulas, so grab everything
            exchanges = (self.dataframe
                         .loc[(self.dataframe["group"] == act_param.group) & (self.dataframe["name"] == act_param.name)]
                         .to_dict(orient="records"))
            self._update_exchanges(exchanges, act)
            bw.parameters.add_exchanges_to_group(act_param.group, act)

        # Now that all exchanges are updated, recalculate them for each group.
        groups = self.dataframe["group"].unique()
        for group in groups:
            try:
                ActivityParameter.recalculate_exchanges(group)
            except Exception as e:
                # Exception is shown faaaar too late to do something about it.
                return parameter_save_errorbox(self, e)

        signals.parameters_changed.emit()
        self.sync(self.dataframe)

    def delete_parameters(self) -> None:
        """ Removes formula(s) from the selected exchange(s)
        """
        deletions = set()
        for index in self.selectedIndexes():
            source_index = self.get_source_index(index)
            row = self.dataframe.iloc[source_index.row(), ]
            act = self._get_activity_from_group_name(
                row["group"], row["name"]
            )
            deletions.add((row["group"], act))
            exc = next(
                exc for exc in act.exchanges() if
                row.get("input") == exc.input and
                row.get("output") == exc.output
            )
            exc = self._remove_formula(exc)
            exc.save()

        # Now, for each group/act, purge the ParameterizedExchanges and
        # rebuild them
        for group, act in deletions:
            with bw.parameters.db.atomic():
                bw.parameters.remove_exchanges_from_group(group, act)
            bw.parameters.add_exchanges_to_group(group, act)

        bw.parameters.recalculate()
        signals.parameters_changed.emit()
        self.sync(self.build_parameter_df())

    def _get_activity_from_group_name(self, group: str, name: str):
        """ Given the group and name, find the related ActivityParameter
        and retrieve the actual activity
        """
        try:
            # Names are unique within a group.
            param = (ActivityParameter
                     .select(ActivityParameter.database, ActivityParameter.code)
                     .where(ActivityParameter.name == name,
                            ActivityParameter.group == group)
                     .limit(1)
                     .get())
            return bw.get_activity((param.database, param.code))
        except ActivityParameter.DoesNotExist:
            # If this happens, the activity and exchange tables are
            # de-synced, somehow.
            return simple_warning_box(
                self,
                "Oops",
                "No activity parameter for '{}, {}' could be found.".format(group, name)
            )

    def _update_exchanges(self, exchanges: List[dict], act) -> None:
        """ Take the given 'edited' exchanges, and the related activity proxy.

        Find and update each exchange within the activity if needed, either:
        Store the new 'formula' inside in the original exchange
        OR
        Update the existing formula with a new one.
        OR
        Remove an existing formula, in effect removing the parameter.
        """
        for edited in exchanges:
            original = next(
                exc for exc in act.exchanges() if
                edited.get("input") == exc.input and
                edited.get("output") == exc.output
            )
            altered = False
            formula = edited.get("formula", "").strip()

            # No changes, continue to next exchange
            if formula == "" and "formula" not in original:
                continue

            if "formula" in original:
                # Formula was set, but is now being removed
                if formula == "":
                    original = self._remove_formula(original)
                    altered = True
                # If formula was set and is now being changed
                elif formula != original["formula"]:
                    original["formula"] = formula
                    altered = True
            # Formula was not set and is now being set
            else:
                original["original_amount"] = original.amount
                original["formula"] = formula
                altered = True

            # Only save to database if changes have occurred
            if altered:
                original.save()

    @staticmethod
    def _remove_formula(exchange: Exchange) -> Exchange:
        """ Trigger this if the user removes the formula from an exchange
        which previously did have a formula.
        """
        # If we can, restore the original exchange amount
        if "original_amount" in exchange:
            exchange["amount"] = exchange["original_amount"]
            del exchange["original_amount"]
        del exchange["formula"]
        return exchange
