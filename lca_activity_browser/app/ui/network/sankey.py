# -*- coding: utf-8 -*-
import os
import json
import collections
from concurrent.futures import ThreadPoolExecutor
from PyQt5 import QtWidgets, QtCore, QtWebEngineWidgets, QtWebChannel
import numpy as np
import brightway2 as bw
import matplotlib.pyplot as plt
from .signals import sankeysignals

class SankeyWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.sankeywidget = SankeyWidget(self)
        self.setCentralWidget(self.sankeywidget)
        self.show()
        screen = QtWidgets.QDesktopWidget().screenGeometry()
        self.setGeometry(10, 10, screen.width() -20, screen.height() -20)
        self.setWindowTitle('Sankey Diagram Contribution Analysis')


class SankeyWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)   
        self.label = QtWidgets.QLabel('hello')
        self.grid_lay = QtWidgets.QGridLayout()
        self.grid_lay.addWidget(QtWidgets.QLabel('Activity: '), 0, 0)
        self.grid_lay.addWidget(QtWidgets.QLabel('Method: '), 1, 0)
        self.cs = self.parent().parent().list_widget.name
        self.func_units = bw.calculation_setups[self.cs]['inv']
        self.func_units = [{bw.get_activity(k):v for k,v in fu.items()} for fu in self.func_units]
        self.methods = bw.calculation_setups[self.cs]['ia']
        self.func_unit_cb = QtWidgets.QComboBox()
        self.func_unit_cb.addItems(
            [list(fu.keys())[0].__repr__() for fu in self.func_units])
        self.method_cb = QtWidgets.QComboBox()
        self.method_cb.addItems([m.__repr__() for m in self.methods])
        self.grid_lay.addWidget(self.func_unit_cb, 0,1)
        self.grid_lay.addWidget(self.method_cb, 1,1)
        self.reload_pb = QtWidgets.QPushButton('Reload')
        self.reload_pb.clicked.connect(self.new_sankey)
        self.grid_lay.addWidget(self.reload_pb, 2, 0)
        self.color_attr_cb = QtWidgets.QComboBox()
        self.color_attr_cb.addItems(['flow', 'location', 'name'])
        self.grid_lay.addWidget(QtWidgets.QLabel('color by: '), 0,2)
        self.grid_lay.addWidget(self.color_attr_cb, 0, 3)
        self.grid_lay.addWidget(QtWidgets.QLabel('cutoff: '),1,2)
        self.cutoff_sb = QtWidgets.QDoubleSpinBox()
        self.cutoff_sb.setRange(0.0, 1.0)
        self.cutoff_sb.setSingleStep(0.001)
        self.cutoff_sb.setDecimals(4)
        self.cutoff_sb.setValue(0.005)
        self.cutoff_sb.setKeyboardTracking(False)
        self.grid_lay.addWidget(self.cutoff_sb, 1, 3)
        self.hlay = QtWidgets.QHBoxLayout()
        self.hlay.addLayout(self.grid_lay)
        self.hlay.addStretch(1)
        
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
        self.color_attr_cb.currentIndexChanged.connect(self.new_sankey)
        self.cutoff_sb.valueChanged.connect(self.new_sankey)
        
        # connections
        sankeysignals.calculating_gt.connect(self.busy_indicator)
        sankeysignals.initial_sankey_ready.connect(self.draw_sankey)
                
    def new_sankey(self):
        sankeysignals.calculating_gt.emit()
        demand = self.func_units[self.func_unit_cb.currentIndex()]
        method = self.methods[self.method_cb.currentIndex()]
        color_attr = self.color_attr_cb.currentText()
        cutoff = self.cutoff_sb.value()
        self.sankey = SankeyGraphTraversal(demand, method, cutoff, color_attr)
        #self.view.load(self.url)

    def draw_sankey(self):
        self.view.load(self.url)

    def busy_indicator(self):
        """to be replaced with d3 busy animation or similar"""
        self.view.setHtml('busy')

    def expand_sankey(self, target_key):
        self.sankey.expand(target_key)
        self.bridge.lca_calc_finished.emit(self.sankey.json_data)

    def send_json(self):
        self.bridge.sankey_ready.emit(self.sankey.json_data)


class Bridge(QtCore.QObject):
    link_clicked = QtCore.pyqtSignal(int)
    lca_calc_finished = QtCore.pyqtSignal(str)
    viewer_waiting = QtCore.pyqtSignal()
    sankey_ready = QtCore.pyqtSignal(str)

    @QtCore.pyqtSlot(str)
    def link_selected(self, link):
        target_key = int(link.split('-')[-2])
        self.link_clicked.emit(target_key)
        
    @QtCore.pyqtSlot()
    def viewer_ready(self):
        self.viewer_waiting.emit()

       
def calculate_graph_traversal(demand, method, cutoff=0.005, max_calc=500):
    return bw.GraphTraversal().calculate(demand, method, cutoff, max_calc)

       
class GraphTraversalThread(QtCore.QThread):
    def __init__(self, demand, method, cutoff, max_calc):
        super().__init__()
        self.demand = demand
        self.method = method
        self.cutoff = cutoff
        self.max_calc = max_calc
        
    def __del__(self):
        """https://joplaete.wordpress.com/2010/07/21/threading-with-pyqt4/"""
        self.wait()
        
    def run(self):
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(calculate_graph_traversal, self.demand,
                                 self.method, self.cutoff, self.max_calc)
            future.add_done_callback(self.send_result)
            
    def send_result(self, future):
        res = future.result()
        sankeysignals.gt_ready.emit(res)
    

class SankeyGraphTraversal:
    def __init__(self, demand, method, cutoff=0.005, color_attr='flow'):
        demand = {k:float(v) for k,v in demand.items()}
        #self.gt = bw.GraphTraversal().calculate(demand, method, cutoff, max_calc=500)
        self.graph_thread = GraphTraversalThread(demand, method, cutoff, max_calc=500)
        self.color_attr = color_attr
        sankeysignals.gt_ready.connect(self.init_graph)
        self.graph_thread.start()
        
    def init_graph(self, gt):
        self.nodes = []
        self.reverse_activity_dict = {v:k for k,v in gt['lca'].activity_dict.items()}
        self.edges = gt['edges']
        self.root_score = gt['nodes'][-1]['cum']
        self.expanded_nodes = set()
        self.expand(-1)
        if len(self.links)==1:
            self.expand(self.links[0]['target'])
        sankeysignals.initial_sankey_ready.emit()


    def expand(self, ind):
        if ind in self.expanded_nodes:
            self.expanded_nodes.remove(ind)
            self.remove_dangling_nodes()
        else:
            self.expanded_nodes.add(ind)
        displayed_edges = [e for e in self.edges if e['to'] in self.expanded_nodes]
        self.links = [{'source': e['to'], 
                       'target': e['from'], 
                       'value': e['impact'],
                       'tooltip': self.tooltip(e)} for e in displayed_edges]
        self.nodes_set = {li['source'] for li in self.links}.union(
            {li['target'] for li in self.links})
        self.nodes = [{'id':n, 'style': 'process'} for n in self.nodes_set]
        self.colors()
        sankey_dict = {'links':self.links, 'nodes':self.nodes}
        self.json_data = json.dumps(sankey_dict)

    def remove_dangling_nodes(self):
        while True:
            displayed_edges = [e for e in self.edges if e['to'] in self.expanded_nodes]
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
                edge['to'], consumer['name'], consumer['location'])+\
            '<b>{}</b> Producing activity: {} | {}<br>'.format(
                edge['from'], producer['name'], producer['location'])+\
            'Flow: {} {} of {}<br>'.format(
                edge['amount'], producer.get('unit',''), producer.get('reference product',''))+\
            'Score: <b>{}</b><br>'.format(str(impact))+\
            'Contribution: <b>{}%</b>'.format(np.round(impact/self.root_score*100,3))
        return tooltip_text
            
    def get_bw_activity_by_index(self, ind):
        if ind == -1:
            return {'name':'Functional Unit', 'location':''}
        key = self.reverse_activity_dict[ind]
        return bw.get_activity(key)
        
    def colors(self):
        options = sorted(
            {self.get_bw_activity_by_index(n).get(self.color_attr) for 
             n in self.nodes_set.difference({-1})})
        color_dict = {o:self.viridis_r_hex(v) for o,v in zip(options, np.linspace(0,1,len(options)))}
        for link in self.links:
            link['color'] = color_dict[self.get_bw_activity_by_index(link['target']).get(self.color_attr)]

    @staticmethod
    def viridis_r_hex(v):
        return "#{0:02x}{1:02x}{2:02x}".format(*plt.cm.viridis_r(v, bytes=True)[:-1])
        

