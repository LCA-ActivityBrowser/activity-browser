# -*- coding: utf-8 -*-
import os
import string
import json
from typing import Tuple

import brightway2 as bw
from PyQt5 import QtWidgets, QtCore, QtWebEngineWidgets, QtWebChannel
from networkx import has_path, MultiDiGraph

from .errorhandler import ErrorHandler
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

        # button navigation/expansion mode
        self.navigation_label = {True: "Current mode: Navigation", False: "Current mode: Expansion"}
        self.button_navigation_mode = QtWidgets.QPushButton(self.navigation_label[self.navigation_mode])
        self.button_navigation_mode.clicked.connect(self.toggle_navigation_mode)

        # button refresh
        self.button_refresh = QtWidgets.QPushButton('Refresh')
        self.button_refresh.clicked.connect(self.draw_graph)

        # button refresh
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
        self.hlay.addWidget(self.button_navigation_mode)
        self.hlay.addWidget(self.button_refresh)
        self.hlay.addWidget(self.button_random_activity)
        self.hlay.addWidget(self.button_toggle_help)

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
        graphsignals.update_graph_reduce.connect(self.update_graph_reduce)
        graphsignals.graph_ready.connect(self.draw_graph)

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

    def new_graph(self, key):
        print("New Graph for key: ", key)
        json_data = self.graph.new_graph(key)
        self.bridge.graph_ready.emit(json_data)

    def update_graph(self, key, user_command=None):
        # interpret user command in the context of navigation mode and checkbox_direct_only
        if self.navigation_mode:  # do not expand
            self.new_graph(key)
        else:  # expansion mode
            print("Expanding graph for key: ", key)
            if user_command:
                print("USER COMMAND", user_command)
                if user_command["shift"]:  # upstream expansion
                    print("Adding upstream nodes.")
                    json_data = self.graph.expand_graph(key, up=True, direct_only=self.checkbox_direct_only.isChecked())
            else:  # downstream expansion
                print("Adding downstream nodes.")
                json_data = self.graph.expand_graph(key, down=True, direct_only=self.checkbox_direct_only.isChecked())

            print("JSON DATA:", json_data)
            self.bridge.graph_ready.emit(json_data)

    def update_graph_reduce(self, key):  # not complete so far!
        """Takes key, retrieves JSON data with reduced nodes, and sends it to js graph_ready func
        Args:
            key: tuple containing the key of the activity
        """
        print("Reducing graph upstream from key: ", key)
        try:
            json_data = self.graph.reduce_graph(key)
            self.bridge.graph_ready.emit(json_data)
        except Exception as e:
            ErrorHandler.trace_error(e)
            print("Removal not possible with this activity:", key)

    def update_graph_random(self):
        """ Show graph for a random activity in the currently loaded database."""
        self.new_graph(bw.Database(self.selected_db).random().key)

    def draw_graph(self):
        self.view.load(self.url)


class Bridge(QtCore.QObject):
    graph_ready = QtCore.pyqtSignal(str)

    @QtCore.pyqtSlot(str)
    def node_clicked(self, js_string):
        """ Is called when a node is clicked for navigation
        Args:
            js_string: string containing the node's database name and the ID of the clicked node
        """
        print("Clicked on: ", js_string)
        db_id = js_string.split(";")
        key = tuple([db_id[0], db_id[1]])
        graphsignals.update_graph.emit(key, dict())

    @QtCore.pyqtSlot(str)
    def node_shift_clicked(self, js_string):
        """ is called when node is shift+clicked for expansion
        Args:
            js_string: string containing the node's database name and the ID of the clicked node
        """
        print("Shift clicked on: ", js_string)
        db_id = js_string.split(";")
        key = tuple([db_id[0], db_id[1]])
        user_commands = {"shift": True}
        graphsignals.update_graph.emit(key, user_commands)


    @QtCore.pyqtSlot(str)
    def node_clicked_reduce(self, js_string):
        # TODO: make a mediating function for data selection on what to delete and check for orphaned funcs
        """ is called when node is alt+clicked for reduction of graph
        Args:
            js_string: string containing the node's database name and the ID of the clicked node
        """
        print("Clicked on to remove node: ", js_string)
        db_id = js_string.split(";")
        key = tuple([db_id[0], db_id[1]])
        graphsignals.update_graph_reduce.emit(key)


class Graph:

    def __init__(self):
        self.clear_graph()

    def clear_graph(self):
        self.activity = None
        self.nodes = None
        self.edges = None
        self.json_data = None

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
        self.clear_graph()

        self.activity = bw.get_activity(key)
        # add nodes
        up_nodes, down_nodes = self.upstream_and_downstream_nodes(key)
        self.nodes = [self.activity]+up_nodes+down_nodes

        # add edges
        # self.edges = self.inner_exchanges(self.nodes)
        up_exs, down_exs = self.upstream_and_downstream_exchanges(key)
        self.edges = up_exs + down_exs

        return self.get_JSON_data()

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
            print(type(self.edges))
            up_exs, down_exs = self.upstream_and_downstream_exchanges(key)
            if up and not down:
                self.edges += up_exs  # TODO: should use something like set() here (but it doesn't work)
            elif down and not up:
                self.edges += down_exs
            elif up and down:
                self.edges += up_exs + down_exs
        else:
            self.edges = self.inner_exchanges(self.nodes)

        return self.get_JSON_data()

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
            "title": self.activity.get("reference product"),
        }
        # print("JSON-Data:", json.dumps(json_data))
        return json.dumps(json_data)

    def get_json_expand_graph(self, key: Tuple[str, str]):
        """ Exploration Function: Expand graph saved in saved_json by adding downstream nodes to the ctrl+clicked node
        Args:
            key: tuple containing the key of the activity
        Returns:
                JSON data as a string
        """
        activity = bw.get_activity(key)
        print("Head:", activity)

    def get_json_expand_graph_upstream(self, key: Tuple[str, str]):
        """ Exploration Function: Expand graph saved in saved_json by adding upstream nodes to the shift+clicked node
        Args:
            key: tuple containing the key of the activity
        Returns:
                JSON data as a string
        """

        activity = bw.get_activity(key)
        print("Head:", activity)

        def make_edge(input_activity, output_activity) -> Edge:
            """ Creates a new edge from the specified input and output activities. """
            source_id = input_activity.key[1]
            target_id = output_activity.key[1]
            label = input_activity.get("reference product")
            return Edge(source_id, target_id, label)

        def make_node(input_activity) -> GraphNode:
            """ Creates a new node from the specified input activity. """
            return GraphNode(
                input_activity.key[1],
                input_activity.get("reference product"),
                input_activity.get("name"),
                input_activity.get("location"),
                input_activity.key[0])

        # add only the upstreams nodes to the specified node
        exchanges = activity.technosphere()
        for exchange in filter(lambda x: x.output.key[1] == key[1], exchanges):
            try:
                self.model.add_node(make_node(exchange.input))
                """self.model.add_edge(make_edge(exchange.input, exchange.output))"""
                self.model.complete_edges(exchange.input.key)
            except Exception as e:
                ErrorHandler.trace_error(e)
                raise

        #print('done with adding nodes & edges')
        """print('checking for missing edges')
        self.model.complete_edges()"""
        # JSON pickle
        json_data = self.model.json()

        #print("JSON-Data:", json_data)
        return json_data

    def reduce_graph(self, key: Tuple[str, str]):
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

    def save_json_to_file(self, filename="data.json"):
        """ Writes the current model´s JSON representation to the specifies file. """

        json_data = self.model.json()
        if json_data:
            filepath = os.path.join(os.path.dirname(__file__), filename)
            with open(filepath, 'w') as outfile:
                json.dump(json_data, outfile)

    # def new_graph(self):
    #     print("Sending new Graph Data")
    #     graph_data = self.get_random_graph()
    #     self.bridge.graph_ready.emit(graph_data)
    #     print("Graph Data: ", graph_data)

    # def get_activity_data_str(self, obj):
    #     obj_str = "_".join([
    #         obj.get("reference product"),
    #         # obj.get("name"),
    #         # obj.get("location")
    #     ])
    #     return obj_str

    # def get_graph_data(self, key):
    #     self.activity = bw.get_activity(key)
    #     self.upstream = False
    #
    #     from_to_list = []
    #     for row, exc in enumerate(self.activity.technosphere()):
    #         from_act = self.get_activity_data_str(exc.input)
    #         to_act = self.get_activity_data_str(exc.output)
    #         from_to_list.append((from_act, to_act))
    #     return from_to_list

    # def format_as_dot(self, from_to_list):
    #     graph = 'digraph inventories {\n'
    #     graph += """node[rx = 5 ry = 5 labelStyle = "font: 300 14px 'Helvetica Neue', Helvetica"]
    #     edge[labelStyle = "font: 300 14px 'Helvetica Neue', Helvetica"]"""
    #     for from_act, to_act in from_to_list:
    #         graph +='\n"'+from_act+'"'+' -> '+'"'+to_act+'"'+'; '
    #     graph += '}'
    #     return graph
