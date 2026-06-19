from qtpy import QtWidgets, QtGui, QtCore
from qtpy.QtCore import Qt
from loguru import logger

import bw2data as bd
import pandas as pd

from activity_browser import app
from activity_browser.ui import widgets, icons, delegates, core
from activity_browser.bwutils.commontasks import is_node_biosphere
from activity_browser.bwutils.uncertainty import EMPTY_UNCERTAINTY, uncertainty_cell_summary
from .impact_category_header import ImpactCategoryHeader


class ImpactCategoryDetailsPage(widgets.ABAbstractPage):
    _populate_later_flag = False

    def __init__(self, name: tuple, parent=None):
        super().__init__(parent)
        self.name = name
        self.impact_category = bd.Method(name)
        self.is_editable = False

        self.setObjectName("_".join(name))
        self.setWindowTitle(" | ".join(name))

        self.header = ImpactCategoryHeader(self)

        self.view = CharacterizationFactorsView(self)
        self.model = CharacterizationFactorsModel(page=self)
        self.view.setModel(self.model)

        self.build_layout()
        self.connect_signals()
        self.sync()

    def connect_signals(self):
        app.signals.method.renamed.connect(self.on_method_renamed)
        app.signals.method.deleted.connect(self.on_method_deleted)
        app.signals.method.changed.connect(lambda _method: self.syncLater())
        app.signals.database.deleted.connect(lambda _name: self.syncLater())
        app.signals.meta.methods_changed.connect(self.syncLater)
        app.signals.metadata.synced.connect(self.on_metadata_changed)

    def on_metadata_changed(self, added, updated, deleted):
        if not core.qt_is_valid(self):
            return
        changed_keys = added | updated | deleted
        if not changed_keys:
            return
        try:
            cf_ids = {cf[0] for cf in self.impact_category.load()}
        except Exception:
            return
        mdf = app.metadata.dataframe
        for key in changed_keys:
            if key not in mdf.index:
                continue
            if mdf.loc[key, "id"] in cf_ids:
                self.syncLater()
                return

    def on_method_renamed(self, old_name, new_name):
        if not core.qt_is_valid(self):
            return
        if self.name == old_name:
            self.name = new_name
            self.setObjectName(" | ".join(new_name))
            self.setWindowTitle(" | ".join(new_name))

    def on_method_deleted(self, method):
        if method.name == self.name:
            self._close_page()

    def syncLater(self):
        core.schedule_awake_sync(self, self.sync)

    def _close_page(self):
        if core.qt_is_valid(self):
            self.deleteLater()

    def sync(self):
        if not core.qt_is_valid(self):
            return

        logger.log("SYNC", f"{self.__class__.__name__}: {id(self)}")

        if self.name not in bd.methods:
            self._close_page()
            return

        self.impact_category = bd.Method(self.name)
        df = self.build_df()
        df.reset_index(drop=True, inplace=True)
        self.model.set_dataframe(df)
        self.header.sync()

    def build_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.header)
        layout.addWidget(widgets.ABHLine(self))
        layout.addWidget(self.view)
        self.setLayout(layout)

    def build_df(self):
        df = pd.DataFrame(self.impact_category.load(), columns=["id", "data"])
        df["amount"] = df["data"].apply(lambda x: x if isinstance(x, (float, int)) else x.get("amount"))
        df["uncertainty"] = df["data"].apply(
            lambda cf: uncertainty_cell_summary(cf) if isinstance(cf, dict) else ""
        )

        other = app.metadata.dataframe[["id", "name", "categories", "database", "unit"]]

        df = df.merge(other, left_on="id", right_on="id").rename(columns={"id": "_id", "data": "_cf"})
        df["_impact_category_name"] = [self.name for i in range(len(df))]
        df["_editable"] = self.is_editable

        cols = [
            "name", "categories", "database", "amount", "unit", "uncertainty",
            "_id", "_impact_category_name", "_cf", "_editable",
        ]
        return df[cols]

    def uncertainty_from_cf(self, cf):
        if not isinstance(cf, dict):
            return {}
        return {k: v for k, v in cf.items() if k in EMPTY_UNCERTAINTY}


class CharacterizationFactorsView(widgets.ABTreeView):
    defaultColumnDelegates = {
        "amount": delegates.FloatDelegate,
        "categories": delegates.ListDelegate,
        "uncertainty": delegates.UncertaintyDelegate,
    }

    class ContextMenu(widgets.ABMenu):
        menuSetup = [
            lambda m: m.add(
                app.actions.CFUncertaintyModify,
                m.impact_category_name,
                m.char_factors,
                enable=bool(m.char_factors),
                text="View uncertainty…" if not m.is_editable else "Modify uncertainty…",
                read_only=not m.is_editable,
            ),
            lambda m: m.add(app.actions.CFRemove, m.impact_category_name, m.char_factors,
                            enable=bool(m.char_factors) and m.is_editable,
                            text="Remove characterization factor(s)"),
        ]

        @property
        def is_editable(self):
            table_view: CharacterizationFactorsView = self.parent()
            return table_view.page.is_editable

        @property
        def impact_category_name(self):
            table_view: CharacterizationFactorsView = self.parent()
            return table_view.page.name

        @property
        def char_factors(self):
            table_view: CharacterizationFactorsView = self.parent()
            table_model: CharacterizationFactorsModel = table_view.model()

            # SelectRows still returns one index per visible column; keep one CF per row.
            char_factors = []
            seen_rows: set[int] = set()
            for index in table_view.selectedIndexes():
                if index.row() in seen_rows:
                    continue
                seen_rows.add(index.row())
                char_factors.append((
                    table_model.get(index, "_id"),
                    table_model.get(index, "_cf"),
                ))
            return char_factors

    def __init__(self, parent):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSortingEnabled(True)
        self.overlay = None

    @property
    def page(self):
        """Returns the ImpactCategoryDetailsPage associated with the view."""
        return self.parent()

    def dragEnterEvent(self, event):
        """
        Handles the drag enter event.

        Args:
            event: The drag enter event.
        """
        if not self.parent().is_editable:
            event.ignore()
            return

        if event.mimeData().hasFormat("application/bw-nodekeylist"):
            self.overlay = widgets.ABDropOverlay(self)
            self.overlay.show()
            event.accept()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """Handles the drag move event - required for proper drop indicator."""
        if not self.parent().is_editable:
            event.ignore()
            return

        if event.mimeData().hasFormat("application/bw-nodekeylist"):
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """
        Handles the drag leave event.

        Args:
            event: The drag leave event.
        """
        if not self.overlay is None:
            # Reset the palette on drag leave
            self.overlay.deleteLater()
            self.overlay = None

    def dropEvent(self, event):
        """
        Handles the drop event.

        Args:
            event: The drop event.
        """
        self.overlay.deleteLater()
        self.overlay = None

        keys: list = event.mimeData().retrievePickleData("application/bw-nodekeylist")

        # Filter to only biosphere flows
        biosphere_keys = [key for key in keys if is_node_biosphere(key)]

        if biosphere_keys:
            app.actions.CFNew.run(self.parent().name, biosphere_keys)


class CharacterizationFactorsModel(core.ABTreeModel):
    """
    A model representing the characterization factors data.
    """
    def __init__(self, page: ImpactCategoryDetailsPage):
        super().__init__(parent=page, enable_sorting=True)
        self.page = page

    def uncertainty_editor_initial(self, index: QtCore.QModelIndex) -> dict:
        if self.column_name(index) != "uncertainty":
            return {}
        row = self.row(index)
        if row is None:
            return {}
        return self.page.uncertainty_from_cf(row.get("_cf"))

    def uncertainty_editor_read_only(self, index: QtCore.QModelIndex) -> bool:
        if self.column_name(index) != "uncertainty":
            return False
        return not bool(self.get(index, "_editable"))

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        """
        Sorts the model based on the given column and order.

        Args:
            column (int): The column index to sort by.
            order (Qt.SortOrder): The order to sort (ascending or descending).
        """
        column_name = self.columns()[column]
        if column_name == "uncertainty":
            return
        super().sort(column, order)

    def setData(self, index: QtCore.QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        """
        Sets the data for the given index.

        Args:
            index (QtCore.QModelIndex): The index to set data for.
            value: The value to set.
            role (int): The role for which to set the data.

        Returns:
            bool: True if the data was set successfully, False otherwise.
        """
        if role != Qt.ItemDataRole.EditRole:
            return False

        column_name = self.column_name(index)
        row = self.row(index)

        if row is None:
            return False

        if column_name == "amount":
            app.actions.CFAmountModify.run(row["_impact_category_name"], row["_id"], value)
            return True

        if column_name == "uncertainty":
            if not row.get("_editable"):
                return False
            app.actions.CFUncertaintyModify.run(
                row["_impact_category_name"], [(row["_id"], row["_cf"])], uncertainty_dict=value
            )
            return True

        return False

    def decorationData(self, index: QtCore.QModelIndex) -> any:
        """
        Provides decoration data for the model.

        Args:
            index (QtCore.QModelIndex): The index for which to provide decoration data.

        Returns:
            The decoration data for the index.
        """
        column_name = self.column_name(index)
        if column_name == "name":
            return icons.qicons.biosphere

        return None

    def fontData(self, index: QtCore.QModelIndex) -> any:
        """
        Provides font data for the model.

        Args:
            index (QtCore.QModelIndex): The index for which to provide font data.

        Returns:
            QtGui.QFont: The font data for the index.
        """
        column_name = self.column_name(index)
        if column_name == "name":
            font = QtGui.QFont()
            font.setWeight(QtGui.QFont.Weight.DemiBold)
            return font

        return None

    def indexEditable(self, index):
        """
        Returns whether the index is editable.

        Args:
            index (QtCore.QModelIndex): The index to check.

        Returns:
            bool: True if the index is editable, False otherwise.
        """
        column_name = self.column_name(index)
        if column_name == "uncertainty":
            return True
        if column_name == "amount" and self.get(index, "_editable"):
            return True

        return False

