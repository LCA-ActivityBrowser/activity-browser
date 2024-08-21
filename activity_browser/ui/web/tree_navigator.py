import json
import time
from heapq import heappush
from typing import List, Optional, Dict

import bw2calc as bc
import bw2data as bd
from PySide2 import QtWidgets
from PySide2.QtCore import Slot
from PySide2.QtWidgets import QComboBox
from bw2calc import LCA
from bw_graph_tools.graph_traversal import Edge as GraphEdge, Counter, CachingSolver, Node
from bw_graph_tools.graph_traversal import NewNodeEachVisitGraphTraversal
from bw_graph_tools.graph_traversal import Node as GraphNode

from activity_browser import log, signals
from activity_browser.mod import bw2data as bd
from activity_browser.mod.bw2data.backends import ActivityDataset
from activity_browser.utils import get_base_path
from .base import BaseGraph, BaseNavigatorWidget
from ...bwutils.commontasks import identify_activity_type
from ...bwutils.superstructure.graph_traversal_with_scenario import (
    GraphTraversalWithScenario,
)


class TreeNavigatorWidget(BaseNavigatorWidget):
    HELP_TEXT = """
    LCA Dynamic Tree Navigator:

    Red flows: Impacts
    Green flows: Avoided impacts

    """
    HTML_FILE = str(get_base_path().joinpath("static", "tree_navigator.html").resolve())

    def __init__(self, cs_name, parent=None):
        super().__init__(parent, css_file="tree_navigator.css")

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
        self.send_json()

    def connect_signals(self):
        super().connect_signals()
        self.button_calculate.clicked.connect(self.new_sankey)
        signals.database_selected.connect(self.set_database)
        # checkboxes
        self.func_unit_cb.currentIndexChanged.connect(self.new_sankey)
        self.method_cb.currentIndexChanged.connect(self.new_sankey)
        self.scenario_cb.currentIndexChanged.connect(self.new_sankey)
        self.bridge.update_graph.connect(self.update_graph)

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
            # this Graph is already cached, generate the tree with Graph cached data
            log.debug(f"CACHED tree for: {demand}, {method}, key: {cache_key}")
            self.graph.new_graph(data)
            self.has_sankey = bool(self.graph.json_data)
            self.send_json()
            return

        start = time.time()
        log.debug(f"CALCULATE tree for: {demand}, {method}, key: {cache_key}")
        try:
            if scenario_lca:
                self.parent.mlca.update_lca_calculation_for_sankey(
                    scenario_index, demand, method_index
                )
            fu, data_objs, _ = bd.prepare_lca_inputs(demand=demand, method=method)
            lca = bc.LCA(demand=fu, data_objs=data_objs)
            lca.lci()
            lca.lcia()
            data = InteractiveGraphTraversal.calculate(
                lca_object=lca, cutoff=cut_off, max_calc=max_calc, max_depth=1
            )

            # store the metadata from this calculation
            data.metadata = {
                "lca": lca,
                "unit": bd.methods[method]["unit"],
                "cut_off": cut_off,
                "max_calc": max_calc,
            }
        except (ValueError, ZeroDivisionError) as e:
            QtWidgets.QMessageBox.information(
                None, "Nonsensical numeric result.", str(e)
            )
        log.debug(f"Completed graph traversal ({round(time.time() - start, 2)} seconds")

        # cache the generated Graph data
        self.cache[cache_key] = data

        # generate the new Graph
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

    @Slot(object, name="update_graph")
    def update_graph(self, click_dict: dict) -> None:
        """Update the graph with the specified JSON data."""
        traversed = self.graph.state_graph.traverse_from_node(click_dict["id"])
        if not traversed:
            # nothing has changed
            return
        self.graph.json_data = Graph.get_json_data(self.graph.state_graph.data)
        self.send_json()


class InteractiveGraphTraversal(NewNodeEachVisitGraphTraversal):
    """
    Graph traversal that maintains state for a partial depth graph traversal.
    """

    def __init__(self, nodes, edges, flows, calculation_count, metadata=None, parameters=None):
        super().__init__()
        self.nodes: Dict[int, GraphNode] = nodes
        self.edges: List[GraphEdge] = edges
        self.flows = flows
        self.calculation_count = calculation_count
        self.metadata = metadata or {}
        self.parameters = parameters or {}
        self.already_calculated = set()

    @property
    def data(self):
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "flows": self.flows,
            "calculation_count": self.calculation_count.value,
            "metadata": self.metadata
        }

    @classmethod
    def calculate(
            cls,
            lca_object: LCA,
            cutoff: Optional[float] = 5e-3,
            biosphere_cutoff: Optional[float] = 1e-4,
            max_calc: Optional[int] = 10000,
            max_depth: Optional[int] = None,
            skip_coproducts: Optional[bool] = False,
            separate_biosphere_flows: Optional[bool] = True,
            static_activity_indices: Optional[set[int]] = set(),
            functional_unit_unique_id: Optional[int] = -1,
    ) -> "InteractiveGraphTraversal":
        total_score = lca_object.score
        if total_score == 0:
            raise ValueError("Zero total LCA score makes traversal impossible")

        cutoff_score = abs(total_score * cutoff)
        biosphere_cutoff_score = abs(total_score * biosphere_cutoff)
        technosphere_matrix = lca_object.technosphere_matrix
        production_exchange_mapping = {
            x: y for x, y in zip(*cls.get_production_exchanges(lca_object.technosphere_mm))
        }
        heap, edges, flows = [], [], []
        calculation_count = Counter()
        characterized_biosphere = cls.get_characterized_biosphere(lca_object)
        caching_solver = CachingSolver(lca_object)

        nodes = {
            functional_unit_unique_id: Node(
                unique_id=functional_unit_unique_id,
                activity_datapackage_id=functional_unit_unique_id,
                activity_index=functional_unit_unique_id,
                reference_product_datapackage_id=functional_unit_unique_id,
                reference_product_index=functional_unit_unique_id,
                reference_product_production_amount=1.0,
                depth=0,
                supply_amount=1.0,
                cumulative_score=lca_object.score,
                direct_emissions_score=0.0,
            )
        }

        cls.traverse_edges(
            consumer_index=functional_unit_unique_id,
            consumer_unique_id=functional_unit_unique_id,
            product_indices=[lca_object.dicts.product[key] for key in lca_object.demand],
            product_amounts=lca_object.demand.values(),
            lca=lca_object,
            current_depth=0,
            max_depth=max_depth,
            calculation_count=calculation_count,
            characterized_biosphere=characterized_biosphere,
            matrix=technosphere_matrix,
            edges=edges,
            flows=flows,
            nodes=nodes,
            heap=heap,
            caching_solver=caching_solver,
            production_exchange_mapping=production_exchange_mapping,
            separate_biosphere_flows=separate_biosphere_flows,
            cutoff_score=cutoff_score,
            static_activity_indices=static_activity_indices,
            biosphere_cutoff_score=biosphere_cutoff_score,
        )

        cls.traverse(
            heap=heap,
            nodes=nodes,
            edges=edges,
            flows=flows,
            max_calc=max_calc,
            max_depth=max_depth,
            cutoff_score=cutoff_score,
            characterized_biosphere=characterized_biosphere,
            calculation_count=calculation_count,
            static_activity_indices=static_activity_indices,
            caching_solver=caching_solver,
            production_exchange_mapping=production_exchange_mapping,
            technosphere_matrix=technosphere_matrix,
            lca=lca_object,
            skip_coproducts=skip_coproducts,
            separate_biosphere_flows=separate_biosphere_flows,
            biosphere_cutoff_score=biosphere_cutoff_score,
        )

        flows.sort(reverse=True)

        non_terminal_nodes = {edge.consumer_unique_id for edge in edges}
        for node_id_key in nodes:
            if node_id_key not in non_terminal_nodes:
                nodes[node_id_key].terminal = True

        return cls(nodes, edges, flows, calculation_count, parameters=dict(
            max_calc=max_calc,
            cutoff_score=cutoff_score,
            characterized_biosphere=characterized_biosphere,
            calculation_count=calculation_count,
            static_activity_indices=static_activity_indices,
            caching_solver=caching_solver,
            production_exchange_mapping=production_exchange_mapping,
            technosphere_matrix=technosphere_matrix,
            lca=lca_object,
            skip_coproducts=skip_coproducts,
            separate_biosphere_flows=separate_biosphere_flows,
            biosphere_cutoff_score=biosphere_cutoff_score,
        ))

    def traverse_from_node(self, node_id: int, max_depth: Optional[int] = None) -> None:
        node = self.nodes[node_id]
        if getattr(node, '_ab_traversed', False):
            log.debug("Node(id=%s) already traversed", node_id)
            return False
        setattr(node, '_ab_traversed', True)
        self.traverse(
            heap=[(0, node)],
            nodes=self.nodes,
            edges=self.edges,
            flows=self.flows,
            max_depth=node.depth + 1 if max_depth is None else max_depth,
            **self.parameters
        )

        self.flows.sort(reverse=True)

        non_terminal_nodes = {edge.consumer_unique_id for edge in self.edges}
        for node_id_key in self.nodes:
            if node_id_key not in non_terminal_nodes:
                terminal = True
            else:
                terminal = False
            self.nodes[node_id_key].terminal = terminal

        return True


class Graph(BaseGraph):
    """
    Python side representation of the graph.
    Functionality for graph navigation (e.g. adding and removing nodes).
    A JSON representation of the graph (edges and nodes) enables its use in javascript/html/css.
    """

    def __init__(self):
        super().__init__()
        self.state_graph: Optional["InteractiveGraphTraversal"] = None

    def new_graph(self, state_graph: "InteractiveGraphTraversal"):
        self.state_graph = state_graph
        self.json_data = Graph.get_json_data(self.state_graph.data)
        self.update()

    @staticmethod
    def get_json_data(data) -> str:
        """Transform graph traversal output to JSON data.

        We use the [dagre](https://github.com/dagrejs/dagre) javascript library for rendering directed graphs. We need to provide the following:

        ```python
        {
            'max_impact': float,  # Total LCA score,
            'title': str,  # Graph title
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
            cum_score = nodes[edge.producer_unique_id].cumulative_score
            unit = bd.get_node(
                id=nodes[edge.producer_unique_id].reference_product_datapackage_id
            ).get("unit", "(unknown)")
            return {
                "source_id": edge.producer_unique_id,
                "target_id": edge.consumer_unique_id,
                "amount": edge.amount,
                "weight": abs(cum_score / total_score) * max_edge_width,
                "label": f"{round(cum_score, 3)} {lcia_unit}",
                "class": "benefit" if cum_score < 0 else "impact",
                "tooltip": f"<b>{round(cum_score, 3)} {lcia_unit}</b> ({edge.amount:.2g} {unit})",
            }

        def convert_node_to_json(
                graph_node: GraphNode,
                total_score: float,
                fu: dict,
                lcia_unit: str,
                max_name_length: int = 20,
        ) -> dict:
            expanded = getattr(graph_node, "_ab_traversed", False)
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
                "expanded": expanded,
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
                <br>Individual impact: {dir_score} {lcia_unit} ({frac_dir_score}%)
                <br>Cumulative impact: {cum_score} {lcia_unit} ({frac_cum_score}%)
                <br>Expanded: {expanded}
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
            "title": "Tree graph result",
        }

        return json.dumps(json_data)


def id_to_key(id):
    if isinstance(id, tuple):
        return id
    return ActivityDataset.get_by_id(id).database, ActivityDataset.get_by_id(id).code
