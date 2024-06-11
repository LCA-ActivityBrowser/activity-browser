# -*- coding: utf-8 -*-
import json
import os
import time
from typing import List

import bw2calc as bc
from PySide2 import QtWidgets
from PySide2.QtCore import Slot
from PySide2.QtWidgets import QComboBox

from activity_browser import log, signals
from activity_browser.mod import bw2data as bd
from activity_browser.mod.bw2data.backends import ActivityDataset

from ...bwutils.commontasks import identify_activity_type
from ...bwutils.superstructure.graph_traversal_with_scenario import \
    GraphTraversalWithScenario
from .base import BaseGraph, BaseNavigatorWidget

try:
    # test whether we're running bw25
    from bw2calc.graph_traversal import \
        AssumedDiagonalGraphTraversal as GraphTraversal
except:
    # fall back on regular bw
    from bw2calc import GraphTraversal


# TODO:
# switch between percent and absolute values
# when avoided impacts, then the scaling between 0-1 of relative impacts does not work properly
# ability to navigate to activities
# ability to calculate LCA for selected activities
# ability to expand (or reduce) the graph
# save graph as image
# random_graph should not work for biosphere

# in Javascript:
# - zoom behaviour


class SankeyNavigatorWidget(BaseNavigatorWidget):
    HELP_TEXT = """
    LCA Sankey:

    Red flows: Impacts
    Green flows: Avoided impacts

    """
    HTML_FILE = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), "../../static/sankey_navigator.html"
    )

    def __init__(self, cs_name, parent=None):
        super().__init__(parent, css_file="sankey_navigator.css")

        self.cache = {}  # we cache the calculated data to improve responsiveness
        self.parent = parent
        self.has_scenarios = self.parent.has_scenarios
        self.cs = cs_name
        self.selected_db = None
        self.has_sankey = False
        self.func_units = []
        self.methods = []
        self.scenarios = []
        self.graph = Graph()

        # Additional Qt objects
        self.scenario_label = QtWidgets.QLabel("Scenario: ")
        self.func_unit_cb = QtWidgets.QComboBox()
        self.method_cb = QtWidgets.QComboBox()
        self.scenario_cb = QtWidgets.QComboBox()
        self.cutoff_sb = QtWidgets.QDoubleSpinBox()
        self.max_calc_sb = QtWidgets.QDoubleSpinBox()
        self.button_calculate = QtWidgets.QPushButton("Calculate")
        self.layout = QtWidgets.QVBoxLayout()

        # graph
        self.draw_graph()
        self.construct_layout()
        self.connect_signals()

    @Slot(name="loadFinishedHandler")
    def load_finished_handler(self) -> None:
        if self.has_sankey:
            self.send_json()

    def connect_signals(self):
        super().connect_signals()
        self.button_calculate.clicked.connect(self.new_sankey)
        signals.database_selected.connect(self.set_database)
        # checkboxes
        self.func_unit_cb.currentIndexChanged.connect(self.new_sankey)
        self.method_cb.currentIndexChanged.connect(self.new_sankey)
        self.scenario_cb.currentIndexChanged.connect(self.new_sankey)

    def construct_layout(self) -> None:
        """Layout of Sankey Navigator"""
        super().construct_layout()
        self.label_help.setVisible(False)

        # Layout Reference Flows and Impact Categories
        grid_lay = QtWidgets.QGridLayout()
        grid_lay.addWidget(QtWidgets.QLabel("Reference flow: "), 0, 0)

        grid_lay.addWidget(self.scenario_label, 1, 0)
        grid_lay.addWidget(QtWidgets.QLabel("Impact indicator: "), 2, 0)

        self.update_calculation_setup()

        grid_lay.addWidget(self.func_unit_cb, 0, 1)
        grid_lay.addWidget(self.scenario_cb, 1, 1)
        grid_lay.addWidget(self.method_cb, 2, 1)

        # cut-off
        grid_lay.addWidget(QtWidgets.QLabel("cutoff: "), 2, 2)
        self.cutoff_sb.setRange(0.0, 1.0)
        self.cutoff_sb.setSingleStep(0.001)
        self.cutoff_sb.setDecimals(4)
        self.cutoff_sb.setValue(0.05)
        self.cutoff_sb.setKeyboardTracking(False)
        grid_lay.addWidget(self.cutoff_sb, 2, 3)

        # max-iterations of graph traversal
        grid_lay.addWidget(QtWidgets.QLabel("Calculation depth: "), 2, 4)
        self.max_calc_sb.setRange(1, 2000)
        self.max_calc_sb.setSingleStep(50)
        self.max_calc_sb.setDecimals(0)
        self.max_calc_sb.setValue(250)
        self.max_calc_sb.setKeyboardTracking(False)
        grid_lay.addWidget(self.max_calc_sb, 2, 5)

        grid_lay.setColumnStretch(6, 1)
        hlay = QtWidgets.QHBoxLayout()
        hlay.addLayout(grid_lay)

        # Controls Layout
        hl_controls = QtWidgets.QHBoxLayout()
        hl_controls.addWidget(self.button_back)
        hl_controls.addWidget(self.button_forward)
        hl_controls.addWidget(self.button_calculate)
        hl_controls.addWidget(self.button_refresh)
        hl_controls.addWidget(self.button_random_activity)
        hl_controls.addWidget(self.button_toggle_help)
        hl_controls.addStretch(1)

        # Layout
        self.layout.addLayout(hl_controls)
        self.layout.addLayout(hlay)
        self.layout.addWidget(self.label_help)
        self.layout.addWidget(self.view)
        self.setLayout(self.layout)

    def get_scenario_labels(self) -> List[str]:
        """Get scenario labels if scenario is used."""
        return self.parent.mlca.scenario_names if self.has_scenarios else []

    def configure_scenario(self):
        """Determine if scenario Qt widgets are visible or not and retrieve
        scenario labels for the selection drop-down box.
        """
        self.scenario_cb.setVisible(self.has_scenarios)
        self.scenario_label.setVisible(self.has_scenarios)
        if self.has_scenarios:
            self.scenarios = self.get_scenario_labels()
            self.update_combobox(self.scenario_cb, self.scenarios)

    @staticmethod
    def update_combobox(box: QComboBox, labels: List[str]) -> None:
        """Update the combobox menu."""
        box.blockSignals(True)
        box.clear()
        box.insertItems(0, labels)
        box.blockSignals(False)

    def update_calculation_setup(self, cs_name=None) -> None:
        """Update Calculation Setup, reference flows and impact categories, and dropdown menus."""
        # block signals
        self.func_unit_cb.blockSignals(True)
        self.method_cb.blockSignals(True)

        self.cs = cs_name or self.cs
        self.func_units = [
            {bd.get_activity(k): v for k, v in fu.items()}
            for fu in bd.calculation_setups[self.cs]["inv"]
        ]
        self.methods = bd.calculation_setups[self.cs]["ia"]
        self.func_unit_cb.clear()
        fu_acts = [list(fu.keys())[0] for fu in self.func_units]
        self.func_unit_cb.addItems(
            [f"{repr(a)} | {a._data.get('database')}" for a in fu_acts]
        )
        self.configure_scenario()
        self.method_cb.clear()
        self.method_cb.addItems([repr(m) for m in self.methods])

        # unblock signals
        self.func_unit_cb.blockSignals(False)
        self.method_cb.blockSignals(False)

    def new_sankey(self) -> None:
        """(re)-generate the sankey diagram."""
        demand_index = self.func_unit_cb.currentIndex()
        method_index = self.method_cb.currentIndex()

        demand = self.func_units[demand_index]
        method = self.methods[method_index]
        scenario_index = None
        scenario_lca = False
        if self.has_scenarios:
            scenario_lca = True
            scenario_index = self.scenario_cb.currentIndex()
        cutoff = self.cutoff_sb.value()
        max_calc = self.max_calc_sb.value()
        self.update_sankey(
            demand,
            method,
            demand_index=demand_index,
            method_index=method_index,
            scenario_index=scenario_index,
            scenario_lca=scenario_lca,
            cut_off=cutoff,
            max_calc=max_calc,
        )

    def update_sankey(
        self,
        demand: dict,
        method: tuple,
        demand_index: int = None,
        method_index: int = None,
        scenario_index: int = None,
        scenario_lca: bool = False,
        cut_off=0.05,
        max_calc=100,
    ) -> None:
        """Calculate LCA, do graph traversal, get JSON graph data for this, and send to javascript."""

        # the cache key consists of demand/method/scenario indices (index of item in the relevant tables),
        # the cutoff, max_calc.
        # together, these are unique.
        cache_key = (demand_index, method_index, scenario_index, cut_off, max_calc)
        if data := self.cache.get(cache_key, False):
            # this Sankey is already cached, generate the Sankey with the cached data
            log.debug(f"CACHED sankey for: {demand}, {method}, key: {cache_key}")
            self.graph.new_graph(data)
            self.has_sankey = bool(self.graph.json_data)
            self.send_json()
            return

        start = time.time()
        log.debug(f"CALCULATE sankey for: {demand}, {method}, key: {cache_key}")
        try:
            if scenario_lca:
                self.parent.mlca.update_lca_calculation_for_sankey(
                    scenario_index, demand, method_index
                )
                data = GraphTraversalWithScenario(self.parent.mlca).calculate(
                    demand, method, cutoff=cut_off, max_calc=max_calc
                )
            else:
                try:
                    data = GraphTraversal().calculate(
                        demand, method, cutoff=cut_off, max_calc=max_calc
                    )
                except:
                    lca = bc.LCA(demand, method)
                    data = GraphTraversal().calculate(
                        lca, cutoff=cut_off, max_calc=max_calc
                    )
                    data["lca"] = lca
            # store the metadata from this calculation
            data["metadata"] = {
                "demand": list(data["lca"].demand.items())[0],
                "score": data["lca"].score,
                "unit": bd.methods[method]["unit"],
                "act_dict": data["lca"].activity_dict.items(),
            }
            # drop LCA object as it's useless from now on
            del data["lca"]

        except (ValueError, ZeroDivisionError) as e:
            QtWidgets.QMessageBox.information(None, "Not possible.", str(e))
        log.debug(
            f"Completed graph traversal ({round(time.time() - start, 2)} seconds, {data['counter']} iterations)"
        )

        # cache the generated Sankey data
        self.cache[cache_key] = data

        # generate the new Sankey
        self.graph.new_graph(data)
        self.has_sankey = bool(self.graph.json_data)
        self.send_json()

    def set_database(self, name):
        """Saves the currently selected database for graphing a random activity"""
        self.selected_db = name

    def random_graph(self) -> None:
        """Show graph for a random activity in the currently loaded database."""
        if self.selected_db:
            method = bd.methods.random()
            act = bd.Database(self.selected_db).random()
            demand = {act: 1.0}
            self.update_sankey(demand, method)
        else:
            QtWidgets.QMessageBox.information(
                None, "Not possible.", "Please load a database first."
            )


class Graph(BaseGraph):
    """
    Python side representation of the graph.
    Functionality for graph navigation (e.g. adding and removing nodes).
    A JSON representation of the graph (edges and nodes) enables its use in javascript/html/css.
    """

    def new_graph(self, data):
        self.json_data = Graph.get_json_data(data)
        self.update()

    @staticmethod
    def get_json_data(data) -> str:
        """Transform bw.Graphtraversal() output to JSON data."""
        meta = data["metadata"]
        lca_score = meta["score"]
        lcia_unit = meta["unit"]
        demand = meta["demand"]
        reverse_activity_dict = {v: k for k, v in meta["act_dict"]}

        build_json_node = Graph.compose_node_builder(lca_score, lcia_unit, demand[0])
        build_json_edge = Graph.compose_edge_builder(
            reverse_activity_dict, lca_score, lcia_unit
        )

        valid_nodes = (
            (bd.get_activity(reverse_activity_dict[idx]), v)
            for idx, v in data["nodes"].items()
            if idx != -1
        )
        valid_edges = (
            edge
            for edge in data["edges"]
            if all(i != -1 for i in (edge["from"], edge["to"]))
        )

        json_data = {
            "nodes": [build_json_node(act, v) for act, v in valid_nodes],
            "edges": [build_json_edge(edge) for edge in valid_edges],
            "title": Graph.build_title(demand, lca_score, lcia_unit),
            "max_impact": max(abs(n["cum"]) for n in data["nodes"].values()),
        }
        return json.dumps(json_data)

    @staticmethod
    def build_title(demand: tuple, lca_score: float, lcia_unit: str) -> str:
        act, amount = demand[0], demand[1]
        if type(act) is tuple or type(act) is int:
            act = bd.get_activity(act)
        format_str = (
            "Reference flow: {:.2g} {} {} | {} | {} <br>" "Total impact: {:.2g} {}"
        )
        return format_str.format(
            amount,
            act.get("unit"),
            act.get("reference product") or act.get("name"),
            act.get("name"),
            act.get("location"),
            lca_score,
            lcia_unit,
        )

    @staticmethod
    def compose_node_builder(lca_score: float, lcia_unit: str, demand: tuple):
        """Build and return a function which processes activities and values
        into valid JSON documents.

        Inspired by https://stackoverflow.com/a/7045809
        """

        def build_json_node(act, values: dict) -> dict:
            return {
                "db": act.key[0],
                "id": act.key[1],
                "product": act.get("reference product") or act.get("name"),
                "name": act.get("name"),
                "location": act.get("location"),
                "amount": values.get("amount"),
                "LCIA_unit": lcia_unit,
                "ind": values.get("ind"),
                "ind_norm": values.get("ind") / lca_score,
                "cum": values.get("cum"),
                "cum_norm": values.get("cum") / lca_score,
                "class": "demand" if act == demand else identify_activity_type(act),
            }

        return build_json_node

    @staticmethod
    def compose_edge_builder(reverse_dict: dict, lca_score: float, lcia_unit: str):
        """Build a function which turns graph edges into valid JSON documents."""

        def build_json_edge(edge: dict) -> dict:
            p = bd.get_activity(reverse_dict[edge["from"]])
            from_key = id_to_key(reverse_dict[edge["from"]])
            to_key = id_to_key(reverse_dict[edge["to"]])
            return {
                "source_id": from_key[1],
                "target_id": to_key[1],
                "amount": edge["amount"],
                "product": p.get("reference product") or p.get("name"),
                "impact": edge["impact"],
                "ind_norm": edge["impact"] / lca_score,
                "unit": lcia_unit,
                "tooltip": "<b>{}</b> ({:.2g} {})"
                "<br>{:.3g} {} ({:.2g}%) ".format(
                    lcia_unit,
                    edge["amount"],
                    p.get("unit"),
                    edge["impact"],
                    lcia_unit,
                    edge["impact"] / lca_score * 100,
                ),
            }

        return build_json_edge


def id_to_key(id):
    if isinstance(id, tuple):
        return id
    return ActivityDataset.get_by_id(id).database, ActivityDataset.get_by_id(id).code
