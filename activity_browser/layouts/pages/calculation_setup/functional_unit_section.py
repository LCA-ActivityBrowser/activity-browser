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
        cols = ["unit", "name", "product", "location", "database", "processor"]

        for fu in self.calculation_setup.get("inv", []):
            for key, amount in fu.items():
                keys.append(key)
                amounts.append(amount)

        act_df = AB_metadata.get_metadata(keys, cols)
        act_df["amount"] = amounts
        act_df["_activity_key"] = keys

        act_df["_processor_key"] = act_df["processor"]
        act_df["_processor_key"] = act_df["_processor_key"].fillna(act_df["_activity_key"])

        # Retrieve metadata for unique processor keys, focusing on the "name" column.
        processor_df = AB_metadata.get_metadata(act_df["_processor_key"].unique(), ["name"])

        # Flatten the index of the processor DataFrame to ensure compatibility with merging.
        processor_df.index = processor_df.index.to_flat_index()

        # Merge the processor keys from the activity DataFrame with the processor metadata.
        processor_df = pd.merge(act_df["_processor_key"].astype(object), processor_df, "right",
                                left_on="_processor_key", right_index=True, )

        # Add a column for function keys by flattening the index of the processor DataFrame.
        processor_df["function_keys"] = processor_df.index.to_flat_index()

        # Remove duplicate rows from the processor DataFrame to ensure uniqueness.
        processor_df = processor_df.drop_duplicates()

        # Add the "process" column to the activity DataFrame using the processor names.
        act_df["process"] = processor_df["name"]

        # Use "product" if available otherwise use "name"
        act_df.update(act_df["product"].rename("name"))
        act_df["product"] = act_df["name"]

        cols = ["amount", "unit", "product", "process", "database", "location", "_processor_key", "_activity_key"]

        return act_df[cols].reset_index(drop=True)


class FunctionalUnitView(widgets.ABTreeView):

    class ContextMenu(widgets.ABMenu):
        menuSetup = [
            lambda m, p: m.add(actions.ActivityOpen, m.selected_processes,
                               text="Open process" if len(m.selected_processes) == 1 else "Open processes",
                               enable=len(m.selected_processes) > 0
                               ),
            lambda m: m.addSeparator(),
            lambda m, p: m.add(actions.CSDeleteFunctionalUnit, m.cs_name, m.selected_fus,
                               text="Delete Functional Unit" if len(m.selected_fus) == 1 else "Delete Functional Units",
                               enable=len(m.selected_fus) > 0
                               ),

        ]

        @property
        def selected_fus(self):
            return list(set([index.internalPointer().key() for index in self.parent().selectedIndexes()]))

        @property
        def selected_processes(self):
            return list(set([index.internalPointer()["_processor_key"] for index in self.parent().selectedIndexes()]))

        @property
        def cs_name(self):
            return self.parent().parent().calculation_setup_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

    def mouseDoubleClickEvent(self, event) -> None:
        """
        Handles the mouse double click event to open the selected activities.

        Args:
            event: The mouse double click event.
        """
        if self.selectedIndexes():
            activities = [index.internalPointer()["_processor_key"] for index in self.selectedIndexes()]
            actions.ActivityOpen.run(list(set(activities)))

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
        if key == "process":
            return icons.qicons.process


class FunctionalUnitModel(widgets.ABItemModel):
    dataItemClass = FunctionalUnitItem
