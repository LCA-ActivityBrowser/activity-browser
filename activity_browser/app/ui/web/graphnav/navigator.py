# -*- coding: utf-8 -*-
from copy import deepcopy
import itertools
import json
import os
from typing import Optional

import brightway2 as bw
import networkx as nx
from PySide2 import QtWidgets
from PySide2.QtCore import Slot

from .base import BaseGraph, BaseNavigatorWidget
from ....signals import signals
from ....bwutils.commontasks import identify_activity_type

# TODO:
# save graph as image
# zoom reverse direction between canvas and minimap
# break long geographies into max length
# enable other layouts (e.g. force)
# random_graph should not work for biosphere
# a selection possibility method would be nice if many nodes are to be added up/downstream (now the only way is to open all and close those that one is not interested in)

# ISSUES:
# - tooltips show values, but these are not scaled to a product system, i.e. the do not make sense as a system


class GraphNavigatorWidget(BaseNavigatorWidget):
    HELP_TEXT = """
    How to use the Graph Navigator:
    
    EXPANSION MODE (DEFAULT):
    Click on activities to expand graph. 
    - click: expand upwards
    - click + shift: expand downstream
    - click + alt: delete activity

    Checkbox "Add only direct up-/downstream exchanges" - there are two ways to expand the graph: 
        1) adding direct up-/downstream nodes and connections (DEFAULT). 
        2) adding direct up-/downstream nodes and connections AS WELL as ALL OTHER connections between the activities in the graph. 
        The first option results in cleaner (but not complete) graphs.    
    
    Checkbox "Remove orphaned nodes": by default nodes that do not link to the central activity (see title) are removed (this may happen after deleting nodes). Uncheck to disable.
    
    Checkbox "Flip negative flows" (experimental): Arrows of negative product flows (e.g. from ecoinvent treatment activities or from substitution) can be flipped. 
    The resulting representation can be more intuitive for understanding the physical product flows (e.g. that wastes are outputs of activities and not negative inputs).   
    
    
    NAVIGATION MODE:
    Click on activities to jump to specific activities (instead of expanding the graph).
    """
    HTML_FILE = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), "navigator.html"
    )

    def __init__(self, parent=None, key=None):
        super().__init__(parent)

        self.graph = Graph()

        # default settings
        self.navigation_label = itertools.cycle(["Current mode: Expansion", "Current mode: Navigation"])
        self.selected_db = None

        self.button_navigation_mode = QtWidgets.QPushButton(next(self.navigation_label))
        self.checkbox_direct_only = QtWidgets.QCheckBox("Add only direct up-/downstream exchanges")
        self.checkbox_remove_orphaned_nodes = QtWidgets.QCheckBox("Remove orphaned nodes")
        self.checkbox_flip_negative_edges = QtWidgets.QCheckBox("Flip negative flows")
        self.layout = QtWidgets.QVBoxLayout()

        # Prepare graph
        self.draw_graph()

        # Construct layout and set signals.
        self.construct_layout()
        self.update_graph_settings()
        self.connect_signals()

        if key:
            self.selected_db = key[0]
            self.new_graph(key)

    @Slot(name="loadFinishedHandler")
    def load_finished_handler(self) -> None:
        """Executed when webpage has been loaded for the first time or refreshed.
        This is needed to resend the json data the first time after the page has completely loaded."""
        # print(time.time(), ": load finished")
        self.send_json()

    def connect_signals(self):
        super().connect_signals()
        self.button_navigation_mode.clicked.connect(self.toggle_navigation_mode)
        # signals.database_selected.connect(self.set_database)
        self.bridge.update_graph.connect(self.update_graph)
        # checkboxes
        self.checkbox_direct_only.stateChanged.connect(self.update_graph_settings)
        self.checkbox_remove_orphaned_nodes.stateChanged.connect(self.update_graph_settings)
        self.checkbox_flip_negative_edges.stateChanged.connect(self.update_graph_settings)
        self.checkbox_flip_negative_edges.stateChanged.connect(self.reload_graph)

    def construct_layout(self) -> None:
        """Layout of Graph Navigator"""
        self.label_help.setVisible(False)

        # checkbox all_exchanges_in_graph
        self.checkbox_direct_only.setChecked(True)
        self.checkbox_direct_only.setToolTip(
            "When adding activities, show product flows between ALL activities or just selected up-/downstream flows")

        # checkbox remove orphaned nodes
        self.checkbox_remove_orphaned_nodes.setChecked(True)
        self.checkbox_remove_orphaned_nodes.setToolTip(
            "When removing activities, automatically remove those that have no further connection to the original product")

        # checkbox flip negative edges
        self.checkbox_flip_negative_edges.setChecked(False)
        self.checkbox_flip_negative_edges.setToolTip(
            "Flip negative product flows (e.g. from ecoinvent treatment activities or from substitution)")
        # Controls Layout
        hl_controls = QtWidgets.QHBoxLayout()
        hl_controls.addWidget(self.button_back)
        hl_controls.addWidget(self.button_forward)
        hl_controls.addWidget(self.button_navigation_mode)
        hl_controls.addWidget(self.button_refresh)
        hl_controls.addWidget(self.button_random_activity)
        hl_controls.addWidget(self.button_toggle_help)
        hl_controls.addStretch(1)

        # Checkboxes Layout
        hl_checkboxes = QtWidgets.QHBoxLayout()
        hl_checkboxes.addWidget(self.checkbox_direct_only)
        hl_checkboxes.addWidget(self.checkbox_remove_orphaned_nodes)
        hl_checkboxes.addWidget(self.checkbox_flip_negative_edges)
        hl_checkboxes.addStretch(1)

        # Layout
        self.layout.addLayout(hl_controls)
        self.layout.addLayout(hl_checkboxes)
        self.layout.addWidget(self.label_help)
        self.layout.addWidget(self.view)
        self.setLayout(self.layout)

    def update_graph_settings(self):
        self.graph.direct_only = self.checkbox_direct_only.isChecked()
        self.graph.remove_orphaned = self.checkbox_remove_orphaned_nodes.isChecked()
        self.graph.flip_negative_edges = self.checkbox_flip_negative_edges.isChecked()

    @property
    def is_expansion_mode(self) -> bool:
        return "Expansion" in self.button_navigation_mode.text()

    @Slot(name="toggleNavigationMode")
    def toggle_navigation_mode(self):
        mode = next(self.navigation_label)
        self.button_navigation_mode.setText(mode)
        print("Switched to:", mode)
        self.checkbox_remove_orphaned_nodes.setVisible(self.is_expansion_mode)
        self.checkbox_direct_only.setVisible(self.is_expansion_mode)

    def new_graph(self, key: tuple) -> None:
        print("New Graph for key: ", key)
        self.graph.new_graph(key)
        self.send_json()

    @Slot(name="reload_graph")
    def reload_graph(self) -> None:
        signals.new_statusbar_message.emit("Reloading graph")
        self.graph.update(delete_unstacked=False)

    @Slot(object, name="update_graph")
    def update_graph(self, click_dict: dict) -> None:
        """
        Update graph based on user command (click+keyboard) and settings.
        Settings:
        - navigation or expansion mode
        - add all or only direct up/downstream nodes
        User commands:
        - mouse (left or right button)
        - additional keyboard keys (shift, alt)
        Behaviour: see HELP text
        """
        key = click_dict["key"]
        keyboard = click_dict["keyboard"]

        # interpret user command:
        if not self.is_expansion_mode:  # do not expand
            self.new_graph(key)
        else:
            if keyboard["alt"]:  # delete node
                print("Deleting node: ", key)
                self.graph.reduce_graph(key)
            else: # expansion mode
                print("Expanding graph: ", key)
                if keyboard["shift"]:  # downstream expansion
                    print("Adding downstream nodes.")
                    self.graph.expand_graph(key, down=True)
                else:  # upstream expansion
                    print("Adding upstream nodes.")
                    self.graph.expand_graph(key, up=True)
            self.send_json()

    def set_database(self, name):
        """Saves the currently selected database for graphing a random activity"""
        self.selected_db = name

    @Slot(name="random_graph")
    def random_graph(self) -> None:
        """ Show graph for a random activity in the currently loaded database."""
        if self.selected_db:
            self.new_graph(bw.Database(self.selected_db).random().key)
        else:
            QtWidgets.QMessageBox.information(None, "Not possible.", "Please load a database first.")


class Graph(BaseGraph):
    """Python side representation of the graph.
    Functionality for graph navigation (e.g. adding and removing nodes).
    A JSON representation of the graph (edges and nodes) enables its use in javascript/html/css.
    """

    def __init__(self):
        super().__init__()
        self.central_activity = None
        self.nodes = None
        self.edges = None

        # some settings
        self.direct_only = True  # for a graph expansion: add only direct up-/downstream nodes instead of all connections between the activities in the graph
        self.remove_orphaned = True  # remove nodes that are isolated from the central_activity after a deletion
        self.flip_negative_edges = False  # show true flow direction of edges (e.g. for ecoinvent treatment activities, or substitutions)

    def update(self, delete_unstacked: bool = True) -> None:
        super().update(delete_unstacked)
        self.json_data = self.get_json_data()

    def store_previous(self) -> None:
        self.stack.append((deepcopy(self.nodes), deepcopy(self.edges)))

    def store_future(self) -> None:
        self.forward_stack.append(self.stack.pop())
        self.nodes, self.edges = self.stack.pop()

    def retrieve_future(self) -> None:
        self.nodes, self.edges = self.forward_stack.pop()

    @staticmethod
    def upstream_and_downstream_nodes(key: tuple) -> (list, list):
        """Returns the upstream and downstream activity objects for a key. """
        activity = bw.get_activity(key)
        upstream_nodes = [ex.input for ex in activity.technosphere()]
        downstream_nodes = [ex.output for ex in activity.upstream()]
        return upstream_nodes, downstream_nodes

    @staticmethod
    def upstream_and_downstream_exchanges(key: tuple) -> (list, list):
        """Returns the upstream and downstream Exchange objects for a key.

        act.upstream refers to downstream exchanges; brightway is confused here)
        """
        activity = bw.get_activity(key)
        return [ex for ex in activity.technosphere()], [ex for ex in activity.upstream()]

    @staticmethod
    def inner_exchanges(nodes: list) -> list:
        """Returns all exchanges (Exchange objects) between a list of nodes."""
        node_keys = set(node.key for node in nodes)
        exchanges = itertools.chain(node.technosphere() for node in nodes)
        return [
            ex for ex in exchanges if
            all(k in node_keys for k in (ex["input"], ex["output"]))
        ]

    def remove_outside_exchanges(self) -> None:
        """
        Ensures that all exchanges are exclusively between nodes of the graph
        (i.e. removes exchanges to previously existing nodes).
        """
        self.edges = [e for e in self.edges if all(k in self.nodes for k in (e.input, e.output))]

    def new_graph(self, key: tuple) -> None:
        """Creates a new JSON graph showing the up- and downstream activities for the activity key passed.
        Args:
            key (tuple): activity key
        Returns:
                JSON data as a string
        """
        self.central_activity = bw.get_activity(key)

        # add nodes
        up_nodes, down_nodes = Graph.upstream_and_downstream_nodes(key)
        self.nodes = [self.central_activity] + up_nodes + down_nodes

        # add edges
        # self.edges = self.inner_exchanges(self.nodes)
        up_exs, down_exs = Graph.upstream_and_downstream_exchanges(key)
        self.edges = up_exs + down_exs
        self.update()

    def expand_graph(self, key: tuple, up=False, down=False) -> None:
        """
        Adds up-, downstream, or both nodes to graph.
        Different behaviour for "direct nodes only" or "all nodes (inner exchanges)" modes.
        """
        up_nodes, down_nodes = Graph.upstream_and_downstream_nodes(key)

        # Add Nodes
        if up and not down:
            self.nodes = list(set(self.nodes + up_nodes))
        elif down and not up:
            self.nodes = list(set(self.nodes + down_nodes))
        elif up and down:
            self.nodes = list(set(self.nodes + up_nodes + down_nodes))

        # Add Edges / Exchanges
        if self.direct_only:
            up_exs, down_exs = Graph.upstream_and_downstream_exchanges(key)
            if up and not down:
                self.edges += up_exs
            elif down and not up:
                self.edges += down_exs
            elif up and down:
                self.edges += up_exs + down_exs
        else:  # all
            self.edges = Graph.inner_exchanges(self.nodes)
        self.update()

    def reduce_graph(self, key: tuple) -> None:
        """
        Deletes nodes from graph.
        Different behaviour for "direct nodes only" or "all nodes (inner exchanges)" modes.
        Can lead to orphaned nodes, which can be removed or kept.
        """
        if key == self.central_activity.key:
            print("Cannot remove central activity.")
            return
        act = bw.get_activity(key)
        self.nodes.remove(act)
        if self.direct_only:
            self.remove_outside_exchanges()
        else:
            self.edges = Graph.inner_exchanges(self.nodes)

        if self.remove_orphaned:  # remove orphaned nodes
            self.remove_orphaned_nodes()

        self.update()

    def remove_orphaned_nodes(self) -> None:
        """
        Remove orphaned nodes from graph using the networkx.
        Orphaned nodes are defined as having no path to the central_activity.
        """

        def format_as_weighted_edges(exchanges, activity_objects=False):
            """Returns the exchanges as a list of weighted edges (from, to, weight) for networkx."""
            if activity_objects:
                return ((ex.input, ex.output, ex.amount) for ex in exchanges)
            else:  # keys
                return ((ex["input"], ex["output"], ex["amount"]) for ex in exchanges)

        # construct networkx graph
        G = nx.MultiGraph()
        for node in self.nodes:
            G.add_node(node.key)
        G.add_weighted_edges_from(format_as_weighted_edges(self.edges))

        # identify orphaned nodes
        # checks each node in current dataset whether it is connected to central node
        # adds node_id of orphaned nodes to list
        orphaned_node_ids = (
            node for node in G.nodes
            if not nx.has_path(G, node, self.central_activity.key)
        )

        count = 1
        for count, key in enumerate(orphaned_node_ids, 1):
            act = bw.get_activity(key)
            print(act["name"], act["location"])
            self.nodes.remove(act)
        print("\nRemoved ORPHANED nodes:", count)

        # update edges again to remove those that link to nodes that have been deleted
        self.remove_outside_exchanges()

    def get_json_data(self) -> Optional[str]:
        """
        Make the JSON graph data from a list of nodes and edges.

        Args:
            nodes: a list of nodes (Activity objects)
            edges: a list of edges (Exchange objects)
        Returns:
            A JSON representation of this.
            """
        if not self.nodes:
            print("Graph has no nodes (activities).")
            return

        data = {
            "nodes": [Graph.build_json_node(act) for act in self.nodes],
            "edges": [
                Graph.build_json_edge(exc, self.flip_negative_edges)
                for exc in self.edges
            ],
            "title": self.central_activity.get("reference product"),
        }
        # print("JSON DATA (Nodes/Edges):", len(nodes), len(edges))
        # print(data)
        return json.dumps(data)

    @staticmethod
    def build_json_node(act) -> dict:
        """Take an activity and return a valid JSON document."""
        return {
            "db": act.key[0],
            "id": act.key[1],
            "product": act.get("reference product") or act.get("name"),
            "name": act.get("name"),
            "location": act.get("location"),
            "class": identify_activity_type(act),
        }

    @staticmethod
    def build_json_edge(exc, flip_negative: bool) -> dict:
        """Take an exchange object and return a valid JSON document.

        ``flip_negative`` will change the direction of the edge to represent
        the correct physical flow direction. However, this is experimental,
        and may not be reflected in the actual display of the product/flow.
        """
        product = exc.input
        reference = product.get("reference product") or product.get("name")
        amount = exc.get("amount")
        from_act, to_act = exc.input, exc.output
        if flip_negative and amount < 0:
            from_act, to_act = to_act, from_act
            amount = abs(amount)
        return {
            "source_id": from_act.key[1],
            "target_id": to_act.key[1],
            "amount": amount,
            "unit": exc.get("unit"),
            "product": reference,
            "tooltip": "<b>{:.3g} {} of {}<b>".format(
                amount,
                exc.get("unit", ""),
                reference
            )
        }
