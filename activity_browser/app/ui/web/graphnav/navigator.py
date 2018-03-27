# -*- coding: utf-8 -*-
import os
import json

import brightway2 as bw
from PyQt5 import QtWidgets, QtCore, QtWebEngineWidgets, QtWebChannel

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
        signals.add_activity_to_history.connect(self.update_graph)
        graphsignals.update_graph.connect(self.update_graph)
        graphsignals.graph_ready.connect(self.draw_graph)

    def update_graph(self, key):
        print("Updating Graph for key: ", key)
        try:
            json_data = self.graph.get_json_graph(key)
            self.bridge.graph_ready.emit(json_data)
        except:
            print("No activity with this key:", key)

    def update_graph_random(self):
        random_activity = bw.Database("ecoinvent 3.4 cutoff").random()
        print("Random key:", random_activity, type(random_activity))
        self.update_graph(random_activity)

    def draw_graph(self):
        self.view.load(self.url)


class Bridge(QtCore.QObject):
    graph_ready = QtCore.pyqtSignal(str)

    @QtCore.pyqtSlot(str)
    def node_clicked(self, js_string):
        print("Clicked on: ", js_string)
        db_id = js_string.split(";")
        key = tuple([db_id[0], db_id[1]])
        graphsignals.update_graph.emit(key)


class Graph():
    def __init__(self):
        self.json_data = {}

    def get_json_graph(self, key):
        self.activity = bw.get_activity(key)
        print("Head:", self.activity)
        edges = []
        nodes = []
        # all inputs
        for exc in self.activity.technosphere():
            edges.append({
                "source": exc.input.key[1],
                "target": exc.output.key[1],
                "label": exc.input.get("reference product")
            })
            nodes.append({
                "id": exc.input.key[1],
                "product": exc.input.get("reference product"),
                "name": exc.input.get("name"),
                "location": exc.input.get("location"),
                "database": exc.input.key[0],
            })
        # all downstream consumers
        for row, exc in enumerate(self.activity.upstream()):
            edges.append({
                "source": exc.input.key[1],
                "target": exc.output.key[1],
                "label": exc.output.get("reference product")
            })
            nodes.append({
                "id": exc.output.key[1],
                "product": exc.output.get("reference product"),
                "name": exc.output.get("name"),
                "location": exc.output.get("location"),
                "database": exc.output.key[0],
            })
        # and the receiving node
        nodes.append({
            "id": self.activity.key[1],
            "product": self.activity.get("reference product"),
            "name": self.activity.get("name"),
            "location": self.activity.get("location"),
            "database": self.activity.key[0],
        })
        json_data = {
            "nodes": nodes,
            "edges": edges,
            "title": self.activity.get("reference product"),
        }

        print("JSON-Data:", json.dumps(json_data))
        return json.dumps(json_data)

    def save_json_to_file(self, filename="data.json"):
        if self.json_data:
            filepath = os.path.join(os.path.dirname(__file__), filename)
            with open(filepath, 'w') as outfile:
                json.dump(self.json_data, outfile)

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

