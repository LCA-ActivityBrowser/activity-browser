from logging import getLogger

from qtpy import QtWidgets, QtCore

import bw2data as bd

from activity_browser import actions
from activity_browser.ui.widgets import ABTreeView
from activity_browser.ui.tables import delegates

from .delegates import PropertyDelegate
from .items import ExchangeItem

log = getLogger(__name__)

EXCHANGE_MAP = {
    "natural resource": "biosphere", "emission": "biosphere", "inventory indicator": "biosphere",
    "economic": "biosphere", "social": "biosphere", "product": "technosphere",
    "processwithreferenceproduct": "technosphere", "waste": "technosphere",
}


class ExchangeView(ABTreeView):
    column_delegates = {
        "Amount": delegates.FloatDelegate,
        "Unit": delegates.StringDelegate,
        "Name": delegates.StringDelegate,
        "Location": delegates.StringDelegate,
        "Product": delegates.StringDelegate,
        "Formula": delegates.StringDelegate,
        "Comment": delegates.StringDelegate,
        "Uncertainty": delegates.UncertaintyDelegate,
    }

    class HeaderMenu(QtWidgets.QMenu):
        def __init__(self, pos: QtCore.QPoint, view: "ExchangeView"):
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
                if col.startswith("Property"):
                    props_indices.append(i)
                    continue

                action = QtWidgets.QAction(model.columns()[i])
                action.setCheckable(True)
                action.setChecked(not view.isColumnHidden(i))
                action.setData([i])
                self.view_actions.append(action)

                view_menu.addAction(action)

            if props_indices:
                action = QtWidgets.QAction("Properties")
                action.setCheckable(True)
                action.setChecked(not view.isColumnHidden(props_indices[0]))
                action.setData(props_indices)
                self.view_actions.append(action)
                view_menu.addAction(action)

            view_menu.triggered.connect(toggle_slot)

            self.addMenu(view_menu)

            if col_name.startswith("Property: "):
                props = view.activity.get("properties")
                prop_name = col_name[10:]

                self.set_alloc = actions.ActivityModify.get_QAction(view.activity.key, "default_allocation", col_name[10:])
                self.set_alloc.setText(f"Allocate by {col_name[10:]}")
                self.addAction(self.set_alloc)

    class ContextMenu(QtWidgets.QMenu):
        def __init__(self, pos, view: "ExchangeView"):
            super().__init__(view)

            self.add_product_action = actions.ActivityNewProduct.get_QAction(view.activity.key)
            self.addAction(self.add_product_action)

            index = view.indexAt(pos)
            if index.isValid():
                item: ExchangeItem = index.internalPointer()

                self.delete_exc_action = actions.ExchangeDelete.get_QAction([item.exchange])
                self.add_property_action = actions.FunctionPropertyAdd.get_QAction(item.exchange.input)

                self.addAction(self.delete_exc_action)
                self.addAction(self.add_property_action)

    def __init__(self, parent):
        super().__init__(parent)
        self.setAcceptDrops(True)

    @property
    def activity(self):
        return self.parent().activity

    def setModel(self, model):
        super().setModel(model)
        self.model().modelReset.connect(self.set_column_delegates)

    def set_column_delegates(self):
        columns = self.model().columns()

        for i, col_name in enumerate(columns):
            if col_name in self.column_delegates:
                self.setItemDelegateForColumn(i, self.column_delegates[col_name](self))
            elif col_name.startswith("Property: "):
                self.setItemDelegateForColumn(i, PropertyDelegate(self))

    def dragMoveEvent(self, event) -> None:
        pass

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/bw-nodekeylist"):
            keys: list = event.mimeData().retrievePickleData("application/bw-nodekeylist")
            event.accept()

    def dropEvent(self, event):
        event.accept()
        log.debug(f"Dropevent from: {type(event.source()).__name__} to: {self.__class__.__name__}")
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

