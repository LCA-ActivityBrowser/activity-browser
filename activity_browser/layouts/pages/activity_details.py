from logging import getLogger

import pandas as pd
from peewee import DoesNotExist

from qtpy import QtCore, QtWidgets, QtGui
from qtpy.QtCore import Slot, Qt

import bw2data as bd

from activity_browser import project_settings, signals, actions
from activity_browser.bwutils import AB_metadata
from activity_browser.ui import icons
from activity_browser.ui.tables import delegates
from activity_browser.ui.widgets import ABTreeView, ABAbstractItemModel, ABDataItem

from ...ui.icons import qicons
from ...ui.style import style_activity_tab
from ...ui.widgets import (
    ActivityDataGrid,
    SignalledPlainTextEdit,
    TagEditor,
)

log = getLogger(__name__)

NODETYPES = {
    "processes": ["process", "multifunctional", "processwithreferenceproduct", "nonfunctional"],
    "products": ["product", "processwithreferenceproduct", "waste"],
    "biosphere": ["natural resource", "emission", "inventory indicator", "economic", "social"],
}

EXCHANGE_MAP = {
    "natural resource": "biosphere", "emission": "biosphere", "inventory indicator": "biosphere",
    "economic": "biosphere", "social": "biosphere", "product": "technosphere",
    "processwithreferenceproduct": "technosphere", "waste": "technosphere",
}



class ActivityDetails(QtWidgets.QWidget):
    """The data relating to Brightway activities can be viewed and edited through this panel interface
    The interface is a GUI representation of the standard activity data format as determined by Brightway
    This is necessitated as AB does not save its own data structures to disk
    Data format documentation is under the heading "The schema for an LCI dataset in voluptuous is:" at this link:
    https://docs.brightway.dev/en/latest/content/theory/structure.html#database-is-a-subclass-of-datastore
    Note that all activity data are optional.
    When activities contain exchanges, some fields are required (input, type, amount)
    Each exchange has a type: production, substitution, technosphere, or biosphere
    AB does not yet support 'substitution'. Other exchange types are shown in separate columns on this interface
    Required and other common exchange data fields are hardcoded as column headers in these tables
    More detail available at: https://docs.brightway.dev/en/latest/content/theory/structure.html#exchange-data-format
    The technosphere products (first table) of the visible activity are consumed by other activities downstream
    The final table of this tab lists these 'Downstream Consumers'
    """

    def __init__(self, key: tuple, read_only=True, parent=None):
        super().__init__(parent)
        self.read_only = read_only
        self.db_read_only = project_settings.db_is_readonly(db_name=key[0])
        self.key = key
        self.db_name = key[0]
        self.activity = bd.get_activity(key)
        self.database = bd.Database(self.db_name)

        # Edit Activity checkbox
        self.checkbox_edit_act = QtWidgets.QCheckBox("Edit Activity")
        self.checkbox_edit_act.setChecked(not self.read_only)
        self.checkbox_edit_act.toggled.connect(lambda checked: self.act_read_only_changed(not checked))

        # Activity Description
        self.activity_description = SignalledPlainTextEdit(
            key=key,
            field="comment",
            parent=self,
        )

        # Activity Description checkbox
        self.checkbox_activity_description = QtWidgets.QCheckBox(
            "Description", parent=self
        )
        self.checkbox_activity_description.clicked.connect(
            self.toggle_activity_description_visibility
        )
        self.checkbox_activity_description.setChecked(not self.read_only)
        self.checkbox_activity_description.setToolTip(
            "Show/hide the activity description"
        )
        self.toggle_activity_description_visibility()

        # Reveal/hide uncertainty columns
        self.checkbox_uncertainty = QtWidgets.QCheckBox("Uncertainty")
        self.checkbox_uncertainty.setToolTip("Show/hide the uncertainty columns")
        self.checkbox_uncertainty.setChecked(False)

        # Reveal/hide exchange comment columns
        self.checkbox_comment = QtWidgets.QCheckBox("Comments")
        self.checkbox_comment.setToolTip("Show/hide the comment column")
        self.checkbox_comment.setChecked(False)

        # Properties button
        properties = QtWidgets.QPushButton("Properties")
        properties.clicked.connect(self.open_property_editor)
        properties.setToolTip("Show the properties dialog")

        # Tags button
        self.tags_button = QtWidgets.QPushButton("Tags")
        self.tags_button.clicked.connect(self.open_tag_editor)
        self.tags_button.setToolTip("Show the tags dialog")

        # Toolbar Layout
        toolbar = QtWidgets.QToolBar()
        self.graph_action = toolbar.addAction(
            qicons.graph_explorer, "Show in Graph Explorer", self.open_graph
        )
        toolbar.addWidget(self.checkbox_edit_act)
        toolbar.addWidget(self.checkbox_activity_description)
        toolbar.addWidget(self.checkbox_uncertainty)
        toolbar.addWidget(self.checkbox_comment)
        toolbar.addWidget(properties)
        toolbar.addWidget(self.tags_button)

        # Activity information
        # this contains: activity name, location, database
        self.activity_data_grid = ActivityDataGrid(
            read_only=self.read_only, parent=self
        )
        self.db_read_only_changed(db_name=self.db_name, db_read_only=self.db_read_only)

        # Exchanges
        self.output_view = ExchangeView(self)
        self.output_model = ExchangeModel(self)
        self.output_view.setModel(self.output_model)

        self.input_view = ExchangeView(self)
        self.input_model = ExchangeModel(self)
        self.input_view.setModel(self.input_model)

        # Full layout
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(10, 10, 4, 1)
        layout.setAlignment(QtCore.Qt.AlignTop)

        layout.addWidget(toolbar)
        layout.addWidget(self.activity_data_grid)
        layout.addWidget(self.activity_description)
        layout.addWidget(QtWidgets.QLabel("<b>Output:</b>"))
        layout.addWidget(self.output_view)
        layout.addWidget(QtWidgets.QLabel("<b>Input:</b>"))
        layout.addWidget(self.input_view)

        self.setLayout(layout)

        self.populate()
        self.update_tooltips()
        self.update_style()
        self.connect_signals()

        # Make the activity tab editable in case it's new
        if not self.read_only:
            self.act_read_only_changed(False)

    def connect_signals(self):
        signals.database_read_only_changed.connect(self.db_read_only_changed)

        signals.node.deleted.connect(self.on_node_deleted)
        signals.database.deleted.connect(self.on_database_deleted)

        signals.node.changed.connect(self.populate)
        signals.edge.changed.connect(self.populate)
        # signals.edge.deleted.connect(self.populate)

        signals.meta.databases_changed.connect(self.populate)

        signals.parameter.recalculated.connect(self.populate)

    def on_node_deleted(self, node):
        if node.id == self.activity.id:
            self.deleteLater()

    def on_database_deleted(self, name):
        if name == self.activity["database"]:
            self.deleteLater()

    def open_graph(self) -> None:
        signals.open_activity_graph_tab.emit(self.key)

    def populate(self) -> None:
        """Populate the various tables and boxes within the Activity Detail tab"""
        if self.db_name in bd.databases:
            # Avoid a weird signal interaction in the tests
            try:
                self.activity = bd.get_activity(self.key)  # Refresh activity.
            except DoesNotExist:
                signals.close_activity_tab.emit(self.key)
                return
        self.populate_description_box()

        # update the object name to be the activity name
        self.setObjectName(self.activity["name"])

        # fill in the values of the ActivityTab widgets, excluding the ActivityDataGrid which is populated separately
        production = self.activity.production()
        technosphere = self.activity.technosphere()
        biosphere = self.activity.biosphere()

        inputs = ([x for x in production if x["amount"] < 0] +
                  [x for x in technosphere if x["amount"] >= 0] +
                  [x for x in biosphere if (x.input["type"] != "emission" and x["amount"] >= 0) or (x.input["type"] == "emission" and x["amount"] < 0)])

        outputs = ([x for x in production if x["amount"] >= 0] +
                   [x for x in technosphere if x["amount"] < 0] +
                   [x for x in biosphere if (x.input["type"] == "emission" and x["amount"] >= 0) or (x.input["type"] != "emission" and x["amount"] < 0)])

        self.output_model.setDataFrame(self.build_df(outputs))
        self.input_model.setDataFrame(self.build_df(inputs))

        self.activity_data_grid.populate()

    def build_df(self, exchanges) -> pd.DataFrame:
        if not exchanges:
            return pd.DataFrame()

        exc_df = pd.DataFrame(exchanges)
        act_df = AB_metadata.get_metadata(exc_df["input"], None)
        df = pd.DataFrame({
            "Amount": list(exc_df["amount"]),
            "Unit": list(act_df["unit"]),
            "Name": list(act_df["name"]),
            "Location": list(act_df["location"]),
            "Exchange Type": list(exc_df["type"]),
            "Activity Type": list(act_df["type"]),
            "Allocation": list(act_df["allocation_factor"]) if "allocation_factor" in act_df.columns else None,
            "_exchange_id": [exc.id for exc in exchanges],
            "_activity_id": list(act_df["id"]),
            "_allocate_by": self.activity.get("default_allocation"),
        })

        if "properties" in act_df.columns:
            for i, props in act_df["properties"].reset_index(drop=True).items():
                if not isinstance(props, dict):
                    continue

                for prop, value in props.items():
                    df.loc[i, f"Property: {prop}"] = value


        return df

    def populate_description_box(self):
        """Populate the activity description."""
        self.activity_description.refresh_text(self.activity.get("comment", ""))
        self.activity_description.setReadOnly(self.read_only)

    def toggle_activity_description_visibility(self) -> None:
        """Show only if checkbox is checked."""
        self.activity_description.setVisible(
            self.checkbox_activity_description.isChecked()
        )

    def act_read_only_changed(self, read_only: bool) -> None:
        """When read_only=False specific data fields in the tables below become user-editable
        When read_only=True these same fields become read-only"""
        self.read_only = read_only
        self.activity_description.setReadOnly(self.read_only)

        if (
            not self.read_only
        ):  # update unique locations, units, etc. for editing (metadata)
            signals.edit_activity.emit(self.db_name)

        self.activity_data_grid.set_activity_fields_read_only(read_only=self.read_only)
        self.activity_data_grid.populate_database_combo()

        self.update_tooltips()
        self.update_style()

    def db_read_only_changed(self, db_name: str, db_read_only: bool) -> None:
        """If database of open activity is set to read-only, the read-only checkbox cannot now be unchecked by user"""
        if db_name == self.db_name:
            self.db_read_only = db_read_only

            # if activity was editable, but now the database is read-only, read_only state must be changed to false.
            if not self.read_only and self.db_read_only:
                self.checkbox_edit_act.setChecked(False)
                self.act_read_only_changed(read_only=True)

            # update checkbox to greyed-out or not
            read_only_process = self.activity.get("type") == "readonly_process"
            self.checkbox_edit_act.setEnabled(not self.db_read_only and not read_only_process)
            self.update_tooltips()

        else:  # on read-only state change for a database different to the open activity...
            # update values in database list to ensure activity cannot be duplicated to read-only db
            self.activity_data_grid.populate_database_combo()

    def update_tooltips(self) -> None:
        if self.db_read_only:
            self.checkbox_edit_act.setToolTip(
                "The database this activity belongs to is read-only."
                " Enable database editing with checkbox in databases list"
            )
        else:
            if self.read_only:
                self.checkbox_edit_act.setToolTip(
                    "Click to enable editing. Edits are saved automatically"
                )
            else:
                self.checkbox_edit_act.setToolTip(
                    "Click to prevent further edits. Edits are saved automatically"
                )

    def update_style(self) -> None:
        # pass
        if self.read_only:
            self.setStyleSheet(style_activity_tab.style_sheet_read_only)
        else:
            self.setStyleSheet(style_activity_tab.style_sheet_editable)

    def open_property_editor(self):
        """Opens the property editor for the current """
        # Do not save the changes if nothing changed
        if PropertyEditor.edit_properties(self.activity, self.read_only, self):
            self.activity.save()
            # Properties changed, redo allocations, the values might have changed
            actions.MultifunctionalProcessRedoAllocation.run(self.activity)

    def open_tag_editor(self):
        """Opens the tag editor for the current"""
        # Do not save the changes if nothing changed
        if TagEditor.edit(self.activity, self.read_only, self):
            self.activity.save()


class ExchangeView(ABTreeView):
    column_delegates = {
        "Amount": delegates.FloatDelegate,
        "Unit": delegates.StringDelegate,
        "Name": delegates.StringDelegate,
        "Location": delegates.StringDelegate,
        "Product": delegates.StringDelegate,
        "Formula": delegates.FormulaDelegate,
        "Comment": delegates.StringDelegate,
        "Uncertainty": delegates.UncertaintyDelegate,
    }

    class HeaderMenu(QtWidgets.QMenu):
        def __init__(self, pos: QtCore.QPoint, view: "ABTreeView"):
            super().__init__(view)

            model = view.model()

            col_index = view.columnAt(pos.x())
            col_name = model.columns()[col_index]

            def toggle_slot(action: QtWidgets.QAction):
                index = action.data()
                hidden = view.isColumnHidden(index)
                view.setColumnHidden(index, not hidden)

            view_menu = QtWidgets.QMenu(view)
            view_menu.setTitle("View")
            self.view_actions = []

            for i in range(1, len(model.columns())):
                action = QtWidgets.QAction(model.columns()[i])
                action.setCheckable(True)
                action.setChecked(not view.isColumnHidden(i))
                action.setData(i)
                view_menu.addAction(action)
                self.view_actions.append(action)

            view_menu.triggered.connect(toggle_slot)

            self.addMenu(view_menu)

    class ContextMenu(QtWidgets.QMenu):
        def __init__(self, pos, view: "ABTreeView"):
            super().__init__(view)

            index = view.indexAt(pos)
            item: ExchangeItem = index.internalPointer()

            self.delete_exc_action = actions.ExchangeDelete.get_QAction([item.exchange])

            self.addAction(self.delete_exc_action)

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
                self.setItemDelegateForColumn(i, delegates.FloatDelegate(self))

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


class ExchangeItem(ABDataItem):
    _exchange: bd.Edge = None

    @property
    def exchange(self):
        from bw2data.backends.proxies import ExchangeDataset
        if self._exchange is None:
            id = self["_exchange_id"]
            self._exchange = bd.Edge(document=ExchangeDataset.get_by_id(id))
        return self._exchange

    def flags(self, col: int, key: str):
        flags = super().flags(col, key)
        if key in ExchangeView.column_delegates:
            return flags | Qt.ItemFlag.ItemIsEditable
        if key.startswith("Property: "):
            return flags | Qt.ItemFlag.ItemIsEditable
        return flags

    def decorationData(self, col, key):
        if key != "Name":
            return

        if self["Activity Type"] in ["process", "processwithreferenceproduct"]:
            return icons.qicons.processproduct
        if self["Activity Type"] in ["natural resource", "emission", "inventory indicator", "economic", "social"]:
            return icons.qicons.biosphere
        if self["Activity Type"] in ["product", "processwithreferenceproduct"]:
            return icons.qicons.product
        if self["Activity Type"] == "waste":
            return icons.qicons.waste

    def fontData(self, col: int, key: str):
        font = super().fontData(col, key)

        # set the font to bold if it's a production/functional exchange
        if self["Exchange Type"] == "production":
            font.setBold(True)
        return font

    def backgroundData(self, col: int, key: str):
        if key == f"Property: {self['_allocate_by']}":
            return QtGui.QBrush(Qt.GlobalColor.lightGray)

    def setData(self, col: int, key: str, value) -> bool:
        if key in ["Amount"]:
            actions.ExchangeModify.run(self.exchange, {"amount": value})
            return True

        if key in ["Unit", "Name", "Location"]:
            act = bd.get_activity(id=self["_activity_id"])

            actions.ActivityModify.run(act.key, key.lower(), value)

        if key.startswith("Property: "):
            act = bd.get_activity(id=self["_activity_id"])
            props = act.get("properties", {})
            props[key[10:]] = value

            actions.ActivityModify.run(act.key, "properties", props)

            process = bd.get_activity(key=act["processor"])
            actions.MultifunctionalProcessRedoAllocation.run(process)

        return False


class ExchangeModel(ABAbstractItemModel):
    dataItemClass = ExchangeItem


