# -*- coding: utf-8 -*-
import os

from PyQt5 import QtCore, QtWidgets

from activity_browser.app.settings import ABSettings

from ..style import style_item
from .models import DragPandasModel, PandasModel


class ABDataFrameTable(QtWidgets.QTableView):
    def __init__(self, parent=None, maxheight=None, *args, **kwargs):
        super(ABDataFrameTable, self).__init__(parent)
        self.setVerticalScrollMode(1)
        self.setHorizontalScrollMode(1)
        self.table_name = 'LCA results'
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
            directory=os.path.join(ABSettings.data_dir, default_file_name),
            filter=filter,
        )
        return filepath

    def to_csv(self):
        filepath = self.savefilepath(default_file_name=self.table_name, filter="CSV (*.csv);; All Files (*.*)")
        if filepath:
            if not filepath.endswith('.csv'):
                filepath += '.csv'
            self.dataframe.to_csv(filepath)

    def to_excel(self):
        filepath = self.savefilepath(default_file_name=self.table_name, filter="Excel (*.xlsx);; All Files (*.*)")
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
                self.model._dataframe.iloc[rows, columns].to_clipboard(index=False)  # index True includes headers
