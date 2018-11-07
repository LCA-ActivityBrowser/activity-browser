# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets
import numpy as np

class ABDataFrameTable(QtWidgets.QTableView):
    def __init__(self, parent=None, maxheight=None, *args, **kwargs):
        super(ABDataFrameTable, self).__init__(parent)
        self.setVerticalScrollMode(1)
        self.setHorizontalScrollMode(1)
        self.maxheight = maxheight
        self.verticalHeader().setDefaultSectionSize(22)  # row height
        self.setSortingEnabled(True)
        self.verticalHeader().setVisible(True)

    @classmethod
    def decorated_sync(cls, sync):
        def wrapper(self, *args, **kwargs):

            sync(self, *args, **kwargs)

            self.model = PandasModel(self.dataframe)
            self.proxy_model = QtCore.QSortFilterProxyModel()  # see: http://doc.qt.io/qt-5/qsortfilterproxymodel.html#details
            self.proxy_model.setSourceModel(self.model)
            self.proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
            self.setModel(self.proxy_model)

            # self.resizeColumnsToContents()
            # self.resizeRowsToContents()
            # if self.maxheight is not None:
            #     self.setMaximumHeight(
            #         self.rowHeight(0) * (self.maxheight + 1) + self.autoScrollMargin())
            # elif self.model.rowCount() > 0:
            #     self.setMaximumHeight(
            #         self.rowHeight(0) * (self.model.rowCount() + 1) + self.autoScrollMargin()
            #     )
            # else:
            #     self.setMaximumHeight(50)
            # if self.maxheight is None:
            #     self.setMinimumHeight(
            #         self.rowHeight(0) * (min(self.model.rowCount()+1.5, 20)) + self.autoScrollMargin()
            #     )

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

    @QtCore.pyqtSlot()
    def keyPressEvent(self, e):
        if e.modifiers() and QtCore.Qt.ControlModifier:

            if e.key() == QtCore.Qt.Key_C:  # copy
                selection = self.selectedIndexes()
                rows = sorted(list(set(index.row() for index in selection)))
                columns = sorted(list(set(index.column() for index in selection)))
                self.model._dataframe.iloc[rows, columns].to_clipboard()




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
                value = self._dataframe.iloc[index.row(), index.column()]
                if type(value) == np.float64:  # QVariant cannot use the pandas/numpy float64 type
                    value = float(value)
                return QtCore.QVariant(value)

        return None

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self._dataframe.columns[section]
        elif orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
            return self._dataframe.index[section]
        return None

    # not needed anymore due to the use of QSortFilterProxyModel
    # def sort(self, p_int, order=None):
    #     self.layoutAboutToBeChanged.emit()
    #     self._dataframe.sort_values(by=self._dataframe.columns[p_int],
    #                                 ascending=False if order==1 else True,
    #                                 inplace=True)
    #     self.layoutChanged.emit()