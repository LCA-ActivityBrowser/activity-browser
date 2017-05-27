# -*- coding: utf-8 -*-
import os
import json
import collections
from PyQt5 import QtWidgets, QtCore, QtWebEngineWidgets, QtWebChannel
import numpy as np
import brightway2 as bw
import matplotlib.pyplot as plt

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
        self.url = QtCore.QUrl('file://' +  os.path.join(
            os.path.abspath(os.path.dirname(__file__)), 'activity-browser-sankey.html'))

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
                
    def new_sankey(self):
        demand = self.func_units[self.func_unit_cb.currentIndex()]
        method = self.methods[self.method_cb.currentIndex()]
        color_attr = self.color_attr_cb.currentText()
        cutoff = self.cutoff_sb.value()
        self.sankey = SankeyBuilder(self.lca, demand, method, cutoff, color_attr)
        self.view.load(self.url)

    def expand_sankey(self, target_key):
        target = bw.get_activity(target_key)
        self.sankey.expand(target)
        self.bridge.lca_calc_finished.emit(self.sankey.json_data)
        

    def send_json(self):
        self.bridge.sankey_ready.emit(self.sankey.json_data)


class Bridge(QtCore.QObject):
    link_clicked = QtCore.pyqtSignal(tuple)
    lca_calc_finished = QtCore.pyqtSignal(str)
    viewer_waiting = QtCore.pyqtSignal()
    sankey_ready = QtCore.pyqtSignal(str)

    @QtCore.pyqtSlot(str)
    def link_selected(self, link):
        target_key = tuple(link.split('-')[1].split(','))
        self.link_clicked.emit(target_key)
        
    @QtCore.pyqtSlot()
    def viewer_ready(self):
        self.viewer_waiting.emit()
       

class SankeyBuilder:
    def __init__(self, lca, demand, method, cutoff=0.005, color_attr='flow'):
        self.lca = lca
        self.lca.switch_method(method)
        self.lca.redo_lcia(demand)
        self.root_score = self.lca.score
        self.cutoff = cutoff
        self.color_attr = color_attr

        assert len(list(demand.keys()))==1, 'demand with several func_units not possible'
        act = list(demand.keys())[0]

        self.nodes = [{'id':act.key, 'title':act.get('name')}]
        self.links = []
        self.amount_dict = collections.defaultdict(int)
        self.amount_dict[act.key] += float(list(demand.values())[0])

        self.expand(act)

    def expand(self, act):
        for e in act.technosphere():
            multiplier = self.amount_dict[act.key]
            self.lca.redo_lcia(demand={e.input:e.amount*multiplier})
            if self.lca.score/self.root_score > self.cutoff:
                self.nodes.append({'id':e.input.key,
                                    'title':e.input.get('name')})
                self.links.append({'source':act.key,
                                   'target':e.input.key,
                                   'value':self.lca.score,
                                   'color':'grey'})
                self.amount_dict[e.input.key] += e.amount* multiplier
                
        self.colors()
        sankey_dict = {'links':self.links, 'nodes':self.nodes}
        self.json_data = json.dumps(sankey_dict)
        
        
    def colors(self):
        values = sorted({bw.get_activity(k['id']).get(self.color_attr) for k in self.nodes})
        color_dict = {k:viridis_r_hex(v) for k,v in zip(values, np.linspace(0,1,len(values)))}
        for link in self.links:
            link['color'] = color_dict[bw.get_activity(link['target']).get(self.color_attr)]


def viridis_r_hex(v):
    return "#{0:02x}{1:02x}{2:02x}".format(*plt.cm.viridis_r(v, bytes=True)[:-1])
        






    

        

