from qtpy import QtWidgets

import bw2data as bd
import pandas as pd

from activity_browser import actions
from activity_browser.ui import widgets, delegates


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
        try:
            self.calculation_setup = bd.calculation_setups[self.calculation_setup_name]
            self.model.setDataFrame(self.build_df())
        except KeyError:
            self.parent().close()
            self.parent().deleteLater()

    def build_df(self):
        data = [bd.methods.get(method_name) for method_name in self.calculation_setup.get("ia", [])]
        df = pd.DataFrame(data, columns=["name", "unit", "num_cfs"])

        df["name"] = self.calculation_setup.get("ia", [])

        cols = ["name", "unit", "num_cfs"]

        return df[cols]


class ImpactCategoryView(widgets.ABTreeView):
    defaultColumnDelegates = {
        "name": delegates.StringDelegate
    }

    class ContextMenu(QtWidgets.QMenu):
        def __init__(self, pos, view: "ImpactCategoryView"):
            super().__init__(view)
            cs_name = view.parent().calculation_setup_name

            if not view.selectedIndexes():
                return

            indices = [index.internalPointer().key() for index in view.selectedIndexes()]

            self.delete_ic_action = actions.CSDeleteImpactCategory.get_QAction(cs_name, indices)
            print(self.delete_ic_action.text())
            self.addAction(self.delete_ic_action)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

    def dragMoveEvent(self, event) -> None:
        pass

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/bw-methodnamelist"):
            event.accept()

    def dropEvent(self, event) -> None:
        event.accept()
        cs_name = self.parent().calculation_setup_name
        method_names = event.mimeData().retrievePickleData("application/bw-methodnamelist")
        actions.CSAddImpactCategory.run(cs_name, method_names)


class ImpactCategoryItem(widgets.ABDataItem):
    pass


class ImpactCategoryModel(widgets.ABItemModel):
    dataItemClass = ImpactCategoryItem
