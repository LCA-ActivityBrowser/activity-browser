# -*- coding: utf-8 -*-
import brightway2 as bw
import pandas as pd
from bw2data.parameters import (ActivityParameter, DatabaseParameter,
                                ProjectParameter)
from PyQt5.QtGui import QContextMenuEvent, QCursor, QIcon
from PyQt5.QtWidgets import QAction, QMenu

from ..icons import icons
from .delegates import (DatabaseDelegate, FloatDelegate, StringDelegate,
                        ViewOnlyDelegate)
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

    def __init__(self, parent=None):
        super().__init__(parent)

        # Set delegates for specific columns
        self.setItemDelegateForColumn(0, StringDelegate(self))
        self.setItemDelegateForColumn(1, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(2, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(3, StringDelegate(self))
        self.setItemDelegateForColumn(4, FloatDelegate(self))
        self.setItemDelegateForColumn(5, StringDelegate(self))

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
            act = bw.get_activity((p.database, p.code))
            row = {"group": p.group, "name": p.name}
            for exc in [exc for exc in act.exchanges() if "formula" in exc]:
                exc_in = (exc.input.get("database"), exc.input.get("code"))
                exc_out = (exc.output.get("database"), exc.output.get("code"))
                row.update({
                    "input": exc_in, "output": exc_out,
                    "amount": exc.amount, "formula": exc.get("formula")
                })
                data.append(row)

        df = pd.DataFrame(data, columns=cls.COLUMNS)
        return df

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
