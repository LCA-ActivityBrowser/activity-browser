from qtpy import QtWidgets

import bw2data as bd
import pandas as pd

from activity_browser import actions
from activity_browser.ui import widgets, icons
from activity_browser.bwutils import AB_metadata


class FunctionalUnitSection(QtWidgets.QWidget):
    def __init__(self, calculation_setup_name: str, parent=None):
        super().__init__(parent)

        self.calculation_setup_name = calculation_setup_name
        self.calculation_setup = bd.calculation_setups.get(self.calculation_setup_name)

        self.view = FunctionalUnitView()
        self.model = FunctionalUnitModel()
        self.view.setModel(self.model)

        self.build_layout()

    def build_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)

    def sync(self):
        try:
            self.calculation_setup = bd.calculation_setups[self.calculation_setup_name]
            self.model.setDataFrame(self.build_df())
        except KeyError:
            self.parent().close()
            self.parent().deleteLater()

    def build_df(self):
        keys, amounts = [], []
        cols = ["unit", "name", "product", "location", "database"]

        for fu in self.calculation_setup.get("inv", []):
            for key, amount in fu.items():
                keys.append(key)
                amounts.append(amount)

        act_df = AB_metadata.get_metadata(keys, cols)
        act_df["amount"] = amounts
        act_df["_activity_key"] = keys

        cols = ["amount", "unit", "product", "name", "location"]

        return act_df[cols].reset_index(drop=True)


class FunctionalUnitView(widgets.ABTreeView):

    class ContextMenu(QtWidgets.QMenu):
        def __init__(self, pos, view: "FunctionalUnitView"):
            super().__init__(view)
            cs_name = view.parent().calculation_setup_name

            if not view.selectedIndexes():
                return

            indices = [index.internalPointer().key() for index in view.selectedIndexes()]

            self.delete_fu_action = actions.CSDeleteFunctionalUnit.get_QAction(cs_name, indices)
            self.addAction(self.delete_fu_action)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

    def dragMoveEvent(self, event) -> None:
        pass

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/bw-nodekeylist"):
            keys: list = event.mimeData().retrievePickleData("application/bw-nodekeylist")
            for key in keys:
                act = bd.get_node(key=key)
                if act["type"] not in bd.labels.product_node_types + ["processwithreferenceproduct"]:
                    keys.remove(key)

            if not keys:
                return

            event.accept()

    def dropEvent(self, event) -> None:
        event.accept()
        cs_name = self.parent().calculation_setup_name

        keys: list = event.mimeData().retrievePickleData("application/bw-nodekeylist")
        for key in keys:
            act = bd.get_node(key=key)
            if act["type"] not in bd.labels.product_node_types + ["processwithreferenceproduct"]:
                keys.remove(key)

        actions.CSAddFunctionalUnit.run(cs_name, keys)


class FunctionalUnitItem(widgets.ABDataItem):
    def decorationData(self, col: int, key: str):
        if key == "product":
            return icons.qicons.product


class FunctionalUnitModel(widgets.ABItemModel):
    dataItemClass = FunctionalUnitItem
