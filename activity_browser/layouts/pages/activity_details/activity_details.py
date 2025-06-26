from logging import getLogger

from qtpy import QtCore, QtWidgets

import bw2data as bd

from activity_browser import signals, bwutils
from activity_browser.ui import widgets

from .activity_header import ActivityHeader
from .exchanges_tab import ExchangesTab
from .description_tab import DescriptionTab
from .graph_tab import GraphTab
from .parameters_tab import ParametersTab
from .data_tab import DataTab
from .consumers_tab import ConsumersTab

log = getLogger(__name__)


class ActivityDetailsPage(QtWidgets.QWidget):
    """
    A widget that displays detailed information about a specific activity.

    Attributes:
        activity (tuple | int | bd.Node): The activity to display details for.
        activity_data_grid (ActivityHeader): The header widget displaying activity data.
        tabs (QtWidgets.QTabWidget): The tab widget containing various detail tabs.
        exchanges_tab (ExchangesTab): The tab displaying exchanges related to the activity.
        description_tab (DescriptionTab): The tab displaying the description of the activity.
        graph_explorer (GraphTab): The tab displaying the graph related to the activity.
        parameters_tab (ParametersTab): The tab displaying parameters of the activity.
        consumer_tab (ConsumersTab): The tab displaying consumers of the activity.
        data_tab (DataTab): The tab displaying data related to the activity.
    """
    _populate_later_flag = False

    def __init__(self, activity: tuple | int | bd.Node, parent=None):
        """
        Initializes the ActivityDetailsPage widget.

        Args:
            activity (tuple | int | bd.Node): The activity to display details for.
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.activity = bd.get_activity(activity)
        self.setObjectName(f"activity_details_{self.activity['database']}_{self.activity['code']}")
        self.setWindowTitle(self.activity["name"])

        # Initialize header widget for activity data
        self.activity_data_grid = ActivityHeader(self)
        # Initialize tab widget to hold various detail tabs
        self.tabs = QtWidgets.QTabWidget(self)

        # Initialize and add the Exchanges tab
        self.exchanges_tab = ExchangesTab(activity, self)
        self.tabs.addTab(self.exchanges_tab, "Exchanges")

        # Initialize and add the Description tab
        self.description_tab = DescriptionTab(activity, self)
        self.tabs.addTab(self.description_tab, "Description")

        # Initialize and add the Graph tab
        self.graph_explorer = GraphTab(activity, self)
        self.tabs.addTab(self.graph_explorer, "Graph")

        # Initialize and add the Parameters tab
        self.parameters_tab = ParametersTab(activity, self)
        self.tabs.addTab(self.parameters_tab, "Parameters")

        # Initialize and add the Consumers tab
        self.consumer_tab = ConsumersTab(activity, self)
        self.tabs.addTab(self.consumer_tab, "Consumers")

        # Initialize and add the Data tab
        self.data_tab = DataTab(activity, self)
        self.tabs.addTab(self.data_tab, "Data")

        # Build the layout of the widget
        self.build_layout()
        # Synchronize the widget with the current state of the activity
        self.sync()
        # Connect signals to their respective slots
        self.connect_signals()

    def build_layout(self):
        """
        Builds the layout of the widget.
        """
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(10, 10, 4, 1)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        # Add the activity data grid and tabs to the layout
        layout.addWidget(self.activity_data_grid)
        layout.addWidget(widgets.ABHLine(self))
        layout.addWidget(self.tabs)

        self.setLayout(layout)

    def connect_signals(self):
        """
        Connects signals to their respective slots.
        """
        signals.node.deleted.connect(self.on_node_deleted)
        signals.database.deleted.connect(self.on_database_deleted)
        signals.meta.databases_changed.connect(self.syncLater)
        signals.parameter.recalculated.connect(self.syncLater)
        signals.node.changed.connect(self.syncLater)

    def on_node_deleted(self, node):
        """
        Slot to handle node deletion.

        Args:
            node: The node that was deleted.
        """
        if node.id == self.activity.id:
            self.deleteLater()

    def on_database_deleted(self, name):
        """
        Slot to handle database deletion.

        Args:
            name: The name of the database that was deleted.
        """
        if name == self.activity["database"]:
            self.deleteLater()

    def syncLater(self):
        """
        Schedules a sync operation to be performed later.
        """

        def slot():
            self._populate_later_flag = False
            self.sync()
            self.thread().eventDispatcher().awake.disconnect(slot)

        if self._populate_later_flag:
            return

        self._populate_later_flag = True
        self.thread().eventDispatcher().awake.connect(slot)

    def sync(self):
        """
        Synchronizes the widget with the current state of the activity.
        """
        self.activity = bwutils.refresh_node_or_none(self.activity)

        if self.activity is None:
            # Activity was already deleted
            return

        # Update the tab name to be the activity name
        self.setWindowTitle(self.activity["name"])

        # Synchronize all tabs with the current state of the activity
        self.activity_data_grid.sync()
        self.exchanges_tab.sync()
        self.description_tab.sync()
        self.consumer_tab.sync()
        self.data_tab.sync()
        self.parameters_tab.sync()
