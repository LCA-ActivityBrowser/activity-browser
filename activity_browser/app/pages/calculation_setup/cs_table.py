"""Reorder + include checkboxes for calculation setup tables."""

from qtpy import QtCore, QtGui, QtWidgets

from activity_browser.bwutils import calculation_setup as cs
from activity_browser.ui import core, delegates, widgets


def _df_row(index: QtCore.QModelIndex) -> int | None:
    node = index.internalPointer()
    if isinstance(node, core.TreeNode) and node.is_leaf:
        return node.df_position
    return None


def _selected_rows(view) -> list[int]:
    return sorted({r for i in view.selectedIndexes() if (r := _df_row(i)) is not None})


def try_reorder_drop(view, event) -> bool:
    if event.source() is not view:
        return False
    model = view.model()
    list_key = getattr(model, "list_key", None)
    if not list_key:
        return False
    pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
    dest_index = view.indexAt(pos).siblingAtColumn(0)
    dest = _df_row(dest_index) if dest_index.isValid() else model.rowCount(QtCore.QModelIndex())
    rows = _selected_rows(view)
    if not rows:
        return False
    cs.reorder(model.df.iloc[rows[0]]["_cs_name"], list_key, rows, dest or 0)
    event.acceptProposedAction()
    return True


class CSListModel(core.ABTreeModel):
    list_key = ""

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if role == QtCore.Qt.ItemDataRole.CheckStateRole and self.indexUserCheckable(index):
            on = bool(self.get(index, "_active"))
            return QtCore.Qt.CheckState.Checked if on else QtCore.Qt.CheckState.Unchecked
        if role == QtCore.Qt.ItemDataRole.ForegroundRole and index.column() > 0 and _df_row(index) is not None:
            if not bool(self.get(index, "_active")):
                return QtGui.QBrush(QtGui.QColor(QtCore.Qt.GlobalColor.gray))
        return super().data(index, role)

    def setData(self, index, value, role=QtCore.Qt.ItemDataRole.EditRole):
        if role == QtCore.Qt.ItemDataRole.CheckStateRole and self.indexUserCheckable(index):
            row = _df_row(index) if _df_row(index) is not None else index.row()
            active = delegates.CheckboxDelegate.is_checked(value)
            cs.set_active(self.get(index, "_cs_name"), self.list_key, row, active)
            return True
        return super().setData(index, value, role)

    def indexUserCheckable(self, index):
        return index.column() == 0 and self.row(index) is not None

    def indexDragEnabled(self, index):
        return self.row(index) is not None

    def indexDropEnabled(self, index):
        return not index.isValid() or self.row(index) is not None


class CSTableView(widgets.ABTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRootIsDecorated(False)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        self.setDragDropOverwriteMode(False)
        self.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)

    def updateIndexColumnVisibility(self):
        self.setColumnHidden(0, False)
        self.setColumnWidth(0, 28)
        self.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)

    def setDefaultColumnDelegates(self):
        super().setDefaultColumnDelegates()
        self.setItemDelegateForColumn(0, delegates.CheckboxDelegate(self))

    def _accept_internal_drag(self, event) -> bool:
        if event.source() is self:
            event.acceptProposedAction()
            return True
        return False

    def dragEnterEvent(self, event):
        if self._accept_internal_drag(event):
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._accept_internal_drag(event):
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        if try_reorder_drop(self, event):
            return
        super().dropEvent(event)
