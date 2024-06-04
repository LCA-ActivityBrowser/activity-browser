from PySide2 import QtWidgets
from PySide2.QtCore import Qt, Slot

from activity_browser import log, signals
from activity_browser.mod.bw2data import calculation_setups

from ..icons import qicons
from .delegates import FloatDelegate
from .impact_categories import MethodsTable, MethodsTree
from .models import CSActivityModel, CSMethodsModel, ScenarioImportModel
from .views import ABDataFrameView


class CSList(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(CSList, self).__init__(parent)
        # Runs even if selection doesn't change
        self.activated["QString"].connect(self.set_cs)
        signals.calculation_setup_selected.connect(self.sync)

    def sync(self, name):
        if not name:
            return
        self.blockSignals(True)
        self.clear()
        keys = sorted(calculation_setups)
        self.insertItems(0, keys)
        self.blockSignals(False)
        self.setCurrentIndex(keys.index(name))

    @staticmethod
    def set_cs(name: str):
        signals.calculation_setup_selected.emit(name)

    @property
    def name(self) -> str:
        return self.currentText()


class CSGenericTable(ABDataFrameView):
    """Generic class to enable internal re-ordering of items in table.

    Items commented out (blass below + first line of init) are intended to help
    with showing a 'drop indicator' where the dragged item would end up.
    This doesn't work yet
    See also comments on PR here: https://github.com/LCA-ActivityBrowser/activity-browser/pull/719
    See also this stackoverflow page: https://stackoverflow.com/questions/61387248/in-pyqt5-how-do-i-properly-move-rows-in-a-qtableview-using-dragdrop
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.setSelectionMode(QtWidgets.QTableView.SingleSelection)

        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QTableView.InternalMove)
        self.setDragDropOverwriteMode(False)

    def mousePressEvent(self, event):
        """Check whether left mouse is pressed and whether CTRL is pressed to change selection mode"""
        if event.button() == Qt.LeftButton:
            if event.modifiers() & Qt.ControlModifier:
                self.setSelectionMode(QtWidgets.QTableView.MultiSelection)
                self.setDragDropMode(QtWidgets.QTableView.DropOnly)
            else:
                self.setSelectionMode(QtWidgets.QTableView.SingleSelection)
                self.setDragDropMode(QtWidgets.QTableView.InternalMove)
        ABDataFrameView.mousePressEvent(self, event)

    def dragMoveEvent(self, event) -> None:
        pass


class CSActivityTable(CSGenericTable):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = CSActivityModel(self)
        self.setItemDelegateForColumn(0, FloatDelegate(self))
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(lambda: self.setColumnHidden(6, True))
        self.model.updated.connect(lambda: self.resizeColumnToContents(2))
        self.model.updated.connect(lambda: self.resizeColumnToContents(3))
        self.setToolTip(
            "Drag Activities from the Activities table to include them as a reference flow\n"
            "Click and drag to re-order individual rows of the table\n"
            "Hold CTRL and click to select multiple rows to open or delete them."
        )

    @Slot(name="openActivities")
    def open_activities(self) -> None:
        keys = set([self.model.get_key(p) for p in self.selectedIndexes()])
        for key in keys:
            signals.safe_open_activity_tab.emit(key)
            signals.add_activity_to_history.emit(key)

    @Slot(name="deleteRows")
    def delete_rows(self):
        self.model.delete_rows(self.selectedIndexes())

    def to_python(self) -> list:
        return self.model.activities

    def mousePressEvent(self, event):
        """Check whether left mouse is pressed and whether CTRL or SHIFT are pressed to change selection mode"""
        if event.button() == Qt.LeftButton:
            if (
                event.modifiers() & Qt.ControlModifier
                or event.modifiers() & Qt.ShiftModifier
            ):
                self.setSelectionMode(QtWidgets.QTableView.ExtendedSelection)
                self.setDragDropMode(QtWidgets.QTableView.DropOnly)
            else:
                self.setSelectionMode(QtWidgets.QTableView.SingleSelection)
                self.setDragDropMode(QtWidgets.QTableView.InternalMove)
        ABDataFrameView.mousePressEvent(self, event)

    def contextMenuEvent(self, event) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QtWidgets.QMenu()
        menu.addAction(qicons.right, "Open activity", self.open_activities)
        menu.addAction(qicons.delete, "Remove row", self.delete_rows)
        menu.exec_(event.globalPos())

    def dragEnterEvent(self, event):
        if getattr(event.source(), "technosphere", False) or event.source() is self:
            event.accept()

    def dropEvent(self, event):
        event.accept()
        source = event.source()
        if getattr(event.source(), "technosphere", False):
            log.info("Dropevent from:", source)
            self.model.include_activities({key: 1.0} for key in source.selected_keys())
        elif event.source() is self:
            selection = self.selectedIndexes()
            from_index = selection[0].row() if selection else -1
            to_index = self.indexAt(event.pos()).row()
            if (
                0 <= from_index < self.model.rowCount()
                and 0 <= to_index < self.model.rowCount()
                and from_index != to_index
            ):
                self.model.relocateRow(from_index, to_index)


class CSMethodsTable(CSGenericTable):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = CSMethodsModel(self)
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(lambda: self.setColumnHidden(3, True))
        self.model.updated.connect(lambda: self.resizeColumnToContents(0))
        self.setToolTip(
            "Drag impact categories from the impact categories tree/table to include them \n"
            "Click and drag to re-order individual rows of the table\n"
            "Hold CTRL and click to select multiple rows to open or delete them."
        )

    def to_python(self):
        return self.model.methods

    def mousePressEvent(self, event):
        """Check whether left mouse is pressed and whether CTRL or SHIFT are pressed to change selection mode"""
        if event.button() == Qt.LeftButton:
            if (
                event.modifiers() & Qt.ControlModifier
                or event.modifiers() & Qt.ShiftModifier
            ):
                self.setSelectionMode(QtWidgets.QTableView.ExtendedSelection)
                self.setDragDropMode(QtWidgets.QTableView.DropOnly)
            else:
                self.setSelectionMode(QtWidgets.QTableView.SingleSelection)
                self.setDragDropMode(QtWidgets.QTableView.InternalMove)
        ABDataFrameView.mousePressEvent(self, event)

    def contextMenuEvent(self, event) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QtWidgets.QMenu()
        menu.addAction(
            qicons.delete,
            "Remove row",
            lambda: self.model.delete_rows(self.selectedIndexes()),
        )
        menu.exec_(event.globalPos())

    def dragEnterEvent(self, event):
        if (
            isinstance(event.source(), (MethodsTable, MethodsTree))
            or event.source() is self
        ):
            event.accept()

    def dropEvent(self, event):
        event.accept()
        source = event.source()
        if isinstance(event.source(), (MethodsTable, MethodsTree)):
            self.model.include_methods(event.source().selected_methods())
        elif event.source() is self:
            selection = self.selectedIndexes()
            from_index = selection[0].row() if selection else -1
            to_index = self.indexAt(event.pos()).row()
            if (
                0 <= from_index < self.model.rowCount()
                and 0 <= to_index < self.model.rowCount()
                and from_index != to_index
            ):
                self.model.relocateRow(from_index, to_index)


class ScenarioImportTable(ABDataFrameView):
    """Self-contained widget that shows the scenario headers for a given
    scenario template dataframe.
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.model = ScenarioImportModel(None, self)
        self.model.updated.connect(self.update_proxy_model)

    def sync(self, names: list):
        self.model.sync(names)
