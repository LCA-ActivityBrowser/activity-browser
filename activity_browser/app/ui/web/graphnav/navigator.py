# -*- coding: utf-8 -*-
import os
import string
import json
from typing import Tuple

import brightway2 as bw
from bw2data import databases
from PyQt5 import QtWidgets, QtCore, QtWebEngineWidgets, QtWebChannel

from activity_browser.app.ui.web.graphnav.errorhandler import ErrorHandler
from .signals import graphsignals
from ....signals import signals


class GraphNavigatorWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.graph = Graph()

        self.connect_signals()

        # button refresh
        self.button_refresh = QtWidgets.QPushButton('Refresh')
        self.button_refresh.clicked.connect(self.draw_graph)

        # button refresh
        self.button_random_activity = QtWidgets.QPushButton('Random Activity')
        self.button_random_activity.clicked.connect(self.update_graph_random)

        # qt js interaction
        self.bridge = Bridge()
        self.channel = QtWebChannel.QWebChannel()
        self.channel.registerObject('bridge', self.bridge)
        self.view = QtWebEngineWidgets.QWebEngineView()
        self.view.page().setWebChannel(self.channel)
        html = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            'graphviz_navigator2.html')
        self.url = QtCore.QUrl.fromLocalFile(html)

        # Layout
        self.vlay = QtWidgets.QVBoxLayout()
        self.vlay.addWidget(self.button_refresh)
        self.vlay.addWidget(self.button_random_activity)
        self.vlay.addWidget(self.view)
        self.setLayout(self.vlay)

        # graph
        self.draw_graph()

    def connect_signals(self):
        signals.database_selected.connect(self.set_database)
        signals.add_activity_to_history.connect(self.update_graph)
        graphsignals.update_graph.connect(self.update_graph)
        graphsignals.update_graph_expand.connect(self.update_graph_expand)
        #graphsignals.update_graph_expand_upstream.connect(self.update_graph_expand_upstream)
        graphsignals.update_graph_reduce.connect(self.update_graph_reduce)
        graphsignals.graph_ready.connect(self.draw_graph)

    def set_database(self, name):
        self.selected_db = name

    def update_graph(self, key):
        print("Updating Graph for key: ", key)
        try:
            json_data = self.graph.get_json_graph(key)
            self.bridge.graph_ready.emit(json_data)
        except Exception as e:
            ErrorHandler.trace_error(e)
            print("No activity with this key:", key)

    def update_graph_expand(self, key):
        """ Takes key, retrieves JSON data with more downstream nodes, and sends it to js graph_ready func
        Args: 
            key: tuple containing the key of the activity
        """
        print("Expanding graph from key: ", key)
        try:
            json_data = self.graph.get_json_expand_graph(key)
            self.bridge.graph_ready.emit(json_data)
        except Exception as e:
            ErrorHandler.trace_error(e)
            print("No expansion possible with this activity:", key)

    def update_graph_expand_upstream(self, key: str):
        """Takes key, retrieves JSON data with more upstream nodes, and sends it to js graph_ready func
        Args: 
            key: tuple containing the key of the activity
        """
        print("Expanding graph upstream from key: ", key)
        try:
            json_data = self.graph.get_json_expand_graph_upstream(key)
            self.bridge.graph_ready.emit(json_data)
        except Exception as e:
            ErrorHandler.trace_error(e)
            print("No upstream expansion possible with this activity:", key)

    def update_graph_reduce(self, key):  # not complete so far!
        """Takes key, retrieves JSON data with reduced nodes, and sends it to js graph_ready func
        Args:
            key: tuple containing the key of the activity
        """
        print("Reducing graph upstream from key: ", key)
        try:
            json_data = self.graph.get_json_reduce_graph(key)
            self.bridge.graph_ready.emit(json_data)
        except Exception as e:
            ErrorHandler.trace_error(e)
            print("Removal not possible with this activity:", key)

    def update_graph_random(self):
        """changes the database the random activity is taken from to a random one present in the project
        replacing: random_activity=bw.Database("ecoinvent3.4cutoff").random()
        how to access the selected database for random activity?
        """
        try:
            cur_db = self.selected_db
            random_activity = bw.Database(cur_db).random()
            if random_activity is None:
                raise Exception("Failed to pick random activity.")

            print("Database: {} ; Randomkey: {}; {}".format(cur_db, random_activity, type(random_activity)))
            self.update_graph(random_activity)
        except Exception as e:
            ErrorHandler.trace_error(e)
            print('Activity empty, please select a Database!')

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
        graphsignals.update_graph.emit(key)

    @QtCore.pyqtSlot(str)
    def node_clicked_expand(self, js_string):
        """ is called when node is ctrl+clicked for downstream expansion
        Args:
            js_string: string containing the node's database name and the ID of the clicked node
        """
        print("Clicked on to expand: ", js_string)
        db_id = js_string.split(";")
        key = tuple([db_id[0], db_id[1]])
        graphsignals.update_graph_expand.emit(key)

    @QtCore.pyqtSlot(str)
    # TODO: remove this after adding mediating function to call expand or expand_upstream
    def node_clicked_expand_upstream(self, js_string):
        """ is called when node is shift+clicked for upstream expansion
        Args:
            js_string: string containing the node's database name and the ID of the clicked node
        """
        print("Clicked on to expand upstream: ", js_string)
        db_id = js_string.split(";")
        key = tuple([db_id[0], db_id[1]])
        graphsignals.update_graph_expand_upstream.emit(key)

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


class Edge(object):

    def __init__(self, source_id: str, target_id: str, label: str):
        """ Initializes a new instance of the Edge class. """
        self.source_id = source_id
        self.target_id = target_id
        self.label = label

    @property
    def source(self):
        """ Gets a value indicating the current edge´s source node identifier. This property is readonly. """
        return self.source_id

    @property
    def target(self):
        """ Gets a value indicating the current edge´s target node identifier. This property is readonly. """
        return self.target_id


class GraphNode(object):

    def __init__(self, activity_identifier: str, product: str, name: str, location: str, database: str):
        """ Initializes a new instance of the GraphNode class. """
        self.id = activity_identifier
        self.product = product
        self.name = name
        self.location = location
        self.db = database
        self._type = ""

    @property
    def type(self) -> str:
        """ Gets a value indicating the current nodes informative type name. """
        return self._type

    @type.setter
    def type(self, type_name: str):
        """ Sets an informative type that classifies the current node;
        for instance receiver, input, consumer, or such. """
        self._type = type_name


class GraphModel:
    """ Stores the data of a graph and provides functionality to manipulate data. """

    from json import JSONEncoder

    class JsonSerializer(JSONEncoder):
        """ A custom JSON serializer that can be used with json.dumps. """
        def default(self, o):
            """ Returns the object to be used with pickle. """
            return o.__dict__

    class GraphData:
        def __init__(self, dictionary):
            """ Initializes the new instance from the given dictionary. """
            for k, v in dictionary.items():
                setattr(self, k, v)

    def __init__(self):
        """ Initializes a new instance of the GraphModel class. By default the model has empty data. """
        self._data = GraphModel.GraphData({
            "nodes": [],
            "edges": [],
            "title": ""
        })

    @property
    def title(self) -> str:
        """ Gets the graph´s title string. """
        return self._data.title

    @title.setter
    def title(self, title: string):
        """ Sets the graph´s title. """
        self._data.title = title

    def clear(self):
        """ Resets the current model (removes all nodes and edges). """
        self._data.edges = []
        self._data.nodes = []
        self._data.title = ""

    def add_edge(self, edge: Edge):
        """ Adds an edge to the current model. """
        # TODO: check whether the given edge already exists, or not (if yes, skip or raise)
        # TODO: check whether source and target are known nodes to the current model (if not, skip or raise)
        # TODO: check whether source and target of the given edge are equal (if yes, skip or raise) - NOT NEEDED
        # TODO: add function to check for existing downstream nodes
        try:
            self._data.edges.append(edge)
        except Exception as e:
            ErrorHandler.trace_error(e)
            raise

    def remove_edge(self, edge: Edge):
        """ Removes the specified node from the current model instance. """

        def edge_filter_predicate(e: Edge, edge_source_id: str, edge_target_id: str):
            """ A filter function that returns true, if the given edge´s source and target properties equal the
            specified source and target identifiers, otherwise false."""
            if e.source == edge_source_id and e.target == edge_target_id:
                return True

            return False

        # num_edges = self._data.edges.__len__()
        self._data.edges = list(filter(lambda e: edge_filter_predicate(e, edge.source, edge.target), self._data.edges))
        # num_edges_after = self._data.edges.__len__()

    def add_node(self, node: GraphNode):
        """ Adds a node to the current model. """
        # TODO: check whether the given node already exists, or not (if yes, skip or raise)
        self._data.nodes.append(node)

    def remove_node(self, node: GraphNode):
        """ Removes the specifies node from the current model instance. """

        def node_filter_predicate(n: GraphNode, node_id: str):
            """ A filter function that returns true, if the given node´s id property equals the specified identifier,
            otherwise false. """
            if n.id == node_id:
                return True

            return False

        self._data.nodes = list(filter(lambda n: node_filter_predicate(n, node.id) is False, self._data.nodes))

    def json(self):
        """ Returns a JSON representation of the current model´s graph data. """
        try:
            return json.dumps(self._data, cls=GraphModel.JsonSerializer)
        except Exception as e:
            ErrorHandler.trace_error(e)
            raise


class Graph:

    def __init__(self):
        self.model = GraphModel()

        # TODO: since all methods obtain the activity via the given key, there´s actually no need to it in a field.
        self.activity = None

    def get_json_graph(self, key: Tuple[str, str]):
        # TODO: remove test print statements
        """Creates JSON graph for an activity
        Args:
            key: tuple containing the key of the activity
        Returns:
                JSON data as a string
        """
        activity = bw.get_activity(key)
        print("Head:", activity)

        # forget all nodes and edges
        self.model.clear()

        # all inputs
        exchanges = activity.technosphere()
        for exchange in exchanges:
            edge = Edge(
                exchange.input.key[1],
                exchange.output.key[1],
                exchange.input.get("reference product"))
            self.model.add_edge(edge)
            node = GraphNode(
                exchange.input.key[1],
                exchange.input.get("reference product"),
                exchange.input.get("name"),
                exchange.input.get("location"),
                exchange.input.key[0])
            node.type = "input"
            self.model.add_node(node)

        # all downstream consumers
        for row, exchange in enumerate(activity.upstream()):
            edge = Edge(
                exchange.input.key[1],
                exchange.output.key[1],
                exchange.output.get("reference product"))
            self.model.add_edge(edge)
            node = GraphNode(
                exchange.output.key[1],
                exchange.output.get("reference product"),
                exchange.output.get("name"),
                exchange.output.get("location"),
                exchange.output.key[0])
            node.type = "downstream consumer"
            self.model.add_node(node)

        # and the receiving node
        activity_id = activity.key[1]
        activity_database = activity.key[0]
        node = GraphNode(
            activity_id,
            activity.get("reference product"),
            activity.get("name"),
            activity.get("location"),
            activity_database)
        node.type = "receiver"
        self.model.add_node(node)

        self.model.title = activity.get("reference product")

        json_data = self.model.json()


        self.activity = activity
        # print("JSON-Data:", json_data)
        return json_data

    def get_json_expand_graph(self, key: Tuple[str, str]):
        """ Exploration Function: Expand graph saved in saved_json by adding downstream nodes to the ctrl+clicked node
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
            label = output_activity.get("reference product")
            return Edge(source_id, target_id, label)

        def make_node(output_activity) -> GraphNode:
            """ Creates a new node from the specified output activity. """
            activity_identifier = output_activity.key[1]
            activity_database = output_activity.key[0]
            return GraphNode(
                activity_identifier,
                output_activity.get("reference product"),
                output_activity.get("name"),
                output_activity.get("location"),
                activity_database)

        # adds only downstream nodes to the ctrl+clicked node
        activity_exchanges = activity.upstream()
        for index, exchange in enumerate(activity_exchanges):
            try:
                self.model.add_node(make_node(exchange.output))
                self.model.add_edge(make_edge(exchange.input, exchange.output))
            except Exception as e:
                ErrorHandler.trace_error(e)
                print("Failed to create edge/node for exchange: {}.", index)
                raise

        json_data = self.model.json()

        # print("JSON-Data:", json_data)
        return json_data

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

        # add only the upstreams nodes to the shift+clicked node
        exchanges = activity.technosphere()
        for exchange in filter(lambda x: x.output.key[1] == key[1], exchanges):
            self.model.add_node(make_node(exchange.input))
            self.model.add_edge(make_edge(exchange.input, exchange.output))

        # JSON pickle
        json_data = self.model.json()

        # print("JSON-Data:", json_data)
        return json_data

    def get_json_reduce_graph(self, key: Tuple[str, str]):  # NOT DONE!!!!
        """ Exploration Function: Reduce graph saved in saved_json by removing the alt+clicked node
        Args:
            key: tuple containing the key of the activity
        Returns:
                JSON data as a string
        """
        activity = bw.get_activity(key)
        print("Head:", activity)

        # remove alt+clicked node and dependencies ---> NOT DONE
        exchanges = activity.technosphere()
        for exchange in filter(lambda x: x.output.key[1] == key[1], exchanges):
            self.model.remove_edge(Edge(
                exchange.input.key[1],
                exchange.output.key[1],
                exchange.input.get("reference product")))
            self.model.remove_node(GraphNode(
                exchange.input.key[1],
                exchange.input.get("reference product"),
                exchange.input.get("name"),
                exchange.input.get("location"),
                exchange.input.key[0]))

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
