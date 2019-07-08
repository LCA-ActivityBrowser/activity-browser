# -*- coding: utf-8 -*-
import os

from PyQt5.QtCore import QSize, QSortFilterProxyModel, Qt, pyqtSlot
from PyQt5.QtWidgets import QFileDialog, QTableView

from activity_browser.app.settings import ABSettings

from ..style import style_item
from .models import DragPandasModel, PandasModel


class ABDataFrameView(QTableView):
    def __init__(self, parent=None, maxheight=None, *args, **kwargs):
        super().__init__(parent)
        self.setVerticalScrollMode(1)
        self.setHorizontalScrollMode(1)
        self.setWordWrap(True)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.verticalHeader().setDefaultSectionSize(22)  # row height
        self.verticalHeader().setVisible(True)

        self.table_name = 'LCA results'
        self.dataframe = None

    def get_max_height(self):
        return (self.verticalHeader().count())*self.verticalHeader().defaultSectionSize() + \
                 self.horizontalHeader().height() + self.horizontalScrollBar().height() + 5

    def sizeHint(self):
        return QSize(self.width(), self.get_max_height())

    @classmethod
    def decorated_sync(cls, sync):
        def wrapper(self, *args, **kwargs):
            sync(self, *args, **kwargs)

            if hasattr(self, 'drag_model'):
                self.model = DragPandasModel(self.dataframe)
            else:
                self.model = PandasModel(self.dataframe)
            self.proxy_model = QSortFilterProxyModel()  # see: http://doc.qt.io/qt-5/qsortfilterproxymodel.html#details
            self.proxy_model.setSourceModel(self.model)
            self.proxy_model.setSortCaseSensitivity(Qt.CaseInsensitive)
            self.setModel(self.proxy_model)
            self.setMaximumHeight(self.get_max_height())

        return wrapper

    def get_source_index(self, proxy_index):
        """Returns the index of the original model from a proxymodel index.
        This way data from the self._dataframe can be obtained correctly."""
        model = proxy_index.model()
        if hasattr(model, 'mapToSource'):
            # We are a proxy model
            source_index = model.mapToSource(proxy_index)
        return source_index

    def to_clipboard(self):
        self.dataframe.to_clipboard()

    def savefilepath(self, default_file_name: str, filter="All Files (*.*)"):
        filepath, _ = QFileDialog.getSaveFileName(
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

    @pyqtSlot()
    def keyPressEvent(self, e):
        if e.modifiers() and Qt.ControlModifier:
            if e.key() == Qt.Key_C:  # copy
                selection = [self.get_source_index(pindex) for pindex in self.selectedIndexes()]
                rows = [index.row() for index in selection]
                columns = [index.column() for index in selection]
                rows = sorted(set(rows), key=rows.index)
                columns = sorted(set(columns), key=columns.index)
                self.model._dataframe.iloc[rows, columns].to_clipboard(index=False)  # includes headers
