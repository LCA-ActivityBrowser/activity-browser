# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets


class ABDataFrameTable(QtWidgets.QTableView):
    def __init__(self, parent=None, *args):
        super(ABDataFrameTable, self).__init__(parent)
        self.setVerticalScrollMode(1)
        self.setHorizontalScrollMode(1)

    @classmethod
    def decorated_sync(cls, sync):
        def wrapper(self, *args, **kwargs):

            sync(self, *args, **kwargs)

            self.model = PandasModel(self.dataframe)
            self.setModel(self.model)
            self.resizeColumnsToContents()
            self.resizeRowsToContents()
            if self.model.rowCount() > 0:
                self.setMaximumHeight(
                    self.rowHeight(0) * (self.model.rowCount() + 1) + self.autoScrollMargin()
                )
            else:
                self.setMaximumHeight(50)
            self.setMinimumHeight(
                self.rowHeight(0) * (min(self.model.rowCount()+1.5, 20)) + self.autoScrollMargin()
            )

        return wrapper

    def to_clipboard(self):
        self.dataframe.to_clipboard()

    def savefilepath(self):
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            'Choose location to save lca results'
        )
        return filepath

    def to_csv(self):
        filepath = self.savefilepath()
        if filepath:
            if not filepath.endswith('.csv'):
                filepath += '.csv'
            self.dataframe.to_csv(filepath)

    def to_excel(self):
        filepath = self.savefilepath()
        if filepath:
            if not filepath.endswith('.xlsx'):
                filepath += '.xlsx'
            self.dataframe.to_excel(filepath)


class PandasModel(QtCore.QAbstractTableModel):
    """
    adapted from https://stackoverflow.com/a/42955764
    """
    def __init__(self, dataframe, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._dataframe = dataframe

    def rowCount(self, parent=None):
        return self._dataframe.shape[0]

    def columnCount(self, parent=None):
        return self._dataframe.shape[1]

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                return "{:.5g}".format(self._dataframe.iloc[index.row(), index.column()])
        return None

    def headerData(self, pos, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self._dataframe.columns[pos]
        elif orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
            return self._dataframe.index[pos]
        return None
