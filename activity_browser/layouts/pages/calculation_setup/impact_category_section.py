from qtpy import QtWidgets

import bw2data as bd
import pandas as pd

from activity_browser import actions
from activity_browser.ui import widgets, icons
from activity_browser.ui.tables import delegates


class ImpactCategorySection(QtWidgets.QWidget):
    def __init__(self, calculation_setup_name: str, parent=None):
        super().__init__(parent)

        self.calculation_setup_name = calculation_setup_name
        self.calculation_setup = bd.calculation_setups.get(self.calculation_setup_name)

        self.view = ImpactCategoryView()
        self.model = ImpactCategoryModel()
        self.view.setModel(self.model)

        self.build_layout()

    def build_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)

    def sync(self):
        self.calculation_setup = bd.calculation_setups[self.calculation_setup_name]
        self.model.setDataFrame(self.build_df())

    def build_df(self):
        data = [bd.methods.get(method_name) for method_name in self.calculation_setup.get("ia", [])]
        df = pd.DataFrame(data)

        df["name"] = self.calculation_setup.get("ia", [])

        cols = ["name", "unit", "num_cfs"]

        return df[cols]


class ImpactCategoryView(widgets.ABTreeView):
    defaultColumnDelegates = {
        "name": delegates.StringDelegate
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

    def dragMoveEvent(self, event) -> None:
        pass

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/bw-methodnamelist"):
            event.accept()

    def dropEvent(self, event) -> None:
        event.accept()
        method_names: list = event.mimeData().retrievePickleData("application/bw-methodnamelist")
        self.model.include_methods(method_names)


class ImpactCategoryItem(widgets.ABDataItem):
    def decorationData(self, col: int, key: str):
        if key == "product":
            return icons.qicons.product


class ImpactCategoryModel(widgets.ABAbstractItemModel):
    dataItemClass = ImpactCategoryItem
