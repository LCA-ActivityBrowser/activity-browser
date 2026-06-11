# -*- coding: utf-8 -*-
import json
import os
import time
from typing import List
from loguru import logger

import bw2calc as bc
import numpy
from bw_graph_tools.graph_traversal import Edge as GraphEdge
from bw_graph_tools.graph_traversal import NewNodeEachVisitGraphTraversal
from bw_graph_tools.graph_traversal import Node as GraphNode
from qtpy import QtWidgets
from qtpy.QtCore import Slot
from qtpy.QtWidgets import QComboBox

from activity_browser.mod import bw2data as bd
from bw2data.backends import ActivityDataset

from activity_browser.bwutils.commontasks import identify_activity_type
from activity_browser.bwutils.export_names import lca_export_basename
from activity_browser.bwutils.filesystem import get_package_path
from activity_browser.ui import icons, widgets

from .style import header, horizontal_line


def _flow_product_name_from_edge(lca, edge: GraphEdge) -> str:
    """Human-readable product on this technosphere edge.

    GraphTraversal ``Edge`` objects expose ``product_index`` (technosphere matrix row)
    but not a label string; resolve the row via ``lca.reverse_dict()`` /
    ``product_dict_rev`` and Brightway node metadata.
    """
    try:
        if getattr(lca, "product_dict_rev", None) is None:
            rev = lca.reverse_dict()
            if not isinstance(rev, tuple) or len(rev) < 3:
                return ""
            lca.activity_dict_rev, lca.product_dict_rev, lca.biosphere_dict_rev = rev
    except Exception:
        return ""
    try:
        key = lca.product_dict_rev.get(edge.product_index)
        if key is None:
            return ""
    except Exception:
        return ""
    try:
        if isinstance(key, tuple) and len(key) >= 2:
            node = bd.get_activity(key)
        else:
            node = bd.get_node(id=key)
    except Exception:
        return ""
    if not node:
        return ""
    return (node.get("reference product") or node.get("name") or "").strip()


def _header_layout_with_help(header_text: str, help_widget: QtWidgets.QWidget) -> QtWidgets.QVBoxLayout:
    hlayout = QtWidgets.QHBoxLayout()
    hlayout.addWidget(header(header_text))
    hlayout.addWidget(help_widget)
    hlayout.setStretch(0, 1)
    vlayout = QtWidgets.QVBoxLayout()
    vlayout.addLayout(hlayout)
    vlayout.addWidget(horizontal_line())
    return vlayout


class SankeyNavigatorWidget(widgets.ABAbstractNavigator):
    HELP_TEXT = """
    LCA Sankey:

    Red flows: Impacts
    Green flows: Avoided impacts

    """
    HTML_FILE = str(get_package_path() / "static" / "sankey_navigator.html")

    def __init__(self, cs_name, parent=None):
        super().__init__(parent, css_file="sankey_navigator.css")

        self.cache = {}  # we cache the calculated data to improve responsiveness
        self.parent = parent
        self.has_scenarios = self.parent.has_scenarios
        self.cs = cs_name
        self.plot_name = lca_export_basename(cs_name, "Sankey")
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

        self.help_button = QtWidgets.QToolBar(self)
        self.help_button.addAction(
            icons.qicons.question,
            "Left click for help on the Sankey diagram",
            self.show_sankey_help,
        )

        # graph
        self.draw_graph()
        self.construct_layout()
        self.connect_signals()

    @Slot(name="loadFinishedHandler")
    def load_finished_handler(self) -> None:
        if self.has_sankey:
            self.send_json()

    @Slot()
    def show_sankey_help(self):
        QtWidgets.QMessageBox.question(
            self,
            "Sankey",
            self.HELP_TEXT.strip(),
            QtWidgets.QMessageBox.Ok,
            QtWidgets.QMessageBox.Ok,
        )

    def connect_signals(self):
        self.button_back.clicked.connect(self.go_back)
        self.button_forward.clicked.connect(self.go_forward)
        self.button_refresh.clicked.connect(self.draw_graph)
        self.button_calculate.clicked.connect(self.new_sankey)
        self.func_unit_cb.currentIndexChanged.connect(self.new_sankey)
        self.method_cb.currentIndexChanged.connect(self.new_sankey)
        self.scenario_cb.currentIndexChanged.connect(self.new_sankey)

    def construct_layout(self) -> None:
        """Layout of Sankey Navigator"""
        super().construct_layout()
        self.label_help.hide()
        self.button_random_activity.hide()
        self.button_toggle_help.hide()

        self.layout.setContentsMargins(4, 2, 4, 2)
        self.layout.setSpacing(4)

        self.update_calculation_setup()

        self.layout.addLayout(_header_layout_with_help("Sankey", self.help_button))

        fixed = QtWidgets.QSizePolicy.Fixed
        for btn in (self.button_back, self.button_forward):
            btn.setSizePolicy(fixed, fixed)

        top_row = QtWidgets.QHBoxLayout()
        top_row.setSpacing(4)
        top_row.addWidget(self.button_back)
        top_row.addWidget(self.button_forward)
        top_row.addWidget(self.button_refresh)
        top_row.addSpacing(12)

        self.cutoff_sb.setRange(0.0, 1.0)
        self.cutoff_sb.setSingleStep(0.01)
        self.cutoff_sb.setDecimals(3)
        self.cutoff_sb.setValue(0.05)
        self.cutoff_sb.setKeyboardTracking(False)
        top_row.addWidget(QtWidgets.QLabel("Cutoff:"))
        top_row.addWidget(self.cutoff_sb)

        self.max_calc_sb.setRange(1, 2000)
        self.max_calc_sb.setSingleStep(50)
        self.max_calc_sb.setDecimals(0)
        self.max_calc_sb.setValue(250)
        self.max_calc_sb.setKeyboardTracking(False)
        top_row.addWidget(QtWidgets.QLabel("Depth:"))
        top_row.addWidget(self.max_calc_sb)
        top_row.addWidget(self.button_calculate)
        top_row.addStretch(1)

        params_row = QtWidgets.QHBoxLayout()
        params_row.setSpacing(6)
        params_row.addWidget(QtWidgets.QLabel("Reference flow:"))
        params_row.addWidget(self.func_unit_cb, 1)
        params_row.addWidget(QtWidgets.QLabel("Impact:"))
        params_row.addWidget(self.method_cb, 1)
        params_row.addWidget(self.scenario_label)
        params_row.addWidget(self.scenario_cb)

        self.layout.addLayout(top_row)
        self.layout.addLayout(params_row)
        self.layout.addWidget(self.view, 1)
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
        self.update_sankey(
            demand,
            method,
            demand_index=demand_index,
            method_index=method_index,
            scenario_index=scenario_index,
            scenario_lca=scenario_lca,
            cut_off=self.cutoff_sb.value(),
            max_calc=int(self.max_calc_sb.value()),
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
            logger.debug(f"CACHED sankey for: {demand}, {method}, key: {cache_key}")
            self.graph.new_graph(data)
            self.has_sankey = bool(self.graph.json_data)
            self.update_plot_name("Sankey", method, demand_index, scenario_index)
            self.send_json()
            return

        start = time.time()
        logger.debug(f"CALCULATE sankey for: {demand}, {method}, key: {cache_key}")
        try:
            if scenario_lca:
                self.parent.mlca.update_lca_calculation_for_sankey(
                    scenario_index, demand, method_index
                )
                lca = self.parent.mlca.lca
                data = NewNodeEachVisitGraphTraversal.calculate(
                    lca, cutoff=cut_off, max_calc=int(max_calc)
                )
            else:
                fu, data_objs, _ = bd.prepare_lca_inputs(demand=demand, method=method)
                lca = bc.LCA(demand=fu, data_objs=data_objs)
                lca.lci(factorize=True)
                lca.lcia()
                data = NewNodeEachVisitGraphTraversal.calculate(
                    lca_object=lca, cutoff=cut_off, max_calc=int(max_calc)
                )

            # store the metadata from this calculation
            data["metadata"] = {
                "lca": lca,
                "unit": bd.methods[method]["unit"],
            }
        except (ValueError, ZeroDivisionError) as e:
            QtWidgets.QMessageBox.information(
                None, "Nonsensical numeric result.", str(e)
            )
        logger.debug(f"Completed graph traversal ({round(time.time() - start, 2)} seconds")

        # cache the generated Sankey data
        self.cache[cache_key] = data

        # generate the new Sankey
        self.graph.new_graph(data)
        self.has_sankey = bool(self.graph.json_data)
        self.update_plot_name("Sankey", method, demand_index, scenario_index)
        self.send_json()

    def random_graph(self) -> None:
        """Not used in the Sankey tab (random activity is not offered here)."""
        pass


def convert_numpy_types(obj) -> int | float | list:
    """Converts numpy types into serializable types"""
    if isinstance(obj, numpy.integer):
        return int(obj)
    if isinstance(obj, numpy.floating):
        return float(obj)
    if isinstance(obj, numpy.ndarray):
        return obj.tolist()
    return obj


def make_serializable(data: dict) -> dict:
    """Converts numpy data into serializable values for json.dumps"""
    for key, value in data.items():
        if isinstance(value, dict):
            make_serializable(value)
        elif isinstance(value, list):
            data[key] = [
                (
                    convert_numpy_types(v)
                    if not isinstance(v, dict)
                    else make_serializable(v)
                )
                for v in value
            ]
        else:
            data[key] = convert_numpy_types(value)
    return data


class Graph(widgets.ABAbstractGraph):
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
        """Transform graph traversal output to JSON data.

        We use the [dagre](https://github.com/dagrejs/dagre) javascript library for rendering directed graphs. We need to provide the following:

        ```python
        {
            'max_impact': float,  # Total LCA score,
            'edges': [{
                'source_id': int,  # Unique ID of producer of material or energy in graph
                'target_id': int,  # Unique ID of consumer of material or energy in graph
                'weight': float,  #  In graph units, relative to `max_edge_width`
                'label': str,  # HTML label
                'product': str,  # The label of the flowing material or energy
                'class': str,  # "benefit" or "impact"; controls styling
                'label': str,  # HTML label
                'toottip': str,  # HTML tooltip
            }],
            'nodes': [{
                'direct_emissions_score_normalized': float,  # Fraction of total LCA score from direct emissions
                'product': str,  # Reference product label, if any
                'location': str,  # Location, if any
                'id': int,  # Graph traversal ID
                'database_id': int,  # Node ID in SQLite database
                'database': str,  # Database name
                'class': str,  # Enumerated set of class label strings
                'label': str,  # HTML label including name and location
                'toottip': str,  # HTML tooltip
            }],
        }

        ```

        """
        lca_score = data["metadata"]["lca"].score
        lcia_unit = data["metadata"]["unit"]
        demand = data["metadata"]["lca"].demand

        def convert_edge_to_json(
            edge: GraphEdge,
            nodes: dict[int, GraphNode],
            total_score: float,
            lcia_unit: str,
            max_edge_width: int = 40,
        ) -> dict:
            lca = data["metadata"]["lca"]
            cum_score = nodes[edge.producer_unique_id].cumulative_score
            unit = bd.get_node(
                id=nodes[edge.producer_unique_id].reference_product_datapackage_id
            ).get("unit", "(unknown)")
            total = float(total_score) if total_score else 0.0
            pct_of_total = (float(cum_score) / total * 100.0) if total else 0.0
            return {
                "source_id": edge.producer_unique_id,
                "target_id": edge.consumer_unique_id,
                "amount": edge.amount,
                "amount_unit": str(unit),
                "weight": abs(cum_score / (total_score or 1)) * max_edge_width,
                "label": f"{round(cum_score, 3)} {lcia_unit}",
                "impact_cumulative": float(cum_score),
                "impact_pct_total": float(pct_of_total),
                "impact_unit": str(lcia_unit),
                "class": "benefit" if cum_score < 0 else "impact",
                "tooltip": f"<b>{round(cum_score, 3)} {lcia_unit}</b> ({edge.amount:.2g} {unit})",
                "product": _flow_product_name_from_edge(lca, edge),
            }

        def convert_node_to_json(
            graph_node: GraphNode,
            total_score: float,
            fu: dict,
            lcia_unit: str,
            max_name_length: int = 20,
        ) -> dict:
            db_node = bd.get_node(id=graph_node.activity_datapackage_id)
            data = {
                "direct_emissions_score_normalized": graph_node.direct_emissions_score
                / (total_score or 1),
                "direct_emissions_score": graph_node.direct_emissions_score,
                "cumulative_score": graph_node.cumulative_score,
                "cumulative_score_normalized": graph_node.cumulative_score
                / (total_score or 1),
                "product": db_node.get("reference product", ""),
                "location": db_node.get("location", "(unknown)"),
                "id": graph_node.unique_id,
                "database_id": graph_node.activity_datapackage_id,
                "database": db_node["database"],
                "class": (
                    "demand"
                    if graph_node.activity_datapackage_id in fu
                    else identify_activity_type(db_node)
                ),
                "name": db_node.get("name", "(unnamed)"),
            }
            frac_dir_score = round(data["direct_emissions_score_normalized"] * 100, 2)
            dir_score = round(data["direct_emissions_score"], 3)
            frac_cum_score = round(data["cumulative_score_normalized"] * 100, 2)
            cum_score = round(data["cumulative_score"], 3)
            data[
                "label"
            ] = f"""{db_node['name'][:max_name_length]}
{data['location']}
{frac_dir_score}%"""
            data[
                "tooltip"
            ] = f"""
                <b>{data['name']}</b>
                <br>Individual impact: {dir_score} {lcia_unit} ({frac_dir_score }%)
                <br>Cumulative impact: {cum_score} {lcia_unit} ({frac_cum_score}%)
            """
            return data

        json_data = {
            "nodes": [
                convert_node_to_json(node, lca_score, demand, lcia_unit)
                for idx, node in data["nodes"].items()
                if idx != -1
            ],
            "edges": [
                convert_edge_to_json(edge, data["nodes"], lca_score, lcia_unit)
                for edge in data["edges"]
                if edge.producer_index != -1 and edge.consumer_index != -1
            ],
        }

        return json.dumps(json_data)


def id_to_key(id):
    if isinstance(id, tuple):
        return id
    return ActivityDataset.get_by_id(id).database, ActivityDataset.get_by_id(id).code
