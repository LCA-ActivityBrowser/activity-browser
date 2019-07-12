# -*- coding: utf-8 -*-
import brightway2 as bw
import pandas as pd
from bw2data.parameters import (ActivityParameter, DatabaseParameter,
                                ProjectParameter)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import (QContextMenuEvent, QCursor, QDragMoveEvent,
                         QDropEvent, QIcon)
from PyQt5.QtWidgets import QAction, QMenu

from ..icons import icons
from .delegates import (DatabaseDelegate, FloatDelegate, StringDelegate,
                        ViewOnlyDelegate)
from .inventory import ActivitiesBiosphereTable
from .views import ABDataFrameEdit


class ProjectParameterTable(ABDataFrameEdit):
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

    @ABDataFrameEdit.decorated_sync
    def sync(self, df):
        self.dataframe = df

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


class DataBaseParameterTable(ABDataFrameEdit):
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

    @ABDataFrameEdit.decorated_sync
    def sync(self, df):
        self.dataframe = df

    @classmethod
    def build_parameter_df(cls):
        """ Build a dataframe using the DatabaseParameters set in brightway
        """
        data = [
            {key: getattr(p, key, "") for key in cls.COLUMNS}
                for p in DatabaseParameter.select()
        ]
        df = pd.DataFrame(data, columns=cls.COLUMNS)
        return df


class ActivityParameterTable(ABDataFrameEdit):
    """ Table widget for activity parameters
    """
    COLUMNS = ["group", "database", "code", "name", "amount", "formula"]
    expand_activity = pyqtSignal(tuple)

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

    @ABDataFrameEdit.decorated_sync
    def sync(self, df):
        self.dataframe = df

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
        if isinstance(event.source(), ActivitiesBiosphereTable):
            event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        db_table = event.source()
        keys = [db_table.get_key(i) for i in db_table.selectedIndexes()]
        event.accept()

        for key in keys:
            act = bw.get_activity(key)
            if act.get("type", "process") != "process":
                continue
            row = {key: act.get(key, "") for key in self.COLUMNS}
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
            self.expand_activity.emit((row.database, row.code))

    def delete_activity_parameters(self, event: QContextMenuEvent):
        """ Receive an event to delete the given activities or exchanges.
        """
        pass
        # print("You clicked delete!")
        # for index in self.selectedIndexes():
        #     source_index = self.get_source_index(index)
        #     print("Deleting row: {}".format(source_index.row()))


class ExchangeParameterTable(ABDataFrameEdit):
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

    @ABDataFrameEdit.decorated_sync
    def sync(self, df):
        self.dataframe = df

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

    def contextMenuEvent(self, event: QContextMenuEvent):
        """ Override and activate QTableView.contextMenuEvent()

        All possible menu events should be added and wired up here
        """
        menu = QMenu(self)
        delete_row_action = QAction(
            QIcon(icons.delete), "Remove parameter(s)", None
        )
        delete_row_action.triggered.connect(
            lambda: self.delete_activity_parameters(event)
        )
        menu.addAction(delete_row_action)
        menu.popup(QCursor.pos())
        menu.exec()

    def delete_activity_parameters(self, event: QContextMenuEvent):
        """ Receive an event to delete the given activities or exchanges.
        """
        pass
        # print("You clicked delete!")
        # for index in self.selectedIndexes():
        #     source_index = self.get_source_index(index)
        #     print("Deleting row: {}".format(source_index.row()))
