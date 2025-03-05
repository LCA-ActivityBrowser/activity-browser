from logging import getLogger

from qtpy import QtWidgets, QtCore, QtGui

import bw2data as bd
import pandas as pd

from activity_browser import actions
from activity_browser.ui.widgets import ABTreeView
from activity_browser.ui.tables import delegates

from .delegates import PropertyDelegate
from .items import ExchangesItem, ConsumersItem

log = getLogger(__name__)

EXCHANGE_MAP = {
    "natural resource": "biosphere", "emission": "biosphere", "inventory indicator": "biosphere",
    "economic": "biosphere", "social": "biosphere", "product": "technosphere",
    "processwithreferenceproduct": "technosphere", "waste": "technosphere",
}


class ExchangesView(ABTreeView):
    defaultColumnDelegates = {
        "amount": delegates.FloatDelegate,
        "allocation_factor": delegates.FloatDelegate,
        "substitution_factor": delegates.FloatDelegate,
        "unit": delegates.StringDelegate,
        "name": delegates.StringDelegate,
        "location": delegates.StringDelegate,
        "product": delegates.StringDelegate,
        "formula": delegates.NewFormulaDelegate,
        "comment": delegates.StringDelegate,
        "uncertainty": delegates.UncertaintyDelegate,
    }
    hovered_item: ExchangesItem | None = None

    class HeaderMenu(QtWidgets.QMenu):
        def __init__(self, pos: QtCore.QPoint, view: "ExchangesView"):
            super().__init__(view)

            model = view.model()

            col_index = view.columnAt(pos.x())
            col_name = model.columns()[col_index]

            def toggle_slot(action: QtWidgets.QAction):
                indices = action.data()
                for index in indices:
                    hidden = view.isColumnHidden(index)
                    view.setColumnHidden(index, not hidden)

            view_menu = QtWidgets.QMenu(view)
            view_menu.setTitle("View")

            self.view_actions = []
            props_indices = []

            for i, col in enumerate(model.columns()):
                if col.startswith("property"):
                    props_indices.append(i)
                    continue

                action = QtWidgets.QAction(model.columns()[i])
                action.setCheckable(True)
                action.setChecked(not view.isColumnHidden(i))
                action.setData([i])
                self.view_actions.append(action)

                view_menu.addAction(action)

            if props_indices:
                action = QtWidgets.QAction("properties")
                action.setCheckable(True)
                action.setChecked(not view.isColumnHidden(props_indices[0]))
                action.setData(props_indices)
                self.view_actions.append(action)
                view_menu.addAction(action)

            view_menu.triggered.connect(toggle_slot)

            self.addMenu(view_menu)

            if col_name.startswith("property"):
                self.set_alloc = actions.ActivityModify.get_QAction(view.activity.key, "allocation", col_name[9:])
                self.set_alloc.setText(f"Allocate by {col_name[9:]}")
                self.addAction(self.set_alloc)

    class ContextMenu(QtWidgets.QMenu):
        def __init__(self, pos, view: "ExchangesView"):
            super().__init__(view)

            self.add_product_action = actions.ActivityNewProduct.get_QAction(view.activity.key)
            self.addAction(self.add_product_action)

            index = view.indexAt(pos)
            if index.isValid():
                item: ExchangesItem = index.internalPointer()

                self.delete_exc_action = actions.ExchangeDelete.get_QAction([item.exchange])
                self.exc_to_sdf_action = actions.ExchangeSDFToClipboard.get_QAction([item.exchange])
                self.addAction(self.delete_exc_action)
                self.addAction(self.exc_to_sdf_action)

                if not pd.isna(item["substitute"]):
                    self.remove_sub_action = actions.FunctionSubstituteRemove.get_QAction(item.exchange.input)
                    self.addAction(self.remove_sub_action)

    def __init__(self, parent):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSortingEnabled(True)

        self.propertyDelegate = PropertyDelegate(self)

    @property
    def activity(self):
        return self.parent().activity

    def setDefaultColumnDelegates(self):
        super().setDefaultColumnDelegates()

        columns = self.model().columns()
        for i, col_name in enumerate(columns):
            if not col_name.startswith("property_"):
                continue
            self.setItemDelegateForColumn(i, self.propertyDelegate)

    def dragMoveEvent(self, event) -> None:
        index = self.indexAt(event.pos())
        item = index.internalPointer()

        if self.hovered_item:
            if item == self.hovered_item:
                pass
            elif isinstance(item, ExchangesItem):
                self.hovered_item.background_color = None
                self.hovered_item = item
            else:
                self.hovered_item.background_color = None
                self.hovered_item = None
        elif isinstance(item, ExchangesItem):
            self.hovered_item = item

        if self.hovered_item and self.hovered_item.acceptsDragDrop(event):
            self.hovered_item.background_color = "#ADD8E6"
            self.setPalette(QtGui.QGuiApplication.palette())
            event.acceptProposedAction()
        else:
            self.dragEnterEvent(event)
            event.acceptProposedAction()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/bw-nodekeylist"):
            palette = self.palette()
            palette.setColor(palette.ColorGroup.All, palette.ColorRole.Base, QtGui.QColor("#e8f4f8"))
            self.setPalette(palette)
            event.accept()

    def dragLeaveEvent(self, event):
        if self.hovered_item:
            self.hovered_item.background_color = None
            self.hovered_item = None
        self.setPalette(QtGui.QGuiApplication.palette())

    def dropEvent(self, event):
        log.debug(f"Dropevent from: {type(event.source()).__name__} to: {self.__class__.__name__}")
        self.setPalette(QtGui.QGuiApplication.palette())

        if self.hovered_item and self.hovered_item.acceptsDragDrop(event):
            self.hovered_item.onDrop(event)
            self.hovered_item.background_color = None
            self.setPalette(QtGui.QGuiApplication.palette())
            return

        keys: list = event.mimeData().retrievePickleData("application/bw-nodekeylist")
        exchanges = {"technosphere": set(), "biosphere": set()}

        for key in keys:
            act = bd.get_node(key=key)
            if act["type"] not in EXCHANGE_MAP:
                continue
            exc_type = EXCHANGE_MAP[act["type"]]
            exchanges[exc_type].add(act.key)

        for exc_type, keys in exchanges.items():
            actions.ExchangeNew.run(keys, self.activity.key, exc_type)


class ConsumersView(ABTreeView):
    def mouseDoubleClickEvent(self, event) -> None:
        items = [i.internalPointer() for i in self.selectedIndexes() if isinstance(i.internalPointer(), ConsumersItem)]
        keys = list({i["_consumer_key"] for i in items})
        if keys:
            actions.ActivityOpen.run(keys)

