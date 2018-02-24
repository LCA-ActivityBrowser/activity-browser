# -*- coding: utf-8 -*-
import os
import json
import collections

import brightway2 as bw
from PyQt5 import QtWidgets, QtCore, QtWebEngineWidgets, QtWebChannel

from .signals import graphsignals
from ....signals import signals


class GraphNavigatorWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.connect_signals()

        # button refresh
        self.button_refresh = QtWidgets.QPushButton('Refresh')
        self.button_refresh.clicked.connect(self.draw_graph)

        # button new graph
        self.button_new_graph = QtWidgets.QPushButton('New Graph')
        self.button_new_graph.clicked.connect(self.new_graph)

        # qt js interaction
        self.bridge = Bridge()
        self.bridge.viewer_waiting.connect(self.send_json)
        self.bridge.link_clicked.connect(self.expand_sankey)

        self.channel = QtWebChannel.QWebChannel()
        self.channel.registerObject('bridge', self.bridge)
        self.view = QtWebEngineWidgets.QWebEngineView()
        self.view.page().setWebChannel(self.channel)
        html = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            'graphviz_navigator1.html')
        self.url = QtCore.QUrl.fromLocalFile(html)

        # Layout
        self.vlay = QtWidgets.QVBoxLayout()
        self.vlay.addWidget(self.button_refresh)
        self.vlay.addWidget(self.button_new_graph)
        self.vlay.addWidget(self.view)
        self.setLayout(self.vlay)

        # graph
        self.digraph = self.get_random_graph()
        self.draw_graph()

    def connect_signals(self):
        signals.add_activity_to_history.connect(self.update_graph)
        signals.add_activity_to_history.connect(self.get_upstream_edges_nodes)
        graphsignals.graph_ready.connect(self.draw_graph)


    def get_upstream_edges_nodes(self, key):
        self.activity = bw.get_activity(key)

        edges = []
        nodes = []
        # all inputs
        for row, exc in enumerate(self.activity.technosphere()):
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
            })
        # and the receiving node
        nodes.append({
            "id": exc.output.key[1],
            "product": exc.output.get("reference product"),
            "name": exc.output.get("name"),
            "location": exc.output.get("location"),
        })
        json_data = {
            "nodes": nodes,
            "edges": edges,
        }

        print("JSON-Data:", json_data)

        filepath = os.path.join(os.path.dirname(__file__), "data.json")
        with open(filepath, 'w') as outfile:
            json.dump(json_data, outfile)

        return json_data


    def get_random_graph(self):
        graph = "digraph wood { \
        				a -> b;\
        				b -> c;\
        				c -> a;\
        				b -> d;\
        				e -> a;\
        				f -> a;\
        				c -> f;\
        				d -> e;\
        				d -> a;\
        				e -> b;\
        				d -> c;\
        				}"
        return graph

    def new_graph(self):
        print("Sending new Graph Data")
        graph_data = self.get_random_graph()
        self.bridge.graph_ready.emit(graph_data)
        print("Graph Data: ", graph_data)

    def get_activity_data_str(self, obj):
        obj_str = "_".join([
            obj.get("reference product"),
            # obj.get("name"),
            # obj.get("location")
        ])
        return obj_str

    def get_graph_data(self, key):
        self.activity = bw.get_activity(key)
        self.upstream = False

        from_to_list = []
        for row, exc in enumerate(self.activity.technosphere()):
            from_act = self.get_activity_data_str(exc.input)
            to_act = self.get_activity_data_str(exc.output)
            from_to_list.append((from_act, to_act))
        return from_to_list

    def format_as_dot(self, from_to_list):
        graph = 'digraph inventories {\n'
        graph += """node[rx = 5 ry = 5 labelStyle = "font: 300 14px 'Helvetica Neue', Helvetica"]
        edge[labelStyle = "font: 300 14px 'Helvetica Neue', Helvetica"]"""
        for from_act, to_act in from_to_list:
            graph +='\n"'+from_act+'"'+' -> '+'"'+to_act+'"'+'; '
        graph += '}'
        return graph

    def update_graph(self, key):
        print("Got key: ", key)
        from_to_list = self.get_graph_data(key)
        print(from_to_list)
        dot_text = self.format_as_dot(from_to_list)
        print(dot_text)
        self.bridge.graph_ready.emit(dot_text)

    def draw_graph(self):
        self.view.load(self.url)

    def expand_sankey(self, target_key):
        self.sankey.expand(target_key)
        self.bridge.lca_calc_finished.emit(self.sankey.json_data)

    def send_json(self):
        self.bridge.graph_ready.emit(self.get_random_graph())


class Bridge(QtCore.QObject):
    link_clicked = QtCore.pyqtSignal(int)
    lca_calc_finished = QtCore.pyqtSignal(str)
    viewer_waiting = QtCore.pyqtSignal()
    graph_ready = QtCore.pyqtSignal(str)

    @QtCore.pyqtSlot(str)
    def link_selected(self, link):
        print("Clicked on: ", link)
        target_key = int(link.split('-')[-2])
        self.link_clicked.emit(target_key)

    @QtCore.pyqtSlot()
    def viewer_ready(self):
        self.viewer_waiting.emit()


