# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets, QtGui

import appdirs
from ..style import style_item

class ABDataFrameTable(QtWidgets.QTableView):
    def __init__(self, parent=None, maxheight=None, *args, **kwargs):
        super(ABDataFrameTable, self).__init__(parent)
        self.setVerticalScrollMode(1)
        self.setHorizontalScrollMode(1)
        # self.maxheight = maxheight
        # self.verticalHeader().setMaximumWidth(100)  # vertical header width
        # self.horizontalHeader().setDefaultSectionSize(150)  # column width
        # self.horizontalHeader().setSectionResizeMode(3)  # QHeaderView::ResizeToContents

        self.setWordWrap(True)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.verticalHeader().setDefaultSectionSize(22)  # row height
        self.verticalHeader().setVisible(True)
        self.dataframe = None
        # self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

    def get_max_height(self):
        return (self.verticalHeader().count())*self.verticalHeader().defaultSectionSize() + \
                 self.horizontalHeader().height() + self.horizontalScrollBar().height() + 5

    def sizeHint(self):
        return QtCore.QSize(self.width(), self.get_max_height())

    @classmethod
    def decorated_sync(cls, sync):
        def wrapper(self, *args, **kwargs):
            sync(self, *args, **kwargs)

            if hasattr(self, 'drag_model'):
                self.model = DragPandasModel(self.dataframe)
            else:
                self.model = PandasModel(self.dataframe)
            self.proxy_model = QtCore.QSortFilterProxyModel()  # see: http://doc.qt.io/qt-5/qsortfilterproxymodel.html#details
            self.proxy_model.setSourceModel(self.model)
            self.proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
            self.setModel(self.proxy_model)

            self.setMaximumHeight(self.get_max_height())

            # self.verticalHeader().setDefaultSectionSize(self.rowHeight(0) - 8)
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

    def get_source_index(self, proxy_index):
        """Returns the index of the original model from a proxymodel index.
        This way data from the self._dataframe can be obtained correctly."""
        # print('Received Index:', proxy_index.row(), proxy_index.column())
        model = proxy_index.model()
        if hasattr(model, 'mapToSource'):
            # We are a proxy model
            source_index = model.mapToSource(proxy_index)
        # print('Source Index:', source_index.row(), source_index.column())
        return source_index

    def to_clipboard(self):
        self.dataframe.to_clipboard()

    def savefilepath(self, default_file_name="LCA results", filter="All Files (*.*)"):

        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            caption='Choose location to save lca results',
            directory=appdirs.AppDirs('ActivityBrowser', 'ActivityBrowser').user_data_dir+"\\" + default_file_name,
            filter=filter,
        )
        return filepath

    def to_csv(self):
        filepath = self.savefilepath(default_file_name="LCA results.csv", filter="CSV (*.csv);; All Files (*.*)")
        if filepath:
            if not filepath.endswith('.csv'):
                filepath += '.csv'
            self.dataframe.to_csv(filepath)

    def to_excel(self):
        filepath = self.savefilepath(default_file_name="LCA results.xlsx", filter="Excel (*.xlsx);; All Files (*.*)")
        if filepath:
            if not filepath.endswith('.xlsx'):
                filepath += '.xlsx'
            self.dataframe.to_excel(filepath)

    @QtCore.pyqtSlot()
    def keyPressEvent(self, e):
        if e.modifiers() and QtCore.Qt.ControlModifier:

            if e.key() == QtCore.Qt.Key_C:  # copy
                # selection = self.selectedIndexes()
                selection = [self.get_source_index(pindex) for pindex in self.selectedIndexes()]
                rows = [index.row() for index in selection]
                columns = [index.column() for index in selection]
                rows = sorted(set(rows), key=rows.index)
                columns = sorted(set(columns), key=columns.index)
                # print('Selected rows/columns:', rows, columns)
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
                try:
                    return QtCore.QVariant(float(value))
                except:
                    return QtCore.QVariant(str(value))
                # if type(value) == np.float64:  # QVariant cannot use the pandas/numpy float64 type
                #     value = float(value)
                # else:
                #     # this enables to show also tuples (e.g. category information like ('air', 'urban air') )
                #     value = str(value)
                # return QtCore.QVariant(value)

            if role == QtCore.Qt.ForegroundRole:
                col_name = self._dataframe.columns[index.column()]
                return QtGui.QBrush(style_item.brushes.get(col_name, style_item.brushes.get("default")))

        return None

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self._dataframe.columns[section]
        elif orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
            return self._dataframe.index[section]
        return None


class DragPandasModel(PandasModel):
    """Same as PandasModel, but enabling dragging."""
    def __init__(self, parent=None):
        super(DragPandasModel, self).__init__(parent)

    def flags(self, index):
            # return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDropEnabled
            return QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
