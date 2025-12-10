from qtpy import QtWidgets
from loguru import logger

import bw2data as bd
import pandas as pd

from activity_browser import app
from activity_browser.ui import widgets, delegates, core


class ImpactCategorySection(QtWidgets.QWidget):
    def __init__(self, calculation_setup_name: str, parent=None):
        super().__init__(parent)

        self.calculation_setup_name = calculation_setup_name
        self.calculation_setup = bd.calculation_setups.get(self.calculation_setup_name)

        self.view = ImpactCategoryView(self)
        self.model = ImpactCategoryModel(parent=self)
        self.view.setModel(self.model)

        self.build_layout()

    def build_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)

    def sync(self):
        logger.debug(f"Syncing {self.__class__.__name__}: {id(self)}")

        try:
            self.calculation_setup = bd.calculation_setups[self.calculation_setup_name]
            df = self.build_df()
            df.reset_index(drop=True, inplace=True)
            self.model.set_dataframe(df)
        except KeyError:
            self.parent().close()
            self.parent().deleteLater()

    def build_df(self):
        data = [bd.methods.get(method_name) for method_name in self.calculation_setup.get("ia", [])]
        df = pd.DataFrame(data, columns=["name", "unit", "num_cfs"])

        df["name"] = self.calculation_setup.get("ia", [])
        df["_cs_name"] = self.calculation_setup_name

        cols = ["name", "unit", "num_cfs", "_cs_name"]

        return df[cols]


class ImpactCategoryView(widgets.ABTreeView):
    defaultColumnDelegates = {
        "name": delegates.StringDelegate
    }

    class ContextMenu(widgets.ABMenu):
        menuSetup = [
            lambda m, p: m.add(app.actions.CSDeleteImpactCategory, m.cs_name, m.selected_ics,
                               text="Delete Impact Category" if len(m.selected_ics) == 1 else "Delete Impact Categories",
                               enable=len(m.selected_ics) > 0
                               ),
        ]

        @property
        def selected_ics(self):
            return self.parent().model().values_from_indices("name", self.parent().selectedIndexes())

        @property
        def cs_name(self):
            return self.parent().parent().calculation_setup_name

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
        app.actions.CSAddImpactCategory.run(cs_name, method_names)


class ImpactCategoryModel(core.ABTreeModel):
    """
    A model representing the data for the impact categories.
    """
    pass
