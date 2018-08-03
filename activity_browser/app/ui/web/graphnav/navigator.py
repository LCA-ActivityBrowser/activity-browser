# -*- coding: utf-8 -*-
import os
import json
from copy import deepcopy
import networkx as nx

import brightway2 as bw
from PyQt5 import QtWidgets, QtCore, QtWebEngineWidgets, QtWebChannel

from .signals import graphsignals
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


class GraphNavigatorWidget(QtWidgets.QWidget):
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
    
    
    NAVIGATION MODE:
    Click on activities to jump to specific activities (instead of expanding the graph).
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        self.graph = Graph()
        self.navigation_mode = False

        self.connect_signals()
        self.selected_db = None

        # Help label
        self.label_help = QtWidgets.QLabel(self.HELP_TEXT)
        self.label_help.setVisible(False)

        # button toggle_help
        self.help = False
        self.button_toggle_help = QtWidgets.QPushButton("Help")
        self.button_toggle_help.clicked.connect(self.toggle_help)

        # button back
        self.button_back = QtWidgets.QPushButton('<<')
        self.button_back.clicked.connect(self.go_back)

        # button forward
        self.button_forward = QtWidgets.QPushButton('>>')
        self.button_forward.clicked.connect(self.go_forward)

        # button navigation/expansion mode
        self.navigation_label = {True: "Current mode: Navigation", False: "Current mode: Expansion"}
        self.button_navigation_mode = QtWidgets.QPushButton(self.navigation_label[self.navigation_mode])
        self.button_navigation_mode.clicked.connect(self.toggle_navigation_mode)

        # button refresh
        self.button_refresh = QtWidgets.QPushButton('Refresh')
        self.button_refresh.clicked.connect(self.draw_graph)

        # button random
        self.button_random_activity = QtWidgets.QPushButton('Random Activity')
        self.button_random_activity.clicked.connect(self.update_graph_random)

        # checkbox all_exchanges_in_graph
        self.checkbox_direct_only = QtWidgets.QCheckBox("Add only direct up-/downstream exchanges")
        self.checkbox_direct_only.setChecked(True)

        # checkbox remove orphaned nodes
        self.checkbox_remove_orphaned_nodes = QtWidgets.QCheckBox("Remove orphaned nodes")
        self.checkbox_remove_orphaned_nodes.setChecked(True)

        # qt js interaction
        self.bridge = Bridge()
        self.channel = QtWebChannel.QWebChannel()
        self.channel.registerObject('bridge', self.bridge)
        self.view = QtWebEngineWidgets.QWebEngineView()
        self.view.page().setWebChannel(self.channel)
        html = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            'navigator.html')
        self.url = QtCore.QUrl.fromLocalFile(html)

        # Controls Layout
        self.hl_controls = QtWidgets.QHBoxLayout()
        self.hl_controls.addWidget(self.button_back)
        self.hl_controls.addWidget(self.button_forward)
        self.hl_controls.addWidget(self.button_navigation_mode)
        self.hl_controls.addWidget(self.button_refresh)
        self.hl_controls.addWidget(self.button_random_activity)
        self.hl_controls.addWidget(self.button_toggle_help)
        self.hl_controls.addStretch(1)

        # Checkboxes Layout
        self.hl_checkboxes = QtWidgets.QHBoxLayout()
        self.hl_checkboxes.addWidget(self.checkbox_direct_only)
        self.hl_checkboxes.addWidget(self.checkbox_remove_orphaned_nodes)
        self.hl_checkboxes.addStretch(1)

        # Layout
        self.vlay = QtWidgets.QVBoxLayout()
        self.vlay.addLayout(self.hl_controls)
        self.vlay.addLayout(self.hl_checkboxes)
        self.vlay.addWidget(self.label_help)
        self.vlay.addWidget(self.view)
        self.setLayout(self.vlay)

        # graph
        self.draw_graph()

    def connect_signals(self):
        signals.database_selected.connect(self.set_database)
        signals.add_activity_to_history.connect(self.new_graph)
        graphsignals.update_graph.connect(self.update_graph)

    def toggle_navigation_mode(self):
        self.navigation_mode = not self.navigation_mode
        self.button_navigation_mode.setText(self.navigation_label[self.navigation_mode])
        print("Switched to:", self.navigation_label[self.navigation_mode])

    def toggle_help(self):
        self.help = not self.help
        self.label_help.setVisible(self.help)

    def go_back(self):
        if self.graph.back():
            print("Going back.")
            self.bridge.graph_ready.emit(self.graph.json_data)
        else:
            print("Cannot go back.")

    def go_forward(self):
        if self.graph.forward():
            print("Going forward.")
            self.bridge.graph_ready.emit(self.graph.json_data)
        else:
            print("Cannot go forward.")

    def new_graph(self, key):
        print("New Graph for key: ", key)
        self.graph.new_graph(key)
        self.bridge.graph_ready.emit(self.graph.json_data)

    def update_graph(self, click_dict):
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
        if self.navigation_mode:  # do not expand
            self.new_graph(key)
        else:
            if keyboard["alt"]:  # delete node
                print("Deleting node: ", key)
                self.graph.reduce_graph(
                    key,
                    direct_only=self.checkbox_direct_only.isChecked(),
                    remove_orphaned=self.checkbox_remove_orphaned_nodes.isChecked()
                )
            else: # expansion mode
                print("Expanding graph: ", key)
                if keyboard["shift"]:  # downstream expansion
                    print("Adding downstream nodes.")
                    self.graph.expand_graph(key, down=True, direct_only=self.checkbox_direct_only.isChecked())
                else:  # upstream expansion
                    print("Adding upstream nodes.")
                    self.graph.expand_graph(key, up=True, direct_only=self.checkbox_direct_only.isChecked())
            self.bridge.graph_ready.emit(self.graph.json_data)

    def set_database(self, name):
        """Saves the currently selected database for graphing a random activity"""
        self.selected_db = name

    def update_graph_random(self):
        """ Show graph for a random activity in the currently loaded database."""
        if self.selected_db:
            self.new_graph(bw.Database(self.selected_db).random().key)
        else:
            QtWidgets.QMessageBox.information(None, "Not possible.", "Please load a database first.")

    def draw_graph(self):
        self.view.load(self.url)


class Bridge(QtCore.QObject):
    graph_ready = QtCore.pyqtSignal(str)

    @QtCore.pyqtSlot(str)
    def node_clicked(self, click_text):
        """ Is called when a node is clicked in Javascript.
        Args:
            click_text: string of a serialized json dictionary describing
            - the node that was clicked on
            - mouse button and additional keys pressed
        """
        click_dict = json.loads(click_text)
        click_dict["key"] = (click_dict["database"], click_dict["id"])  # since JSON does not know tuples
        print("Click information: ", click_dict)
        graphsignals.update_graph.emit(click_dict)


class Graph:
    """Python side representation of the graph.
    Functionality for graph navigation (e.g. adding and removing nodes).
    A JSON representation of the graph (edges and nodes) enables its use in javascript/html/css.
    """

    def __init__(self):
        self.central_activity = None
        self.nodes = None
        self.edges = None
        self.json_data = None
        self.stack = []  # stores previous graphs, if any, and enables back/forward buttons
        self.forward_stack = []  # stores graphs that can be returned to after having used the "back" button

    def update(self, delete_unstacked=True):
        self.json_data = self.get_JSON_data()
        self.stack.append((deepcopy(self.nodes), deepcopy(self.edges)))
        # print("Stacked (Nodes/Edges):", len(self.nodes), len(self.edges))
        if delete_unstacked:
            self.forward_stack = []

    def forward(self):
        """Go forward, if previously gone back."""
        if self.forward_stack:
            self.nodes, self.edges = self.forward_stack.pop()
            self.update(delete_unstacked=False)
            return True
        else:
            return False

    def back(self):
        """Go back to previous graph, if any."""
        if len(self.stack) > 1:
            self.forward_stack.append(self.stack.pop())  # as the last element is always the current graph
            # print("Forward stack:", self.forward_stack)
            self.nodes, self.edges = self.stack.pop()
            # print("Un-Stacked (Nodes/Edges):", len(self.nodes), len(self.edges))
            self.update(delete_unstacked=False)
            return True
        else:
            return False

    def upstream_and_downstream_nodes(self, key):
        """Returns the upstream and downstream activity objects for a key. """
        activity = bw.get_activity(key)
        upstream_nodes = [ex.input for ex in activity.technosphere()]
        downstream_nodes = [ex.output for ex in activity.upstream()]
        return upstream_nodes, downstream_nodes

    def upstream_and_downstream_exchanges(self, key):
        """Returns the upstream and downstream Exchange objects for a key. (act.upstream refers to downstream exchanges; brightway is confused here)"""
        activity = bw.get_activity(key)
        return [ex for ex in activity.technosphere()], [ex for ex in activity.upstream()]

    def inner_exchanges(self, nodes):
        """Returns all exchanges (Exchange objects) between a list of nodes."""
        node_keys = [node.key for node in nodes]
        # the if part is the slow part, but MUCH faster if not the object, but just the key is compared
        return [ex for node in nodes for ex in node.technosphere() if
                ex["input"] in node_keys and ex["output"] in node_keys]

    def remove_outside_exchanges(self):
        """
        Ensures that all exchanges are exclusively between nodes of the graph
        (i.e. removes exchanges to previously existing nodes).
        """
        self.edges = [e for e in self.edges if e.input in self.nodes and e.output in self.nodes]

    def new_graph(self, key):
        """Creates a new JSON graph showing the up- and downstream activities for the activity key passed.
        Args:
            key (tuple): activity key
        Returns:
                JSON data as a string
        """
        self.central_activity = bw.get_activity(key)

        # add nodes
        up_nodes, down_nodes = self.upstream_and_downstream_nodes(key)
        self.nodes = [self.central_activity] + up_nodes + down_nodes

        # add edges
        # self.edges = self.inner_exchanges(self.nodes)
        up_exs, down_exs = self.upstream_and_downstream_exchanges(key)
        self.edges = up_exs + down_exs
        self.update()

    def expand_graph(self, key, up=False, down=False, direct_only=True):
        """
        Adds up-, downstream, or both nodes to graph.
        Different behaviour for "direct nodes only" or "all nodes (inner exchanges)" modes.
        """
        up_nodes, down_nodes = self.upstream_and_downstream_nodes(key)

        # Add Nodes
        if up and not down:
            self.nodes = list(set(self.nodes + up_nodes))
        elif down and not up:
            self.nodes = list(set(self.nodes + down_nodes))
        elif up and down:
            self.nodes = list(set(self.nodes + up_nodes + down_nodes))

        # Add Edges / Exchanges
        if direct_only:
            up_exs, down_exs = self.upstream_and_downstream_exchanges(key)
            if up and not down:
                self.edges += up_exs
            elif down and not up:
                self.edges += down_exs
            elif up and down:
                self.edges += up_exs + down_exs
        else:  # all
            self.edges = self.inner_exchanges(self.nodes)
        self.update()

    def reduce_graph(self, key, direct_only=True, remove_orphaned=True):
        """
        Deletes nodes from graph.
        Different behaviour for "direct nodes only" or "all nodes (inner exchanges)" modes.
        Can lead to orphaned nodes, which can be removed or kept.
        """
        act = bw.get_activity(key)
        if act == self.central_activity:
            print("Cannot remove central activity.")
            return
        if direct_only:
            self.nodes.remove(act)
            self.remove_outside_exchanges()
        else:
            self.nodes.remove(act)
            self.edges = self.inner_exchanges(self.nodes)

        if remove_orphaned:  # remove orphaned nodes
            self.remove_orphaned_nodes()

        self.update()

    def remove_orphaned_nodes(self):
        """
        Remove orphaned nodes from graph using the networkx.
        Orphaned nodes are defined as having no path to the central_activity.
        """

        def format_as_weighted_edges(exchanges, activity_objects=False):
            """Returns the exchanges as a list of weighted edges (from, to, weight) for networkx."""
            if activity_objects:
                return [(ex.input, ex.output, ex.amount) for ex in exchanges]
            else:  # keys
                return [(ex["input"], ex["output"], ex["amount"]) for ex in exchanges]

        # construct networkx graph
        G = nx.MultiGraph()
        for node in self.nodes:
            G.add_node(node.key)
        G.add_weighted_edges_from(format_as_weighted_edges(self.edges))

        # identify orphaned nodes
        # checks each node in current dataset whether it is connected to central node
        # adds node_id of orphaned nodes to list
        orphaned_node_ids = []
        for node in G.nodes:
            if not nx.has_path(G, node, self.central_activity.key):# and node != self.central_activity.key:
                orphaned_node_ids.append(node)

        print("\nRemoving ORPHANED nodes:", len(orphaned_node_ids))
        for key in orphaned_node_ids:
            act = bw.get_activity(key)
            print(act["name"], act["location"])
            self.nodes.remove(act)

        # update edges again to remove those that link to nodes that have been deleted
        self.remove_outside_exchanges()

    def get_JSON_data(self):
        """
        Make the JSON graph data from a list of nodes and edges.

        Args:
            nodes: a list of nodes (Activity objects)
            edges: a list of edges (Exchange objects)
        Returns:
            A JSON representation of this.
            """
        nodes = [
                    {
                        # "key": node.key,
                        "db": act.key[0],
                        "id": act.key[1],
                        "product": act.get("reference product") or act.get("name"),
                        "name": act.get("name"),
                        "location": act.get("location"),
                        "class": identify_activity_type(act),
                    }
                    for act in self.nodes
                ]
        edges = [
                    {
                        "source_id": exc.input.key[1],
                        "target_id": exc.output.key[1],
                        "amount": exc.get("amount"),
                        "unit": exc.get("unit"),
                        "product": exc.input.get("reference product") or exc.input.get("name"),
                        "tooltip": '<b>{:.3g} {} of {}<b>'.format(
                        # "tooltip": '{:.3g} {} of {}'.format(
                            exc.get("amount"),
                            exc.get('unit', ''),
                            exc.input.get("reference product") or exc.input.get("name"))
                    }
                    for exc in self.edges
                ]
        json_data = {
            "nodes": nodes,
            "edges": edges,
            "title": self.central_activity.get("reference product"),
        }
        print("JSON DATA (Nodes/Edges):", len(nodes), len(edges))
        print(json_data)
        return json.dumps(json_data)

    def save_json_to_file(self, filename="data.json"):
        """ Writes the current model´s JSON representation to the specifies file. """
        if self.json_data:
            filepath = os.path.join(os.path.dirname(__file__), filename)
            with open(filepath, 'w') as outfile:
                json.dump(self.json_data, outfile)
