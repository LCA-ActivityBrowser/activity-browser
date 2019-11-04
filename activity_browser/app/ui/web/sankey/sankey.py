# -*- coding: utf-8 -*-
import os
import json
import collections

import numpy as np
import brightway2 as bw
import matplotlib.pyplot as plt
from PySide2 import QtWidgets, QtCore, QtWebEngineWidgets, QtWebChannel
from PySide2.QtCore import Signal, Slot

from .. import wait_html
from .signals import sankeysignals
from .worker_threads import gt_worker_thread


class SankeyWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, cs=None):
        super().__init__(parent)
        self.name = "&Sankey Diagram"
        self.label = QtWidgets.QLabel('hello')
        self.grid_lay = QtWidgets.QGridLayout()
        self.grid_lay.addWidget(QtWidgets.QLabel('Activity: '), 0, 0)
        self.grid_lay.addWidget(QtWidgets.QLabel('Method: '), 1, 0)
        # self.cs = self.window().right_panel.LCA_setup_tab.list_widget.name
        self.cs = cs
        self.func_units = bw.calculation_setups[self.cs]['inv']
        self.func_units = [{bw.get_activity(k): v for k, v in fu.items()}
                           for fu in self.func_units]
        self.methods = bw.calculation_setups[self.cs]['ia']
        self.func_unit_cb = QtWidgets.QComboBox()
        self.func_unit_cb.addItems(
            [list(fu.keys())[0].__repr__() for fu in self.func_units])
        self.method_cb = QtWidgets.QComboBox()
        self.method_cb.addItems([m.__repr__() for m in self.methods])
        self.grid_lay.addWidget(self.func_unit_cb, 0, 1)
        self.grid_lay.addWidget(self.method_cb, 1, 1)
        self.reload_pb = QtWidgets.QPushButton('Reload')
        self.reload_pb.clicked.connect(self.new_sankey)
        self.grid_lay.addWidget(self.reload_pb, 2, 0)
        self.close_pb = QtWidgets.QPushButton('Close')
        self.close_pb.clicked.connect(self.switch_to_main)
        self.grid_lay.setColumnStretch(4, 1)
        self.grid_lay.addWidget(self.close_pb, 0, 5)
        self.color_attr_cb = QtWidgets.QComboBox()
        self.color_attr_cb.addItems(['flow', 'location', 'name'])
        self.grid_lay.addWidget(QtWidgets.QLabel('color by: '), 0, 2)
        self.grid_lay.addWidget(self.color_attr_cb, 0, 3)
        self.grid_lay.addWidget(QtWidgets.QLabel('cutoff: '), 1, 2)
        self.cutoff_sb = QtWidgets.QDoubleSpinBox()
        self.cutoff_sb.setRange(0.0, 1.0)
        self.cutoff_sb.setSingleStep(0.001)
        self.cutoff_sb.setDecimals(4)
        self.cutoff_sb.setValue(0.005)
        self.cutoff_sb.setKeyboardTracking(False)
        self.grid_lay.addWidget(self.cutoff_sb, 1, 3)
        self.hlay = QtWidgets.QHBoxLayout()
        self.hlay.addLayout(self.grid_lay)

        # qt js interaction
        self.bridge = Bridge()
        self.bridge.viewer_waiting.connect(self.send_json)
        self.bridge.link_clicked.connect(self.expand_sankey)

        self.channel = QtWebChannel.QWebChannel()
        self.channel.registerObject('bridge', self.bridge)
        self.view = QtWebEngineWidgets.QWebEngineView()
        self.view.page().setWebChannel(self.channel)
        html = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            'activity-browser-sankey.html')
        self.url = QtCore.QUrl.fromLocalFile(html)
        self.wait_url = QtCore.QUrl.fromLocalFile(wait_html)
        self.view.load(self.wait_url)
        self.vlay = QtWidgets.QVBoxLayout()
        self.vlay.addLayout(self.hlay)
        self.vlay.addWidget(self.view)
        self.setLayout(self.vlay)

        # sankey
        demand_all = dict(collections.ChainMap(*self.func_units))
        self.lca = bw.LCA(demand_all, bw.methods.random())
        self.lca.lci()
        self.lca.lcia()
        self.new_sankey()

        self.func_unit_cb.currentIndexChanged.connect(self.new_sankey)
        self.method_cb.currentIndexChanged.connect(self.new_sankey)
        self.color_attr_cb.currentIndexChanged.connect(self.update_colors)
        self.cutoff_sb.valueChanged.connect(self.new_sankey)

        # connections
        sankeysignals.calculating_gt.connect(self.busy_indicator)
        sankeysignals.initial_sankey_ready.connect(self.draw_sankey)

    def new_sankey(self):
        # print("Entering new_sankey")
        sankeysignals.calculating_gt.emit()
        demand = self.func_units[self.func_unit_cb.currentIndex()]
        method = self.methods[self.method_cb.currentIndex()]
        color_attr = self.color_attr_cb.currentText()
        cutoff = self.cutoff_sb.value()
        # print("calling SankeyGraphTraversal")
        self.sankey = SankeyGraphTraversal(demand, method, cutoff, color_attr)
        # print("finished SankeyGraphTraversal")

    def update_colors(self):
        self.sankey.color_attr = self.color_attr_cb.currentText()
        self.sankey.colors()
        self.sankey.to_json()
        self.bridge.lca_calc_finished.emit(self.sankey.json_data)

    def draw_sankey(self):
        # print("drawing sankey")
        self.view.load(self.url)

    def busy_indicator(self):
        self.view.load(self.wait_url)

    def expand_sankey(self, target_key):
        # print("expanding sankey")
        self.sankey.expand(target_key)
        self.bridge.lca_calc_finished.emit(self.sankey.json_data)

    def send_json(self):
        # print("sending json")
        self.bridge.sankey_ready.emit(self.sankey.json_data)

    def switch_to_main(self):
        window = self.window()
        window.stacked.setCurrentWidget(window.main_widget)


class Bridge(QtCore.QObject):
    link_clicked = Signal(int)
    lca_calc_finished = Signal(str)
    viewer_waiting = Signal()
    sankey_ready = Signal(str)

    @Slot(str)
    def link_selected(self, link):
        target_key = link.split('-')[-2]
        if target_key.startswith('__'):
            target_key = target_key.split('_')[-2]
        self.link_clicked.emit(int(target_key))

    @Slot()
    def viewer_ready(self):
        # print("Viewer ready!")
        self.viewer_waiting.emit()


class SankeyGraphTraversal:
    def __init__(self, demand, method, cutoff=0.005, color_attr='flow'):
        demand = {k: float(v) for k, v in demand.items()}
        gt_worker_thread.update_params(demand, method, cutoff, max_calc=500)
        self.color_attr = color_attr
        sankeysignals.gt_ready.connect(self.init_graph)
        gt_worker_thread.start()

    def init_graph(self, gt):
        self.nodes = []
        self.reverse_activity_dict = {v: k for k, v in
                                      gt['lca'].activity_dict.items()}
        self.edges = gt['edges']
        self.root_score = gt['nodes'][-1]['cum']
        self.expanded_nodes = set()
        self.expand(-1)
        if len(self.links) == 1:
            self.expand(self.links[0]['target'])
        sankeysignals.initial_sankey_ready.emit()

    def expand(self, ind):
        if ind in self.expanded_nodes:
            self.expanded_nodes.remove(ind)
            self.remove_dangling_nodes()
        else:
            self.expanded_nodes.add(ind)
        displayed_edges = [e for e in self.edges if
                           e['to'] in self.expanded_nodes]
        self.links = [{'source': e['to'],
                       'target': e['from'],
                       'value': e['impact'],
                       'tooltip': self.tooltip(e)} for e in displayed_edges]
        self.nodes_set = {li['source'] for li in self.links}.union(
            {li['target'] for li in self.links})
        self.nodes = [{'id': n, 'style': 'process'} for n in self.nodes_set]
        self.colors()
        self.to_json()

    def to_json(self):
        sankey_dict = {'links': self.links, 'nodes': self.nodes}
        self.json_data = json.dumps(sankey_dict)

    def remove_dangling_nodes(self):
        while True:
            displayed_edges = [e for e in self.edges if
                               e['to'] in self.expanded_nodes]
            to = {e['to'] for e in displayed_edges}
            from_ = {e['from'] for e in displayed_edges}
            dangling = to.difference(from_)
            dangling.remove(-1)
            if not dangling:
                break
            self.expanded_nodes = self.expanded_nodes.difference(dangling)

    def tooltip(self, edge):
        producer = self.get_bw_activity_by_index(edge['from'])
        consumer = self.get_bw_activity_by_index(edge['to'])
        impact = edge['impact']
        tooltip_text = \
            '<b>{}</b> Consuming activity: {} | {}<br>'.format(
                edge['to'], consumer['name'], consumer.get('location', '')) +\
            '<b>{}</b> Producing activity: {} | {}<br>'.format(
                edge['from'], producer['name'], producer.get('location', '')) +\
            'Flow: {} {} of {}<br>'.format(
                edge['amount'], producer.get('unit', ''),
                producer.get('reference product', producer.get('name', ''))) +\
            'Score: <b>{}</b><br>'.format(str(impact)) +\
            'Contribution: <b>{}%</b>'.format(np.round(impact/self.root_score*100, 3))
        return tooltip_text

    def get_bw_activity_by_index(self, ind):
        if ind == -1:
            return {'name': 'Functional Unit', 'location': ''}
        key = self.reverse_activity_dict[ind]
        return bw.get_activity(key)

    def colors(self):
        options = sorted(
            {self.get_bw_activity_by_index(n).get(
                self.color_attr,
                self.get_bw_activity_by_index(n).get('name')
            ) for n in self.nodes_set.difference({-1})
            }
        )
        color_dict = {o: self.viridis_r_hex(v) for o, v in
                      zip(options, np.linspace(0, 1, len(options)))}
        for link in self.links:
            link['color'] = color_dict[
                self.get_bw_activity_by_index(link['target']).get(
                    self.color_attr,
                    self.get_bw_activity_by_index(link['target']).get('name', '')
                )
            ]

    @staticmethod
    def viridis_r_hex(v):
        return "#{0:02x}{1:02x}{2:02x}".format(
            *plt.cm.viridis_r(v, bytes=True)[:-1])
