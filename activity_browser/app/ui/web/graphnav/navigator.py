# -*- coding: utf-8 -*-
import os
import string
import json
from typing import Tuple

import brightway2 as bw
from bw2data import databases
from PyQt5 import QtWidgets, QtCore, QtWebEngineWidgets, QtWebChannel
from networkx import has_path, MultiGraph

from activity_browser.app.ui.web.graphnav.errorhandler import ErrorHandler
from .signals import graphsignals
from ....signals import signals


class GraphNavigatorWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.graph = Graph()

        self.connect_signals()
        self.selected_db = ''

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
        graphsignals.method_chooser.connect(self.method_chooser)
        graphsignals.update_graph_reduce.connect(self.update_graph_reduce)
        graphsignals.graph_ready.connect(self.draw_graph)

    def set_database(self, name):
        """
        Saves the currently selected database for graphing a random activity
        Args: takes string of selected database
        """
        self.selected_db = name

    def update_graph(self, key):
        print("Updating Graph for key: ", key)
        try:
            json_data = self.graph.get_json_graph(key)
            self.bridge.graph_ready.emit(json_data)
        except Exception as e:
            ErrorHandler.trace_error(e)
            print("No activity with this key:", key)

    def method_chooser(self, key):
        if self.graph.model.method_chooser_helper(key) is True:
            print("Upstream Expansion initiated for:", key)
            self.update_graph_expand_upstream(key)
        else:
            print("Downstream Expansion initiated for:", key)
            self.update_graph_expand(key)

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

    def update_graph_expand_upstream(self, key):
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
        """ is called when node is shift+clicked for expansion
        Args:
            js_string: string containing the node's database name and the ID of the clicked node
        """
        print("Clicked on to expand: ", js_string)
        db_id = js_string.split(";")
        key = tuple([db_id[0], db_id[1]])
        graphsignals.method_chooser.emit(key)


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

    class JsonSerializer(json.JSONEncoder):
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
        if len(list(filter(lambda e: e.source_id == edge.source_id and
                                     e.target_id == edge.target_id, self._data.edges))) == 0:
            try:
                self._data.edges.append(edge)
            except Exception as e:
                ErrorHandler.trace_error(e)
                raise
        else:
            print('Edge already present, source_id: {} ; target_id: {}'.format(edge.source_id, edge.target_id))
    def remove_edge(self, edge: Edge):
        """ Removes the specified node from the current model instance. """

        def edge_filter_predicate(e: Edge, edge_source_id: str, edge_target_id: str):
            """ A filter function that returns true, if the given edge´s source and target properties equal the
            specified source and target identifiers, otherwise false."""
            if e.source == edge_source_id and e.target == edge_target_id:
                #print('{} == {}' .format(e.source, edge_source_id))
                return True

            return False

        #num_edges = self._data.edges.__len__()
        #print('no of edges before removal: ', self._data.edges.__len__())
        try:
            self._data.edges = list(
                filter(lambda e: edge_filter_predicate(e, edge.source, edge.target) is False, self._data.edges))
        except Exception as e:
            ErrorHandler.trace_error(e)
            print("Failed to set reduced array of edges")
            raise

        #num_edges_after = self._data.edges.__len__()
        #print('no of edges after removal: ', self._data.edges.__len__())

    def add_node(self, node: GraphNode):
        """ Adds a node to the current model. """
        if len(list(filter(lambda n: n.id == node.id, self._data.nodes))) == 0:
            try:
                self._data.nodes.append(node)
            except Exception as e:
                ErrorHandler.trace_error(e)
                raise
        else:
            print('Node {} already present'.format(node.id))

    def remove_node(self, node: GraphNode):
        """ Removes the specifies node from the current model instance. """

        def node_filter_predicate(n: GraphNode, node_id: str):
            """ A filter function that returns true, if the given node´s id property equals the specified identifier,
            otherwise false. """
            if n.id == node_id:
                #print('{} == {}' .format(n.id, node_id))
                return True

            return False

        #print('no of nodes before removal: ', len(self._data.nodes))
        reduced_nodes = list(filter(lambda n: node_filter_predicate(n, node.id) is False, self._data.nodes))
        #print('no of nodes after removal', len(reduced_nodes))
        try:
            self._data.nodes = list(filter(lambda n: node_filter_predicate(n, node.id) is False, self._data.nodes))
        except Exception as e:
            ErrorHandler.trace_error(e)
            print("Failed to set reduced array of nodes: {}.", node.id)
            raise

    def method_chooser_helper(self, key: Tuple[str, str]):
        """
        Checks current model instance for whether the specified node has any downstream edges connected to it
        and returns True if Yes; returns False if No
        Args: node
        Returns: True or False
        """
        activity = bw.get_activity(key)
        node_id = key[1]
        def contains_source_id(e: Edge, source_id: str):
            """Filter function to return True, if the edges source id is identical to specified source id string"""
            if e.source_id == source_id:
                return True
            return False
        #print("Checking for downstream exchanges present for:", activity, key)
        if len(list(filter(lambda e: contains_source_id(e, node_id), self._data.edges))) >= 1:
            #print("At least one downstream edge seems to be present for:", activity, key)
            return True
        else:
            # print("No downstream edges seem to be present for:", activity, key)
            return False

    def get_orphaned_nodes(self, node_central: GraphNode):
        """Returns a list of orphaned nodes (i.e. who have no path to the central node)
        Args: central node, specified node
        Ret: list of node ids without connection to central node"""
        # creates MultiGraph class for networkx function has_path
        G = MultiGraph()
        # fills node_ids into MultiGraph
        for node in list(self._data.nodes):
            G.add_node(node.id)
        # fills edges (source_id, target_id) into MultiGraph
        for edge in list(self._data.edges):
            G.add_edge(edge.source_id, edge.target_id)

        orphaned_node_ids = []
        #checks each node in current dataset whether it is connected to central node
        #adds node_id of orphaned nodes to list
        for node in G.nodes:
            if not has_path(G, node, node_central.id) and node != node_central.id:
                orphaned_node_ids.append(node)
                #print('Orphaned node added with name', node.name)
        print('no of orphaned nodes added: ',len(orphaned_node_ids))
        return orphaned_node_ids

    """def complete_edges(self):
        "Method checks each node in the current dataset and compare whether all exchanges between the nodes present
        in the dataset are included as edges, appends the missing edges
        Args: current self._data
        Return: none, appends self._data.edges in-situ"
        print('complete_edges started')
        for node in self._data.nodes:
            c = 0
            key = (node.db, node.id)
            activity = bw.get_activity(key)
            upstream = activity.technosphere()
            downstream  = activity.upstream()
            #checks upstream exchanges
            for exchange in upstream:
                edge = Edge(
                    exchange.input.key[1],
                    exchange.output.key[1],
                    exchange.input.get("reference product"))
                if len(list(filter(lambda n: n.id == edge.source_id or n.id == edge.target_id, self._data.nodes))) == 2:
                    try:
                        self.add_edge(edge)
                        c += 1
                        print('missing upstream edge added')
                    except Exception as e:
                        ErrorHandler.trace_error(e)
                        raise
            #checks downstream exchanges
            for row, exchange in enumerate(downstream):
                edge = Edge(
                    exchange.input.key[1],
                    exchange.output.key[1],
                    exchange.output.get("reference product"))
                if len(list(filter(lambda n: n.id == edge.source_id or n.id == edge.target_id, self._data.nodes))) == 2:
                    try:
                        self.add_edge(edge)
                    except Exception as e:
                        ErrorHandler.trace_error(e)
                        raise """

    def complete_edges(self, key):
        """Method checks node for whether all exchanges between the nodes present
        in the dataset are included as edges, appends the missing edges
        Args: current self._data
        Return: none, appends self._data.edges in -situ"""
        print('complete_edges started')

        activity = bw.get_activity(key)
        upstream = activity.technosphere()
        downstream = activity.upstream()
        # checks upstream exchanges
        for exchange in upstream:
            edge = Edge(
                exchange.input.key[1],
                exchange.output.key[1],
                exchange.input.get("reference product"))
            if len(list(filter(lambda n: n.id == edge.source_id or n.id == edge.target_id, self._data.nodes))) == 2:
                try:
                    self.add_edge(edge)
                except Exception as e:
                    ErrorHandler.trace_error(e)
                    raise
        # checks downstream exchanges
        for row, exchange in enumerate(downstream):
            edge = Edge(
                exchange.input.key[1],
                exchange.output.key[1],
                exchange.output.get("reference product"))
            if len(list(filter(lambda n: n.id == edge.source_id or n.id == edge.target_id, self._data.nodes))) == 2:
                try:
                    self.add_edge(edge)
                except Exception as e:
                    ErrorHandler.trace_error(e)
                    raise

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

        # to avoid a change of title and retain information about the original central node it is stored here
        self.central_node = None

    def get_json_graph(self, key: Tuple[str, str]):
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

        self.central_node = node
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

        # adds only downstream nodes to the specified node
        activity_exchanges = activity.upstream()
        for index, exchange in enumerate(activity_exchanges):
            try:
                self.model.add_node(make_node(exchange.output))
                """self.model.add_edge(make_edge(exchange.input, exchange.output))"""
                self.model.complete_edges(exchange.output.key)
            except Exception as e:
                ErrorHandler.trace_error(e)
                print("Failed to create edge/node for exchange: {}.", index)
                raise

        """
        print('checking for missing edges')
        self.model.complete_edges()"""

        json_data = self.model.json()

        #print("JSON-Data:", json_data)
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

    def get_json_reduce_graph(self, key: Tuple[str, str]):
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
