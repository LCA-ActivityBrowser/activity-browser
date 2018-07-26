# -*- coding: utf-8 -*-
import os
import json
from typing import Tuple
from copy import deepcopy

import brightway2 as bw
from PyQt5 import QtWidgets, QtCore, QtWebEngineWidgets, QtWebChannel

from .signals import graphsignals
from ....signals import signals


class GraphNavigatorWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.graph = Graph()
        self.navigation_mode = False

        self.connect_signals()
        self.selected_db = None

        # Help label
        self.help_text = """
        QUICK HELP
        
        Expansion mode (default): clicking on nodes adds downstream (click) or upstream (shift-click) activities, and thus expands the graph 
        Navigation mode: clicking on a node "navigates" to this node (only directly connected activities are shown) 
        
        Checkbox "Add only direct up-/downstream exchanges" - there are two ways to expand the graph: 
            1) adding direct up-/downstream nodes and connections. 
            2) adding direct up-/downstream nodes and connections AS WELL as connections between the added activities and the rest of the graph. 
            The first option is the default as it results in cleaner (but not complete) graphs.    
        """
        self.label_help = QtWidgets.QLabel(self.help_text)
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

        # qt js interaction
        self.bridge = Bridge()
        self.channel = QtWebChannel.QWebChannel()
        self.channel.registerObject('bridge', self.bridge)
        self.view = QtWebEngineWidgets.QWebEngineView()
        self.view.page().setWebChannel(self.channel)
        html = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            'graphviz_navigator2.html')
        self.url = QtCore.QUrl.fromLocalFile(html)

        # Controls Layout
        self.hlay = QtWidgets.QHBoxLayout()
        self.hlay.addWidget(self.button_back)
        self.hlay.addWidget(self.button_forward)
        self.hlay.addWidget(self.button_navigation_mode)
        self.hlay.addWidget(self.button_refresh)
        self.hlay.addWidget(self.button_random_activity)
        self.hlay.addWidget(self.button_toggle_help)
        self.hlay.addStretch(1)

        # Layout
        self.vlay = QtWidgets.QVBoxLayout()
        # self.vlay.addWidget(self.button_refresh)
        # self.vlay.addWidget(self.button_random_activity)
        self.vlay.addLayout(self.hlay)
        self.vlay.addWidget(self.checkbox_direct_only)
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

    def set_database(self, name):
        """
        Saves the currently selected database for graphing a random activity
        Args: takes string of selected database
        """
        self.selected_db = name

    def go_back(self):
        if self.graph.back():
            print("Going back.")
            self.bridge.graph_ready.emit(self.graph.json_data)
        else:
            print("Cannot go back.")

    def go_forward(self):
        if self.graph.forward():
            print("Going foroward.")
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
        Behaviour:
        - left-click: move to node (navigation mode) or expand downstream (expansion mode)
        - left click + shift: expand upstream (expansion mode)
        - left click + alt: remove nodes
        """
        key = click_dict["key"]
        keyboard = click_dict["keyboard"]

        # interpret user command:
        if self.navigation_mode:  # do not expand
            self.new_graph(key)
        else:
            if keyboard["alt"]:  # delete node
                print("Deleting node: ", key)
                self.graph.reduce_graph(key, direct_only=self.checkbox_direct_only.isChecked())
            else: # expansion mode
                print("Expanding graph: ", key)
                if keyboard["shift"]:  # upstream expansion
                    print("Adding upstream nodes.")
                    self.graph.expand_graph(key, up=True, direct_only=self.checkbox_direct_only.isChecked())
                else:  # downstream expansion
                    print("Adding downstream nodes.")
                    self.graph.expand_graph(key, down=True, direct_only=self.checkbox_direct_only.isChecked())
            self.bridge.graph_ready.emit(self.graph.json_data)

    def update_graph_random(self):
        """ Show graph for a random activity in the currently loaded database."""
        self.new_graph(bw.Database(self.selected_db).random().key)

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
        click_dict["key"] = (click_dict["database"], click_dict["id"])
        print("Click information: ", click_dict)
        graphsignals.update_graph.emit(click_dict)


class Graph:

    def __init__(self):
        self.activity = None
        self.nodes = None
        self.edges = None
        self.json_data = None
        self.stack = []  # stores previous graphs, if any, and enables back/forward buttons
        self.forward_stack = []  # stores graphs that can be returned to after having used the "back" button

    def update(self, delete_unstacked=True):
        self.json_data = self.get_JSON_data()
        self.stack.append((deepcopy(self.nodes), deepcopy(self.edges)))
        print("Stacked (Nodes/Edges):", len(self.nodes), len(self.edges))
        if delete_unstacked:
            self.forward_stack = []

    def forward(self):
        print("Forward stack:", self.forward_stack)
        if self.forward_stack:
            print("in forward")
            self.nodes, self.edges = self.forward_stack.pop()
            self.update(delete_unstacked=False)
            return True
        else:
            return False

    def back(self):
        if len(self.stack) > 1:
            self.forward_stack.append(self.stack.pop())  # as the last element is always the current graph
            print("Forward stack:", self.forward_stack)
            self.nodes, self.edges = self.stack.pop()
            print("Un-Stacked (Nodes/Edges):", len(self.nodes), len(self.edges))
            self.update(delete_unstacked=False)
            return True
        else:
            return False
        # while True:  # go back through stack to see if there is a previous graph
        #     if self.stack:
        #         print("one back")
        #         nodes, edges = self.stack.pop()
        #         if nodes != self.nodes:
        #             self.nodes = nodes
        #             self.edges = edges
        #             break
        #     else:
        #         self.stack.append((self.nodes, deepcopy(self.edges)))
        #         return False
        #
        # print("Un-Stacked (Nodes/Edges):", len(self.nodes), len(self.edges))
        # self.update()
        # return True

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

    def new_graph(self, key):
        """Creates a new JSON graph showing the up- and downstream activities for the activity key passed.
        Args:
            key: tuple containing the key of the activity
        Returns:
                JSON data as a string
        """
        self.activity = bw.get_activity(key)
        # add nodes
        up_nodes, down_nodes = self.upstream_and_downstream_nodes(key)
        self.nodes = [self.activity]+up_nodes+down_nodes

        # add edges
        # self.edges = self.inner_exchanges(self.nodes)
        up_exs, down_exs = self.upstream_and_downstream_exchanges(key)
        self.edges = up_exs + down_exs
        self.update()

    def expand_graph(self, key, up=False, down=False, direct_only=True):
        """
        Interprets user behavious. Then adds nodes to the graph depending on the desired behaviour (e.g. upstream, downstream, all nodes).
        Logic: if there already is a downstream activity to this node, then go upstream. Else downstream.
        """
        up_nodes, down_nodes = self.upstream_and_downstream_nodes(key)
        # print("UP-NODES:", up_nodes)
        # print("DOWN-NODES:", down_nodes)

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
                self.edges += up_exs  # TODO: should use something like set() here (but it doesn't work)
            elif down and not up:
                self.edges += down_exs
            elif up and down:
                self.edges += up_exs + down_exs
        else:  # all
            self.edges = self.inner_exchanges(self.nodes)
        self.update()

    def reduce_graph(self, key, direct_only=True):
        act = bw.get_activity(key)
        if not direct_only:
            pass
        else:
            self.nodes.remove(act)
            self.edges = self.inner_exchanges(self.nodes)
        self.update()

    def reduce_graph1(self, key: Tuple[str, str]):
        """ Exploration Function: Reduce graph saved in saved_json by removing the alt+clicked node and direct exchanges
            Removes specified node as well as any dependent nodes which become isolated and their edges
        Args:
            key: tuple containing the key of the activity
        Returns:
                JSON data as a string
        """
        def remove_edges(id: str):
            # filters edges that have the specified node_id as a target or source
            edges_removable = list(filter(lambda x: x.source == id or x.target == id, self.model._data.edges))
            # print('Number of edges to remove: ', len(edges_removable))
            for x in edges_removable:
                try:
                    self.model.remove_edge(x)
                    print("edge removed with source_id: ", x.source)
                except Exception as e:
                    ErrorHandler.trace_error(e)
                    raise
        def remove_nodes(id: str):
            node_removable = list(filter(lambda x: x.id == id, self.model._data.nodes))
            # print('Number of nodes to remove: ', len(node_removable))
            for x in node_removable:
                try:
                    self.model.remove_node(x)
                    print("specified node removed with key: ", id)
                except Exception as e:
                    ErrorHandler.trace_error(e)
                    raise

        activity = bw.get_activity(key)
        print("Head:", activity)
        if key[1] == self.central_node.id:
            print('Central node cannot be removed.')
            return self.model.json()
        # remove alt+clicked node and directly connected edges
        remove_edges(key[1])
        remove_nodes(key[1])

        # retrieve list of orphaned nodes and remove these and their direct edges
        for orphan_id in self.model.get_orphaned_nodes(self.central_node):
            remove_edges(orphan_id)
            remove_nodes(orphan_id)
            print('removed nodes and edges for orphaned node', orphan_id)

        # JSON pickle
        json_data = self.model.json()

        # print("JSON-Data:", json_data)
        return json_data

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
                        "key": node.key,
                        "db": node.key[0],
                        "id": node.key[1],
                        "product": node.get("reference product"),
                        "name": node.get("name"),
                        "location": node.get("location"),
                    }
                    for node in self.nodes
                ]
        edges = [
                    {
                        "source_id": exc.input.key[1],
                        "target_id": exc.output.key[1],
                        "label": exc.input.get("reference product")
                    }
                    for exc in self.edges
                ]
        json_data = {
            "nodes": nodes,
            "edges": edges,
            # "title": self.activity.get("reference product"),
            "title": "Graph",
        }
        print("JSON DATA (Nodes/Edges):", len(nodes), len(edges))
        print(json_data)
        return json.dumps(json_data)

    def save_json_to_file(self, filename="data.json"):
        """ Writes the current model´s JSON representation to the specifies file. """

        json_data = self.model.json()
        if json_data:
            filepath = os.path.join(os.path.dirname(__file__), filename)
            with open(filepath, 'w') as outfile:
                json.dump(json_data, outfile)
