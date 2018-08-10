# -*- coding: utf-8 -*-
import os
import json
from copy import deepcopy
import time

import brightway2 as bw
from PyQt5 import QtWidgets, QtCore, QtWebEngineWidgets, QtWebChannel

from ....bwutils.commontasks import identify_activity_type
from .signals import graphsignals
from ....signals import signals

# TODO:
# make this a subtab in the LCA Results Tab
# solve initial delay (Spinner) issue: Sankey is still empty if one selects the Sankey Tab very fast after CS calculation
# mark functional unit in sankey
# when avoided impacts, then the scaling between 0-1 of relative impacts does not work properly
# disable current right click menu
# ability to navigate to activities
# ability to calculate LCA for selected activities
# ability to expand (or reduce) the graph
# save graph as image
# random_graph should not work for biosphere

# in Javascript:
# - zoom behaviour


class SankeyNavigatorWidget(QtWidgets.QWidget):
    HELP_TEXT = """
    LCA Sankey:
    
    Red flows: Impacts
    Green flows: Avoided impacts
    
    """
    def __init__(self, cs_name, parent=None):
        super().__init__(parent)

        self.graph = Graph()

        self.selected_db = None

        # Layout Functional Units and LCIA Methods
        self.grid_lay = QtWidgets.QGridLayout()
        self.grid_lay.addWidget(QtWidgets.QLabel('Functional unit: '), 0, 0)
        self.grid_lay.addWidget(QtWidgets.QLabel('Impact indicator: '), 1, 0)
        self.cs = cs_name  # TODO: just a workaround; needs to be adapted to always link to the FUs in the active LCA results tab
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
        # self.reload_pb = QtWidgets.QPushButton('Reload')
        # self.reload_pb.clicked.connect(self.new_sankey)
        # self.grid_lay.addWidget(self.reload_pb, 2, 0)
        # self.close_pb = QtWidgets.QPushButton('Close')
        # self.close_pb.clicked.connect(self.switch_to_main)

        # self.grid_lay.addWidget(self.close_pb, 0, 5)
        # self.color_attr_cb = QtWidgets.QComboBox()
        # self.color_attr_cb.addItems(['flow', 'location', 'name'])
        # self.grid_lay.addWidget(QtWidgets.QLabel('color by: '), 0, 2)
        # self.grid_lay.addWidget(self.color_attr_cb, 0, 3)

        # cut-off
        self.grid_lay.addWidget(QtWidgets.QLabel('cutoff: '), 1, 2)
        self.cutoff_sb = QtWidgets.QDoubleSpinBox()
        self.cutoff_sb.setRange(0.0, 1.0)
        self.cutoff_sb.setSingleStep(0.001)
        self.cutoff_sb.setDecimals(4)
        self.cutoff_sb.setValue(0.05)
        self.cutoff_sb.setKeyboardTracking(False)
        self.grid_lay.addWidget(self.cutoff_sb, 1, 3)

        # max-iterations of graph traversal
        self.grid_lay.addWidget(QtWidgets.QLabel('Calculation depth: '), 1, 4)
        self.max_calc_sb = QtWidgets.QDoubleSpinBox()
        self.max_calc_sb.setRange(1, 2000)
        self.max_calc_sb.setSingleStep(50)
        self.max_calc_sb.setDecimals(0)
        self.max_calc_sb.setValue(500)
        self.max_calc_sb.setKeyboardTracking(False)
        self.grid_lay.addWidget(self.max_calc_sb, 1, 5)

        self.grid_lay.setColumnStretch(6, 1)
        self.hlay = QtWidgets.QHBoxLayout()
        self.hlay.addLayout(self.grid_lay)

        # Help label
        self.label_help = QtWidgets.QLabel(self.HELP_TEXT)
        self.label_help.setVisible(False)

        # button toggle_help
        self.help = False
        self.button_toggle_help = QtWidgets.QPushButton("Help")
        self.button_toggle_help.clicked.connect(self.toggle_help)

        # button calculate
        self.button_calculate = QtWidgets.QPushButton('Calculate')
        self.button_calculate.clicked.connect(self.new_sankey)

        # button back
        self.button_back = QtWidgets.QPushButton('<<')
        self.button_back.clicked.connect(self.go_back)

        # button forward
        self.button_forward = QtWidgets.QPushButton('>>')
        self.button_forward.clicked.connect(self.go_forward)

        # button refresh
        self.button_refresh = QtWidgets.QPushButton('Refresh HTML')
        self.button_refresh.clicked.connect(self.draw_graph)

        # button random
        self.button_random_activity = QtWidgets.QPushButton('Random Activity')
        self.button_random_activity.clicked.connect(self.random_sankey)

        # checkbox cumulative impact
        # self.checkbox_cumulative_impact = QtWidgets.QCheckBox("Cumulative impact")
        # self.checkbox_cumulative_impact.setChecked(True)

        # qt js interaction
        self.bridge = Bridge()
        self.channel = QtWebChannel.QWebChannel()
        self.channel.registerObject('bridge', self.bridge)
        self.view = QtWebEngineWidgets.QWebEngineView()
        self.view.page().setWebChannel(self.channel)
        html = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            'sankey_navigator.html')
        self.url = QtCore.QUrl.fromLocalFile(html)

        # Controls Layout
        self.hl_controls = QtWidgets.QHBoxLayout()
        self.hl_controls.addWidget(self.button_back)
        self.hl_controls.addWidget(self.button_forward)
        self.hl_controls.addWidget(self.button_calculate)
        self.hl_controls.addWidget(self.button_refresh)
        self.hl_controls.addWidget(self.button_random_activity)
        self.hl_controls.addWidget(self.button_toggle_help)
        self.hl_controls.addStretch(1)

        # Checkboxes Layout
        self.hl_checkboxes = QtWidgets.QHBoxLayout()
        # self.hl_checkboxes.addWidget(self.checkbox_cumulative_impact)
        self.hl_checkboxes.addStretch(1)

        # Layout
        self.vlay = QtWidgets.QVBoxLayout()
        self.vlay.addLayout(self.hl_controls)
        self.vlay.addLayout(self.hlay)
        self.vlay.addLayout(self.hl_checkboxes)
        self.vlay.addWidget(self.label_help)
        self.vlay.addWidget(self.view)
        self.setLayout(self.vlay)

        # graph
        self.connect_signals()
        self.draw_graph()
        # self.new_sankey()  # does not show it...

    def connect_signals(self):
        signals.database_selected.connect(self.set_database)
        self.func_unit_cb.currentIndexChanged.connect(self.new_sankey)
        self.method_cb.currentIndexChanged.connect(self.new_sankey)
        # self.cutoff_sb.valueChanged.connect(self.new_sankey)
        # self.max_calc_sb.valueChanged.connect(self.new_sankey)

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

    def new_sankey(self):
        print("New Sankey for CS: ", self.cs)
        demand = self.func_units[self.func_unit_cb.currentIndex()]
        method = self.methods[self.method_cb.currentIndex()]
        cutoff = self.cutoff_sb.value()
        max_calc = self.max_calc_sb.value()
        self.update_sankey(demand, method, cut_off=cutoff, max_calc=max_calc)

    def update_sankey(self, demand, method, cut_off=0.05, max_calc=100):
        """Calculate LCA, do graph traversal, get JSON graph data for this, and send to javascript."""
        print("Demand / Method:", demand, method)
        start = time.time()
        try:
            data = bw.GraphTraversal().calculate(demand, method, cutoff=cut_off, max_calc=max_calc)
        except ValueError as e:
            QtWidgets.QMessageBox.information(None, "Not possible.", str(e))
        print("Completed graph traversal ({:.2g} seconds, {} iterations)".format(time.time() - start, data["counter"]))

        self.graph.new_graph(data)
        print("emitting graph ready signal")
        self.bridge.graph_ready.emit(self.graph.json_data)

    def set_database(self, name):
        """Saves the currently selected database for graphing a random activity"""
        self.selected_db = name

    def random_sankey(self):
        """ Show graph for a random activity in the currently loaded database."""
        if self.selected_db:
            method = bw.methods.random()
            act = bw.Database(self.selected_db).random()
            demand = {act: 1.0}
            self.update_sankey(demand, method)
        else:
            QtWidgets.QMessageBox.information(None, "Not possible.", "Please load a database first.")

    def draw_graph(self):
        print("Drawing graph, i.e. loading the view.")
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
        # graphsignals.update_graph.emit(click_dict)


class Graph:
    """
    Python side representation of the graph.
    Functionality for graph navigation (e.g. adding and removing nodes).
    A JSON representation of the graph (edges and nodes) enables its use in javascript/html/css.
    """

    def __init__(self):
        self.json_data = None
        self.stack = []  # stores previous graphs, if any, and enables back/forward buttons
        self.forward_stack = []  # stores graphs that can be returned to after having used the "back" button

    def update(self, delete_unstacked=True):
        self.stack.append((deepcopy(self.json_data)))
        # print("Stacked (Nodes/Edges):", len(self.nodes), len(self.edges))
        if delete_unstacked:
            self.forward_stack = []

    def forward(self):
        """Go forward, if previously gone back."""
        if self.forward_stack:
            self.json_data = self.forward_stack.pop()
            self.update(delete_unstacked=False)
            return True
        else:
            return False

    def back(self):
        """Go back to previous graph, if any."""
        if len(self.stack) > 1:
            self.forward_stack.append(self.stack.pop())  # as the last element is always the current graph
            # print("Forward stack:", self.forward_stack)
            self.json_data = self.stack.pop()
            # print("Un-Stacked (Nodes/Edges):", len(self.nodes), len(self.edges))
            self.update(delete_unstacked=False)
            return True
        else:
            return False

    def new_graph(self, data):
        self.json_data = self.get_JSON_from_graph_traversal_data(data)
        self.update()

    def get_JSON_from_graph_traversal_data(self, data):
        """Transform bw.Graphtraversal() output to JSON data."""

        def get_activity_by_index(ind):
            if ind != -1:
                return bw.get_activity(reverse_activity_dict[ind])
            else:
                return False

        def get_max_impact(nodes):
            return max([abs(n["cum"]) for n in nodes.values()])


        gnodes = data["nodes"]
        gedges = data["edges"]
        lca = data["lca"]
        lca_score = lca.score #abs(lca.score)
        max_impact = get_max_impact(gnodes)
        # print("Max impact:", max_impact)
        LCIA_unit = bw.Method(lca.method).metadata["unit"]
        demand = list(lca.demand.items())[0]
        reverse_activity_dict = {v: k for k, v in lca.activity_dict.items()}

        nodes, edges = [], []

        for node_index, values in gnodes.items():
            act = get_activity_by_index(node_index)
            if not act:
                continue

            nodes.append(
                {
                    # "key": act.key,
                    "db": act.key[0],
                    "id": act.key[1],
                    "product": act.get("reference product") or act.get("name"),
                    "name": act.get("name"),
                    "location": act.get("location"),
                    "amount": values.get("amount"),
                    "LCIA_unit": LCIA_unit,
                    "ind": values.get("ind"),
                    "ind_norm": values.get("ind") / lca_score,
                    "cum": values.get("cum"),
                    "cum_norm": values.get("cum") / lca_score,
                    "class": "demand" if act == demand[0] else identify_activity_type(act),
                }
            )

        for gedge in gedges:
            if gedge["from"] == -1 or gedge["to"] == -1:
                continue

            product = get_activity_by_index(gedge["from"]).get("reference product") or get_activity_by_index(gedge["from"]).get("name")
            from_key = reverse_activity_dict[gedge["from"]]
            to_key = reverse_activity_dict[gedge["to"]]

            edges.append(
                {
                    "source_id": from_key[1],
                    "target_id": to_key[1],
                    "amount": gedge["amount"],
                    "product": product,
                    "impact": gedge["impact"],
                    "ind_norm": gedge["impact"] / lca_score,
                    "unit": bw.Method(lca.method).metadata["unit"],
                    "tooltip": '<b>{}</b> ({:.2g} {})'
                               '<br>{:.3g} {} ({:.2g}%) '.format(
                        product, gedge["amount"], bw.get_activity(from_key).get("unit"),
                        gedge["impact"], LCIA_unit, gedge["impact"] / lca.score * 100,
                    )
                }
            )

        def get_title():
            act, amount = demand[0], demand[1]
            m = bw.Method(lca.method)

            return 'Functional unit: {:.2g} {} {} | {} | {} <br>' \
                   'LCIA method: {} [{}] <br>' \
                   'Total impact: {:.2g} {}'.format(
                amount,
                act.get("unit"),
                act.get("reference product") or act.get("name"),
                act.get("name"),
                act.get("location"),
                m.name,
                m.metadata.get("unit"),
                lca.score, m.metadata.get("unit"),
            )

        json_data = {
            "nodes": nodes,
            "edges": edges,
            "title": get_title(),
            "max_impact": max_impact,
        }
        print("JSON DATA (Nodes/Edges):", len(nodes), len(edges))
        print(json_data)
        return json.dumps(json_data)

    def save_json_to_file(self, filename="sankey_data.json"):
        """ Writes the current model´s JSON representation to the specifies file. """
        if self.json_data:
            filepath = os.path.join(os.path.dirname(__file__), filename)
            with open(filepath, 'w') as outfile:
                json.dump(self.json_data, outfile)
