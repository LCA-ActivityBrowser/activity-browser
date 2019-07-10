# -*- coding: utf-8 -*-
import pandas as pd
from bw2data.parameters import DatabaseParameter, ProjectParameter
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction

from activity_browser.app.signals import signals

from ..icons import icons
from .delegates import DatabaseDelegate, FloatDelegate, StringDelegate
from .views import ABDataFrameEdit


class ProjectParameterTable(ABDataFrameEdit):
    """ Table widget for project parameters

    Using parts of https://stackoverflow.com/a/47021620
    and https://doc.qt.io/qt-5/model-view-programming.html
    """
    def __init__(self, parent=None, *args):
        super().__init__(parent, *args)

        # Set delegates for specific columns
        self.setItemDelegateForColumn(0, StringDelegate(self))
        self.setItemDelegateForColumn(1, FloatDelegate(self))
        self.setItemDelegateForColumn(2, StringDelegate(self))

        self._setup_context_menu()
        self._connect_signals()

    # def _setup_context_menu(self):
    #     self.delete_row_action = QAction(
    #         QIcon(icons.delete), "Remove parameter", None
    #     )
    #     self.addAction(self.delete_row_action)
    #     self.delete_row_action.triggered.connect(self.delete_rows)

    def _connect_signals(self):
        pass

    @ABDataFrameEdit.decorated_sync
    def sync(self, df):
        self.dataframe = df

    @staticmethod
    def build_parameter_df():
        """ Build a dataframe using the ProjectParameters set in brightway
        """
        data = [
            {"name": p.name, "amount": p.amount, "formula": p.formula} for
                p in ProjectParameter.select()
        ]
        df = pd.DataFrame(data, columns=["name", "amount", "formula"])
        # df.set_index('name', inplace=True)
        return df

    # def delete_rows(self, *args):
    #     super().delete_rows(*args)
    #     signals.parameters_changed.emit()


class DataBaseParameterTable(ABDataFrameEdit):
    """ Table widget for database parameters
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set delegates for specific columns
        self.setItemDelegateForColumn(0, DatabaseDelegate(self))
        self.setItemDelegateForColumn(1, StringDelegate(self))
        self.setItemDelegateForColumn(2, FloatDelegate(self))
        self.setItemDelegateForColumn(3, StringDelegate(self))

        self._setup_context_menu()
        self._connect_signals()

    # def _setup_context_menu(self):
    #     self.delete_row_action = QAction(
    #         QIcon(icons.delete), "Remove parameter", None
    #     )
    #     self.addAction(self.delete_row_action)
    #     self.delete_row_action.triggered.connect(self.delete_rows)

    def _connect_signals(self):
        pass

    @ABDataFrameEdit.decorated_sync
    def sync(self, df):
        self.dataframe = df

    @staticmethod
    def build_parameter_df():
        """ Build a dataframe using the DatabaseParameters set in brightway
        """
        data = [
            {"database": p.database, "name": p.name, "amount": p.amount,
             "formula": p.formula} for p in DatabaseParameter.select()
        ]
        df = pd.DataFrame(data, columns=["database", "name", "amount", "formula"])
        # df.set_index('name', inplace=True)
        return df

    # def delete_rows(self, *args):
    #     super().delete_rows(*args)
    #     signals.parameters_changed.emit()
