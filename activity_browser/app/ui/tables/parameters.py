# -*- coding: utf-8 -*-
from typing import Optional

import pandas as pd
from brightway2 import get_activity, parameters
from bw2data.parameters import (ActivityParameter, DatabaseParameter,
                                ProjectParameter)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import (QContextMenuEvent, QCursor, QDragMoveEvent,
                         QDropEvent, QIcon)
from PyQt5.QtWidgets import QAction, QMenu, QMessageBox

from activity_browser.app.settings import project_settings

from ..icons import icons
from ..widgets import parameter_save_errorbox, simple_warning_box
from .delegates import (DatabaseDelegate, FloatDelegate, StringDelegate,
                        ViewOnlyDelegate)
from .inventory import ActivitiesBiosphereTable
from .views import ABDataFrameEdit


class BaseParameterTable(ABDataFrameEdit):
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

    def __init__(self, parent=None, *args):
        super().__init__(parent, *args)

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

    def save_parameters(self, overwrite: bool=True) -> Optional[QMessageBox]:
        """ Attempts to store all of the parameters in the dataframe
        as new (or updated) brightway project parameters
        """
        if not self.has_data:
            return

        data = self.dataframe.to_dict(orient='records')
        try:
            parameters.new_project_parameters(data, overwrite)
        except Exception as e:
            return parameter_save_errorbox(e)


class DataBaseParameterTable(BaseParameterTable):
    """ Table widget for database parameters

    NOTE: Currently no good way to delete database parameters due to
    requiring recursive dependency cleanup. Either leave the parameters
    in or delete the entire project.
    """
    COLUMNS = ["database", "name", "amount", "formula"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

    def save_parameters(self, overwrite: bool=True) -> Optional[QMessageBox]:
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
                parameters.new_database_parameters(data, db_name, overwrite)
            except Exception as e:
                return parameter_save_errorbox(e)


class ActivityParameterTable(BaseParameterTable):
    """ Table widget for activity parameters
    """
    COLUMNS = ["group", "database", "code", "name", "amount", "formula"]
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
            {key: getattr(p, key, "") for key in cls.COLUMNS}
                for p in ActivityParameter.select()
        ]
        df = pd.DataFrame(data, columns=cls.COLUMNS)
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
            box = simple_warning_box(
                "Not allowed",
                "Cannot set activity parameters on read-only databases"
            )
            box.exec()
            return

        keys = [db_table.get_key(i) for i in db_table.selectedIndexes()]
        event.accept()

        for key in keys:
            act = get_activity(key)
            if act.get("type", "process") != "process":
                box = simple_warning_box(
                    "Not allowed",
                    "Activity must be 'process' type, '{}' is type '{}'.".format(
                        act.get("name"), act.get("type")
                    )
                )
                box.exec()
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
            QIcon(icons.add), "Load all exchanges", None
        )
        load_exchanges_action.triggered.connect(
            lambda: self.add_activity_exchanges(event)
        )
        delete_row_action = QAction(
            QIcon(icons.delete), "Remove parameter(s)", None
        )
        delete_row_action.triggered.connect(
            lambda: self.delete_activity_parameters(event)
        )
        menu.addAction(load_exchanges_action)
        menu.addAction(delete_row_action)
        menu.popup(QCursor.pos())
        menu.exec()

    def add_activity_exchanges(self, event: QContextMenuEvent):
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
                box = simple_warning_box(
                    "Not allowed",
                    "'{}' is a read-only database".format(row.database)
                )
                box.exec()
                continue

            self.expand_activity.emit((row.database, row.code))

    def save_parameters(self, overwrite: bool=True) -> Optional[QMessageBox]:
        """ Separates the activity parameters by group name and saves each
        chunk of parameters separately.
        """
        if not self.has_data:
            return

        groups = self.dataframe["group"].str.strip().unique()
        if "" in groups:
            return parameter_save_errorbox("Cannot use an empty string as group name.")

        for group in groups:
            data = (self.dataframe
                    .loc[self.dataframe["group"] == group]
                    .to_dict(orient="records"))
            try:
                parameters.new_activity_parameters(data, group, overwrite)
            except Exception as e:
                return parameter_save_errorbox(e)

    def delete_activity_parameters(self, event: QContextMenuEvent):
        """ Handle event to delete the given activities and related exchanges.
        """
        for index in self.selectedIndexes():
            source_index = self.get_source_index(index)
            row = self.dataframe.iloc[source_index.row(), ]
            parameters.remove_from_group(
                row["group"], get_activity((row["database"], row["code"]))
            )
        # Recalculate remaining groups
        parameters.recalculate()

        # Reload activities table and trigger reload of exchanges table
        self.sync(self.build_parameter_df())
        self.reload_exchanges.emit()


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
        self.setItemDelegateForColumn(4, FloatDelegate(self))
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

    def extend_exchange_df(self, key: tuple) -> Optional[QMessageBox]:
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
                "Data missing",
                "Cannot retrieve exchanges of unsaved activity parameters"
            )

    @staticmethod
    def _collect_activity_exchanges(key: tuple, only_formula: bool=True) -> list:
        """ Given an activity key, retrieve row data for the exchange table
        """
        act = get_activity(key)
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

    def save_parameters(self, overwrite: bool=True) -> Optional[QMessageBox]:
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
            try:
                # Names are unique within a group.
                param = (ActivityParameter
                         .select(ActivityParameter.database, ActivityParameter.code)
                         .where(ActivityParameter.name == act_param.name,
                                ActivityParameter.group == act_param.group)
                         .limit(1)
                         .get())
                act = get_activity((param.database, param.code))
            except ActivityParameter.DoesNotExist as e:
                # If this happens, the activity and exchange tables are
                # de-synced, somehow.
                continue
            if not act:
                # If this occurs, I have no idea how to handle it safely
                # (the original activity was deleted from the database)
                continue

            # We don't know if the edited exchanges are those with or without
            # formulas, so grab everything
            exchanges = (self.dataframe
                         .loc[(self.dataframe["group"] == act_param.group) & (self.dataframe["name"] == act_param.name)]
                         .to_dict(orient="records"))
            self._update_exchanges(exchanges, act)
            parameters.add_exchanges_to_group(act_param.group, act)

        # Now that all exchanges are updated, recalculate them for each group.
        groups = self.dataframe["group"].unique()
        for group in groups:
            ActivityParameter.recalculate_exchanges(group)

    @staticmethod
    def _update_exchanges(edited: list, act) -> None:
        """ Take the given 'edited' exchanges, and the related activity proxy.

        Find and update each exchange within the activity, either storing the
        original amount in 'original_amount' and setting the given 'formula'
        OR
        remove the 'formula' field from the exchange and restore the 'amount'
        by replacing it with the 'original_amount' value (dropping that after)
        """
        for edited_exc in edited:
            original_exc = next(exc for exc in act.exchanges() if
                                edited_exc.get("input") == exc.input and
                                edited_exc.get("output") == exc.output)
            altered = False
            # If formula was set before
            if 'formula' in original_exc:
                # If the formula was changed in some way
                if edited_exc.get("formula") != original_exc.get("formula"):
                    original_exc["formula"] = edited_exc.get("formula")
                    altered = True
            # If formula was not set
            else:
                # A new formula is set on the exchange
                if not edited_exc.get("formula", "") == "":
                    original_exc["formula"] = edited_exc.get("formula")
                    altered = True

            # Only save to database if changes have occurred
            if altered:
                original_exc.save()
