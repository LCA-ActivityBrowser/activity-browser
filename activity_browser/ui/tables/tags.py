from PySide2 import QtWidgets
from PySide2.QtCore import Slot, Qt, QSortFilterProxyModel
from PySide2.QtWidgets import QAction

from activity_browser.bwutils import AB_metadata
from activity_browser.ui.icons import qicons
from activity_browser.ui.tables.delegates import (
    StringDelegate,
    JSONDelegate,
    ComboBoxDelegate,
)
from activity_browser.ui.tables.models.tags import TagsModel
from activity_browser.ui.tables.views import ABDataFrameView
from activity_browser.ui.widgets.line_edit import AutoCompleteLineEdit


class TagDelegate(StringDelegate):
    def __init__(self, database: str, parent=None):
        super().__init__(parent=parent)
        self.database = database

    def createEditor(self, parent, option, index):
        editor = AutoCompleteLineEdit(AB_metadata.get_tag_names(self.database), parent)
        return editor


class TagTable(ABDataFrameView):

    def __init__(self, tags: dict, database: str, read_only: bool = False, parent=None):
        super().__init__(parent)
        self.read_only = read_only
        self.verticalHeader().setVisible(False)
        self.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        if not read_only:
            self.setItemDelegateForColumn(0, TagDelegate(database, self))
            self.setItemDelegateForColumn(1, JSONDelegate(2, self))
            self.setItemDelegateForColumn(
                2,
                ComboBoxDelegate(
                    [
                        ("Integer", "int"),
                        ("String", "str"),
                        ("Date", "date"),
                    ],
                    self,
                ),
            )
        self.model = TagsModel(TagsModel.dataframe_from_tags(tags), parent=self)
        self.add_tag_button = QAction(qicons.add, "Add Tag", self)
        self.add_tag_button.setStatusTip("Add new tag to the table")
        self.remove_tag_button = QAction(qicons.delete, "Remove Tag", self)
        self.remove_tag_button.setStatusTip("Remove tag from the table")

        self._connect_signals()
        self.update_proxy_model()

    def _connect_signals(self):
        self.add_tag_button.triggered.connect(self.model.add_new_tag)
        self.remove_tag_button.triggered.connect(self.remove_tag)

    @Slot(name="updateProxyModel")
    def update_proxy_model(self) -> None:
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setSortCaseSensitivity(Qt.CaseSensitive)
        self.setModel(self.proxy_model)
        self.sortByColumn(0, Qt.AscendingOrder)

    def remove_tag(self):
        proxy = self.currentIndex()
        self.model.remove_tag(proxy.row())

    def contextMenuEvent(self, event) -> None:
        menu = QtWidgets.QMenu(self)
        if not self.read_only:
            menu.addAction(self.add_tag_button)
        proxy = self.indexAt(event.pos())
        if proxy.row() != -1:
            menu.addAction(self.remove_tag_button)

        menu.exec_(event.globalPos())
