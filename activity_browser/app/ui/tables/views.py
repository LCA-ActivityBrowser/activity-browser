# -*- coding: utf-8 -*-
import os
from functools import wraps
from typing import Optional

from PyQt5.QtCore import (QAbstractTableModel, QModelIndex, QSize,
                          QSortFilterProxyModel, Qt, pyqtSlot)
from PyQt5.QtWidgets import QFileDialog, QTableView, QTreeView

from activity_browser.app.settings import ab_settings

from .models import (DragPandasModel, EditableDragPandasModel,
                     EditablePandasModel, PandasModel,
                     SimpleCopyDragPandasModel, SimpleCopyPandasModel)


def dataframe_sync(sync):
    """ Syncs the data from the dataframe into the table view.

    Uses either of the PandasModel classes depending if the class is
    'drag-enabled'.
    """
    @wraps(sync)
    def wrapper(self, *args, **kwargs):
        sync(self, *args, **kwargs)

        self.model = self._select_model()
        # See: http://doc.qt.io/qt-5/qsortfilterproxymodel.html#details
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.setModel(self.proxy_model)
        self._resize()

    return wrapper


class ABDataFrameView(QTableView):
    """ Base class for showing pandas dataframe objects as tables.
    """
    ALL_FILTER = "All Files (*.*)"
    CSV_FILTER = "CSV (*.csv);; All Files (*.*)"
    EXCEL_FILTER = "Excel (*.xlsx);; All Files (*.*)"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollMode(QTableView.ScrollPerPixel)
        self.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.setWordWrap(True)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.verticalHeader().setDefaultSectionSize(22)  # row height
        self.verticalHeader().setVisible(True)

        self.table_name = 'LCA results'
        self.dataframe = None
        # Initialize attributes which are set during the `sync` step.
        # Creating (and typing) them here allows PyCharm to see them as
        # valid attributes.
        self.model: Optional[QAbstractTableModel] = None
        self.proxy_model: Optional[QSortFilterProxyModel] = None

    def get_max_height(self) -> int:
        return (self.verticalHeader().count())*self.verticalHeader().defaultSectionSize() + \
                 self.horizontalHeader().height() + self.horizontalScrollBar().height() + 5

    def sizeHint(self) -> QSize:
        return QSize(self.width(), self.get_max_height())

    def rowCount(self) -> int:
        if getattr(self, "model") is not None:
            return self.model.rowCount()
        return 0

    def _select_model(self) -> QAbstractTableModel:
        """ Select which model to use for the proxy model.
        """
        if hasattr(self, 'drag_model'):
            return DragPandasModel(self.dataframe)
        return PandasModel(self.dataframe)

    def _resize(self):
        """ Custom table resizing to perform after setting new (proxy) model.
        """
        self.setMaximumHeight(self.get_max_height())

    @staticmethod
    def get_source_index(proxy_index: QModelIndex) -> QModelIndex:
        """ Returns the index of the original model from a proxymodel index.

        This way data from the self._dataframe can be obtained correctly.
        """
        model = proxy_index.model()
        if hasattr(model, 'mapToSource'):
            # We are a proxy model
            source_index = model.mapToSource(proxy_index)
            return source_index
        return QModelIndex()  # Returns an invalid index

    def to_clipboard(self):
        """ Copy dataframe to clipboard
        """
        self.dataframe.to_clipboard()

    def savefilepath(self, default_file_name: str, file_filter: str=None):
        """ Construct and return default path where data is stored

        Uses the application directory for AB
        """
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            caption='Choose location to save lca results',
            directory=os.path.join(ab_settings.data_dir, default_file_name),
            filter=file_filter or self.ALL_FILTER,
        )
        return filepath

    def to_csv(self):
        """ Save the dataframe data to a CSV file.
        """
        filepath = self.savefilepath(self.table_name, file_filter=self.CSV_FILTER)
        if filepath:
            if not filepath.endswith('.csv'):
                filepath += '.csv'
            self.dataframe.to_csv(filepath)

    def to_excel(self):
        """ Save the dataframe data to an excel file.
        """
        filepath = self.savefilepath(self.table_name, file_filter=self.EXCEL_FILTER)
        if filepath:
            if not filepath.endswith('.xlsx'):
                filepath += '.xlsx'
            self.dataframe.to_excel(filepath)

    @pyqtSlot()
    def keyPressEvent(self, e):
        """ Allow user to copy selected data from the table

        NOTE: by default, the table headers (column names) are also copied.
        """
        if e.modifiers() and Qt.ControlModifier:
            if e.key() == Qt.Key_C:  # copy
                selection = [self.get_source_index(pindex) for pindex in self.selectedIndexes()]
                rows = [index.row() for index in selection]
                columns = [index.column() for index in selection]
                rows = sorted(set(rows), key=rows.index)
                columns = sorted(set(columns), key=columns.index)
                self.model.to_clipboard(rows, columns)


class ABDataFrameSimpleCopy(ABDataFrameView):
    """ A view-only class which copies values without including headers
    """
    def _select_model(self) -> QAbstractTableModel:
        if hasattr(self, 'drag_model'):
            return SimpleCopyDragPandasModel(self.dataframe)
        return SimpleCopyPandasModel(self.dataframe)


class ABDataFrameEdit(ABDataFrameView):
    """ Inherit from view class but use editable models and more flexible
    sizing.
    """
    def _select_model(self) -> QAbstractTableModel:
        if hasattr(self, 'drag_model'):
            return EditableDragPandasModel(self.dataframe)
        return EditablePandasModel(self.dataframe)

    def _resize(self) -> None:
        self.setMaximumHeight(self.get_max_height())
        self.resizeColumnsToContents()
        self.resizeRowsToContents()


def tree_model_decorate(sync):
    """ Take and execute the given sync function, then build the view model.
    """
    @wraps(sync)
    def wrapper(self, *args, **kwargs):
        sync(self, *args, **kwargs)
        model = self._select_model()
        self.setModel(model)
        self._resize()
    return wrapper


class ABDictTreeView(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setUniformRowHeights(True)
        self.data = {}
        self._connect_signals()

    def _connect_signals(self):
        self.expanded.connect(self._resize)
        self.collapsed.connect(self._resize)

    def _select_model(self):
        """ Returns the model to be used in the view.
        """
        raise NotImplementedError

    @pyqtSlot()
    def _resize(self) -> None:
        """ Resize the first column (usually 'name') whenever an item is
        expanded or collapsed.
        """
        self.resizeColumnToContents(0)
