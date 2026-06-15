from qtpy import QtWidgets
from loguru import logger

import bw2data as bd
import pandas as pd

from activity_browser import app
from activity_browser.ui import widgets, delegates
from activity_browser.bwutils.calculation_setup import active_flags
from .cs_table import CSListModel, CSTableView, try_reorder_drop


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
        logger.log("SYNC", f"{self.__class__.__name__}: {id(self)}")

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
        df["_active"] = active_flags(self.calculation_setup, "ia")
        df["_cs_name"] = self.calculation_setup_name

        cols = ["name", "unit", "num_cfs", "_cs_name", "_active"]

        return df[cols]


class ImpactCategoryView(CSTableView):
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
            return list(set([index.row() for index in self.parent().selectedIndexes()]))

        @property
        def cs_name(self):
            return self.parent().parent().calculation_setup_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat("application/bw-methodnamelist"):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/bw-methodnamelist"):
            event.accept()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:
        if try_reorder_drop(self, event):
            return
        if not event.mimeData().hasFormat("application/bw-methodnamelist"):
            super().dropEvent(event)
            return
        event.accept()
        cs_name = self.parent().calculation_setup_name
        method_names = event.mimeData().retrievePickleData("application/bw-methodnamelist")
        app.actions.CSAddImpactCategory.run(cs_name, method_names)


class ImpactCategoryModel(CSListModel):
    list_key = "ia"
