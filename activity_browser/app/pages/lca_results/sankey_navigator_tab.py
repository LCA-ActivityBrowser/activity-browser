# -*- coding: utf-8 -*-
import json
import time
from typing import List
from loguru import logger

import bw2calc as bc
from bw_graph_tools.graph_traversal import Edge as GraphEdge
from bw_graph_tools.graph_traversal import GraphTraversalSettings
from bw_graph_tools.graph_traversal import NewNodeEachVisitGraphTraversal
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Slot

from activity_browser.mod import bw2data as bd

from activity_browser import app
from activity_browser.bwutils.graph_traversal.engine import (
    PLOT_AGGREGATE_FIELDS,
    PLOT_AGGREGATE_LABELS,
    activity_metadata_for_ids,
    activities_from_open_refs,
    open_process_refs,
    safe_traverse_from_node,
    suppress_graph_traversal_warnings,
)
from activity_browser.bwutils.graph_traversal.sankey import (
    apply_graph_display_click,
    d3_graph_payload,
    graph_display_set,
    include_new_unique_suppliers,
    inventory_direct_lookup,
    keep_best_visit_per_activity,
    mapped_edge_amounts,
    overlay_inventory_directs,
    run_expand_policy,
    unique_process_stats,
    unopened_same_activity_hops,
)
from activity_browser.bwutils.export_names import lca_export_basename
from activity_browser.bwutils.filesystem import get_package_path
from activity_browser.bwutils.lca_inputs import activity_direct_impacts, prepared_lca_inputs
from activity_browser.ui import widgets
from activity_browser.ui.selection_history import IndexSelectionHistory
from activity_browser.ui.widgets.abstract_navigator import savefilepath, to_svg

from .contribution_tree_model import (
    EXPAND_MODE_CUMULATIVE,
    EXPAND_MODE_PATH,
    EXPAND_MODE_TIER,
)
from .style import (
    app_is_dark,
    configure_lca_tab_layout,
    inject_qt_ui_font,
    lca_header_layout,
    lca_help_tool_button,
    lca_run_button,
    lca_tab_control_row,
    show_open_process_menu,
    SmallComboBox,
)

from .combobox_utils import configure_selection_comboboxes, scenario_labels

# Runaway guard per NNEV hop, not the Adjust policy stop.
SANKEY_MAX_CALC = 1000
SANKEY_STARTUP_TIER = 1


class _StoppableNNEV(NewNodeEachVisitGraphTraversal):
    """NNEV that Stop can halt; nodes already visited stay on the graph."""

    def __init__(self, lca, settings, should_continue=None, **kwargs):
        super().__init__(lca, settings, **kwargs)
        self._should_continue = should_continue

    @property
    def exceeded_calculation_count(self):
        if self._should_continue is not None and not self._should_continue():
            return True
        return super().exceeded_calculation_count


class SankeyNNEVState:
    """Adapter so :func:`run_expand_policy` can one-hop NNEV like SNEV (adjust policy)."""

    def __init__(self, trav: NewNodeEachVisitGraphTraversal):
        self._trav = trav
        self.visited_nodes: set = set()

    @property
    def nodes(self):
        return self._trav.nodes

    @property
    def edges(self):
        return self._trav.edges

    @property
    def _root_node(self):
        return self._trav._root_node

    def traverse_from_node(self, unique_id, depth=1):
        if unique_id in self.visited_nodes:
            return False
        node = self._trav.nodes.get(unique_id)
        if node is None:
            return False
        n_before = len(self._trav.nodes)
        if unique_id == self._root_node.unique_id:
            self._trav.traverse(depth=depth)
        else:
            self._trav.traverse(nodes=[node], depth=depth)
        if (
            unique_id != self._root_node.unique_id
            and self._trav.exceeded_calculation_count
            and len(self._trav.nodes) == n_before
        ):
            return False
        self.visited_nodes.add(unique_id)
        return True

    def snapshot(self):
        return (
            dict(self._trav._nodes),
            list(self._trav._edges),
            list(self._trav._flows),
            set(self.visited_nodes),
        )

    def restore(self, snap) -> None:
        nodes, edges, flows, visited = snap
        self._trav._nodes = nodes
        self._trav._edges = edges
        self._trav._flows = flows
        self.visited_nodes = visited


def _flow_product_name_from_edge(lca, edge: GraphEdge, metadata_lookup=None) -> str:
    """Human-readable product on this technosphere edge.

    GraphTraversal ``Edge`` objects expose ``product_index`` (technosphere matrix
    row) but not a label; resolve via ``product_dict_rev`` then MetaDataStore
    (ADR-0005). Does not call ``bd.get_node`` for display.
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
        aid = int(key)
    except (TypeError, ValueError):
        return ""
    if metadata_lookup is None:
        return ""
    meta = metadata_lookup(aid) or {}
    return str(meta.get("product") or meta.get("name") or "").strip()


class SankeyNavigatorWidget(widgets.ABAbstractNavigator):
    HELP_TEXT = """
    <html><body>
    <p><b>Sankey</b> shows supply-chain impact for one reference flow, impact
    category, and scenario. Back/Forward are selection history. Each process
    appears once (circular supply is two boxes, not an unrolled path).</p>
    <p><b>Legend</b>
    <ul>
      <li><i>Flows</i>: red = path impact (green = avoided).</li>
      <li><i>Processes</i>: blue = direct impact (green = benefit, white = none).</li>
      <li><i>Triangles</i>: expand or collapse that process.</li>
    </ul></p>
    <p><b>Adjust to</b> — <b>Tier</b> opens to that depth.
    <b>Individual path impact</b> and <b>Cumulative impact</b> continue the
    same calculated graph until the unique-process display set meets the
    target, then stop — same idea as the Tree tab. A new reference flow,
    impact category, or scenario opens at the reference flow (tier 1).
    Click <b>Adjust</b> to apply the current policy. Stop keeps the graph
    calculated so far. Clicking a triangle calculates one hop of new
    processes for each unopened visit of that process. Right-click a box for
    <b>Open process</b> (Activity Details). <b>Show all</b> (footer) draws every
    calculated unique process.</p>
    <p><b>Cutoff</b> prunes branches below this share of the total score during
    calculation.</p>
    <p><b>Aggregate by</b> rolls up sibling processes (same tier) by attribute.
    <b>Color by</b> tints process boxes; Direct impact uses blue/green intensity.
    Ribbons stay red/green by path impact.</p>
    </body></html>
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
        self.graph = Graph()

        # Additional Qt objects
        self.scenario_label = QtWidgets.QLabel("Scenario:")
        self.func_unit_cb = SmallComboBox(self)
        self.method_cb = SmallComboBox(self)
        self.scenario_cb = SmallComboBox(self)
        self.cutoff_sb = QtWidgets.QDoubleSpinBox()
        self.button_adjust = lca_run_button(self, text="Adjust")
        self.button_adjust.setToolTip(
            "Apply the current cutoff and adjust policy"
        )
        self.expand_mode_cb = SmallComboBox(self)
        self.expand_mode_cb.addItem("Tier", EXPAND_MODE_TIER)
        self.expand_mode_cb.addItem("Individual path impact", EXPAND_MODE_PATH)
        self.expand_mode_cb.addItem("Cumulative impact", EXPAND_MODE_CUMULATIVE)
        self.expand_mode_cb.setToolTip("How far Adjust opens the calculated Sankey")
        self.expand_value_sb = QtWidgets.QDoubleSpinBox()
        self.expand_value_sb.setKeyboardTracking(False)
        self.aggregate_by_cb = SmallComboBox(self)
        self.aggregate_by_cb.addItem("None", None)
        for field in PLOT_AGGREGATE_FIELDS:
            self.aggregate_by_cb.addItem(PLOT_AGGREGATE_LABELS[field], field)
        self.aggregate_by_cb.setToolTip(
            "Roll up sibling process boxes by metadata (graph only)"
        )
        self.color_by_cb = SmallComboBox(self)
        self.color_by_cb.addItem("Direct impact", "direct")
        self.color_by_cb.addItem("Product", "product")
        self.color_by_cb.addItem("Process", "process")
        self.color_by_cb.addItem("Location", "location")
        self.color_by_cb.addItem("Database", "database")
        self.color_by_cb.setToolTip(
            "Tint process boxes (plot only). Ribbons stay red/green by path impact."
        )
        self._stats_label = QtWidgets.QLabel("")
        self._stats_label.setToolTip(
            "Shown = unique processes drawn. Calculated = unique processes in the graph, including those Adjust is hiding."
        )
        self.show_all_btn = QtWidgets.QPushButton("Show all")
        self.show_all_btn.setToolTip(
            "Draw every calculated unique process (Adjust may have hidden some)."
        )
        self.show_all_btn.setEnabled(False)
        self.export_plot_copy_btn = QtWidgets.QPushButton("Copy")
        self.export_plot_copy_btn.setToolTip("Copy the plot to the clipboard as an image")
        self.export_plot_png_btn = QtWidgets.QPushButton(".png")
        self.export_plot_svg_btn = QtWidgets.QPushButton(".svg")
        self._selection_history = IndexSelectionHistory()
        self._suppress_selection = False
        self._full_data = None
        self._included_uids: set | None = None
        self._cache_key: tuple | None = None
        self._last_expand_target_pct: float | None = None
        self._meta_cache: dict = {}
        self.layout = QtWidgets.QVBoxLayout()

        self.help_button = lca_help_tool_button(
            self,
            "Left click for help on the Sankey diagram",
            self.show_sankey_help,
        )

        # graph
        self.draw_graph()
        self.construct_layout()
        self.connect_signals()

    @Slot(name="loadFinishedHandler")
    def load_finished_handler(self) -> None:
        self._apply_web_theme()
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
        self.button_back.clicked.connect(self._on_selection_back)
        self.button_forward.clicked.connect(self._on_selection_forward)
        self.button_adjust.clicked.connect(self._on_adjust_clicked)
        self.show_all_btn.clicked.connect(self._on_show_all_clicked)
        self.func_unit_cb.currentIndexChanged.connect(self._on_selection_changed)
        self.method_cb.currentIndexChanged.connect(self._on_selection_changed)
        self.scenario_cb.currentIndexChanged.connect(self._on_selection_changed)
        self.expand_mode_cb.currentIndexChanged.connect(self._on_expand_mode_changed)
        self.aggregate_by_cb.currentIndexChanged.connect(self._redraw_sankey_display)
        self.color_by_cb.currentIndexChanged.connect(self._redraw_sankey_display)
        self.export_plot_copy_btn.clicked.connect(self._export_plot_copy)
        self.export_plot_png_btn.clicked.connect(self._export_plot_png)
        self.export_plot_svg_btn.clicked.connect(self._export_plot_svg)
        self.bridge.update_graph.connect(self._on_node_clicked)
        app.application.theme_changed.connect(self._apply_web_theme)

    @Slot()
    def _apply_web_theme(self) -> None:
        QtCore.QTimer.singleShot(0, self._lock_web_theme)

    def _lock_web_theme(self) -> None:
        dark = "true" if app_is_dark() else "false"
        self.page.runJavaScript(
            "if (window.abLockGraphTheme) window.abLockGraphTheme(" + dark + ");"
        )
        inject_qt_ui_font(self.page)

    def construct_layout(self) -> None:
        """Layout of Sankey Navigator"""
        super().construct_layout()
        self.label_help.hide()
        self.button_random_activity.hide()
        self.button_toggle_help.hide()
        self.button_refresh.hide()

        configure_lca_tab_layout(self.layout)

        self.update_calculation_setup()

        self.layout.addLayout(lca_header_layout("Sankey", self.help_button))

        fixed = QtWidgets.QSizePolicy.Fixed
        self.button_back.setToolTip(
            "Previous reference flow, impact category, or scenario"
        )
        self.button_forward.setToolTip(
            "Next reference flow, impact category, or scenario"
        )
        self.button_back.setEnabled(False)
        self.button_forward.setEnabled(False)
        for btn in (self.button_back, self.button_forward):
            btn.setSizePolicy(fixed, fixed)

        controls_row = lca_tab_control_row()
        controls_row.addWidget(QtWidgets.QLabel("Reference flow:"))
        controls_row.addWidget(self.func_unit_cb)
        controls_row.addWidget(QtWidgets.QLabel("Impact category:"))
        controls_row.addWidget(self.method_cb)
        controls_row.addWidget(self.scenario_label)
        controls_row.addWidget(self.scenario_cb)
        controls_row.addWidget(self.button_back)
        controls_row.addWidget(self.button_forward)
        controls_row.addStretch(1)

        self.cutoff_sb.setRange(0.001, 99.0)
        self.cutoff_sb.setSingleStep(0.01)
        self.cutoff_sb.setDecimals(3)
        self.cutoff_sb.setValue(0.1)
        self.cutoff_sb.setSuffix(" %")
        self.cutoff_sb.setKeyboardTracking(False)
        self.cutoff_sb.setToolTip(
            "Graph traversal cutoff: prune branches below this share of the total score"
        )

        policy_row = lca_tab_control_row()
        policy_row.addWidget(QtWidgets.QLabel("Cutoff:"))
        policy_row.addWidget(self.cutoff_sb)
        policy_row.addSpacing(12)
        policy_row.addWidget(QtWidgets.QLabel("Adjust to:"))
        policy_row.addWidget(self.expand_mode_cb)
        policy_row.addWidget(self.expand_value_sb)
        policy_row.addWidget(self.button_adjust)
        policy_row.addSpacing(12)
        policy_row.addWidget(QtWidgets.QLabel("Aggregate by:"))
        policy_row.addWidget(self.aggregate_by_cb)
        policy_row.addWidget(QtWidgets.QLabel("Color by:"))
        policy_row.addWidget(self.color_by_cb)
        policy_row.addStretch(1)

        self.layout.addLayout(controls_row)
        self.layout.addLayout(policy_row)
        self.layout.addWidget(self.view, 1)
        footer = QtWidgets.QHBoxLayout()
        footer.addWidget(self._stats_label)
        footer.addWidget(self.show_all_btn)
        footer.addStretch(1)
        footer.addWidget(QtWidgets.QLabel("Plot:"))
        footer.addWidget(self.export_plot_copy_btn)
        footer.addWidget(self.export_plot_png_btn)
        footer.addWidget(self.export_plot_svg_btn)
        self.layout.addLayout(footer)
        self.setLayout(self.layout)
        self._apply_expand_mode_defaults(reset_value=True)

    def get_scenario_labels(self) -> List[str]:
        """Get scenario labels if scenario is used."""
        return scenario_labels(self.parent)

    def configure_scenario(self):
        """Determine if scenario Qt widgets are visible or not and retrieve
        scenario labels for the selection drop-down box.
        """
        configure_selection_comboboxes(
            parent=self.parent,
            fu_box=self.func_unit_cb,
            method_box=self.method_cb,
            scenario_box=self.scenario_cb,
            scenario_label=self.scenario_label,
            has_scenarios=self.has_scenarios,
        )
        self.scenarios = self.get_scenario_labels()

    @property
    def func_units(self):
        mlca = getattr(self.parent, "mlca", None)
        if mlca is None:
            return []
        return [
            {bd.get_activity(k): v for k, v in fu.items()}
            for fu in mlca.func_units
        ]

    @property
    def methods(self):
        mlca = getattr(self.parent, "mlca", None)
        return list(mlca.methods) if mlca else []

    def update_calculation_setup(self, cs_name=None) -> None:
        """Update Calculation Setup, reference flows and impact categories, and dropdown menus."""
        self.func_unit_cb.blockSignals(True)
        self.method_cb.blockSignals(True)
        self.scenario_cb.blockSignals(True)

        self.cs = cs_name or self.cs
        self.configure_scenario()

        self.func_unit_cb.blockSignals(False)
        self.method_cb.blockSignals(False)
        self.scenario_cb.blockSignals(False)
        self._seed_selection_history()

    def new_sankey(self, *, apply_adjust: bool = False) -> None:
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
            cut_off=self._traversal_cutoff(),
            display_mode=self.expand_mode_cb.currentData() or EXPAND_MODE_TIER,
            display_value=float(self.expand_value_sb.value()),
            apply_adjust=apply_adjust,
        )

    def update_sankey(
        self,
        demand: dict,
        method: tuple,
        demand_index: int = None,
        method_index: int = None,
        scenario_index: int = None,
        scenario_lca: bool = False,
        cut_off=0.001,
        max_calc=SANKEY_MAX_CALC,
        max_depth: int | None = None,
        display_mode: str | None = None,
        display_value: float | None = None,
        apply_adjust: bool = False,
    ) -> None:
        """Ensure a calculated NNEV graph; continue Adjust only when requested."""

        mode = display_mode or EXPAND_MODE_TIER
        value = float(self.expand_value_sb.value() if display_value is None else display_value)
        cache_key = (
            demand_index,
            method_index,
            scenario_index,
            round(float(cut_off), 12),
        )
        self._cache_key = cache_key
        entry = self.cache.get(cache_key)
        progress = None
        try:
            if entry is None:
                logger.debug(f"CALCULATE sankey for: {demand}, {method}, key: {cache_key}")
                progress = self._busy_dialog("Calculating Sankey…")
                self._busy_tick(progress, "Running LCI / LCIA…")
                if progress.wasCanceled():
                    return
                if scenario_lca:
                    self.parent.mlca.update_lca_calculation_for_sankey(
                        scenario_index, demand, method_index
                    )
                    lca = self.parent.mlca.lca
                else:
                    fu, data_objs, _ = prepared_lca_inputs(demand, method)
                    lca = bc.LCA(demand=fu, data_objs=data_objs)
                    lca.lci(factorize=True)
                    lca.lcia()
                if progress.wasCanceled():
                    return
                settings = GraphTraversalSettings(
                    cutoff=cut_off,
                    max_calc=int(max_calc),
                    max_depth=None,
                )
                trav = _StoppableNNEV(lca, settings)
                state = SankeyNNEVState(trav)
                entry = {
                    "state": state,
                    "lca": lca,
                    "unit": bd.methods[method]["unit"],
                }
                self.cache[cache_key] = entry
                self._run_sankey_initial(entry, progress)
                data = self._sankey_data_from_entry(entry)
                n_nodes = max(0, len(entry["state"].nodes) - 1)
                self._busy_rebuild(progress, n_nodes)
                self._last_expand_target_pct = None
                self._show_sankey_data(
                    data,
                    method,
                    demand_index,
                    scenario_index,
                    included_uids=self._display_uids_for(
                        data,
                        mode=EXPAND_MODE_TIER,
                        value=float(SANKEY_STARTUP_TIER),
                    ),
                )
                self._persist_included_uids()
            elif apply_adjust:
                logger.debug(f"CACHED sankey for: {demand}, {method}, key: {cache_key}")
                progress = self._busy_dialog("Calculating Sankey…")
                self._run_sankey_adjust(entry, mode, value, progress)
                data = self._sankey_data_from_entry(entry)
                n_nodes = max(0, len(entry["state"].nodes) - 1)
                self._busy_rebuild(progress, n_nodes)
                self._last_expand_target_pct = (
                    value if mode in (EXPAND_MODE_PATH, EXPAND_MODE_CUMULATIVE) else None
                )
                self._show_sankey_data(data, method, demand_index, scenario_index)
                self._persist_included_uids()
            else:
                logger.debug(f"CACHED sankey for: {demand}, {method}, key: {cache_key}")
                data = self._sankey_data_from_entry(entry)
                stored = entry.get("included_uids")
                self._show_sankey_data(
                    data,
                    method,
                    demand_index,
                    scenario_index,
                    included_uids=stored,
                )
                if stored is None:
                    self._persist_included_uids()
        except (ValueError, ZeroDivisionError) as e:
            QtWidgets.QMessageBox.information(
                None, "Nonsensical numeric result.", str(e)
            )
        finally:
            if progress is not None:
                progress.close()
                progress.deleteLater()

    def _sankey_data_from_entry(self, entry: dict) -> dict:
        state = entry["state"]
        lca = entry["lca"]
        directs = entry.get("inventory_directs")
        if directs is None:
            directs = activity_direct_impacts(lca)
            entry["inventory_directs"] = directs
        return {
            "nodes": state.nodes,
            "edges": state.edges,
            "flows": getattr(state._trav, "flows", []),
            "opened": set(state.visited_nodes),
            "state": state,
            "metadata": {
                "lca": lca,
                "unit": entry["unit"],
                "inventory_directs": directs,
            },
        }

    def _run_sankey_initial(self, entry: dict, progress) -> None:
        """One hop from the reference flow; do not apply the current Adjust widgets."""
        state = entry["state"]
        trav = state._trav
        trav._should_continue = lambda: not progress.wasCanceled()
        lca = entry["lca"]
        directs = entry.get("inventory_directs")
        if directs is None:
            directs = activity_direct_impacts(lca)
            entry["inventory_directs"] = directs
        self._busy_tick(progress, "Traversing supply chain…")
        with suppress_graph_traversal_warnings():
            if not state.visited_nodes:
                safe_traverse_from_node(state, state._root_node.unique_id, depth=1)
        trav._should_continue = None

    def _run_sankey_adjust(self, entry: dict, mode, value, progress) -> None:
        state = entry["state"]
        lca = entry["lca"]
        start = time.time()
        self._busy_tick(progress, "Traversing supply chain…")

        def _tick(step, n_nodes):
            label = (
                f"Traversing supply chain… ({n_nodes} nodes)"
                if step % 5 == 0
                else None
            )
            return self._busy_tick(progress, label)

        trav = state._trav
        trav._should_continue = lambda: not progress.wasCanceled()
        directs = entry.get("inventory_directs")
        if directs is None:
            directs = activity_direct_impacts(lca)
            entry["inventory_directs"] = directs
        lookup = (
            inventory_direct_lookup(state.nodes, directs) if directs else None
        )
        with suppress_graph_traversal_warnings():
            if not state.visited_nodes:
                safe_traverse_from_node(state, state._root_node.unique_id, depth=1)
            run_expand_policy(
                state,
                mode=mode,
                value=value,
                total_score=float(lca.score),
                on_progress=_tick,
                direct_lookup=lookup,
            )
        trav._should_continue = None
        logger.debug(
            f"Completed graph traversal ({round(time.time() - start, 2)} seconds"
        )

    def _persist_included_uids(self) -> None:
        key = self._cache_key
        if key is None or self._included_uids is None:
            return
        entry = self.cache.get(key)
        if entry is not None:
            entry["included_uids"] = set(self._included_uids)

    def _busy_dialog(self, label: str) -> QtWidgets.QProgressDialog:
        progress = QtWidgets.QProgressDialog(label, "Stop", 0, 0, self)
        progress.setWindowTitle("Sankey")
        progress.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, False)
        progress.show()
        progress.raise_()
        QtWidgets.QApplication.processEvents()
        return progress

    @staticmethod
    def _busy_tick(progress: QtWidgets.QProgressDialog, label: str | None = None) -> bool:
        if label is not None:
            progress.setLabelText(label)
        QtWidgets.QApplication.processEvents()
        return not progress.wasCanceled()

    def _busy_rebuild(self, progress: QtWidgets.QProgressDialog, n_nodes: int | None = None) -> None:
        if progress.wasCanceled():
            progress.reset()
            progress.setRange(0, 0)
        progress.setCancelButton(None)
        label = "Building plot…"
        if n_nodes:
            label = f"{label} ({n_nodes} nodes)"
        self._busy_tick(progress, label)

    def random_graph(self) -> None:
        """Not used in the Sankey tab (random activity is not offered here)."""
        pass

    def _graph_style_kwargs(self) -> dict:
        return {
            "aggregate_by": self.aggregate_by_cb.currentData(),
            "color_by": self.color_by_cb.currentData() or "direct",
            "metadata_lookup": self._lookup_activity_meta,
        }

    def _prefetch_metadata(self, data: dict) -> None:
        ids = [
            getattr(node, "activity_datapackage_id", None)
            for node in (data.get("nodes") or {}).values()
        ]
        wanted = [i for i in ids if isinstance(i, int) and i >= 0 and i not in self._meta_cache]
        if wanted:
            self._meta_cache.update(
                activity_metadata_for_ids(wanted, app.metadata.dataframe)
            )

    def _lookup_activity_meta(self, activity_id) -> dict:
        if activity_id is None:
            return {}
        if activity_id in self._meta_cache:
            return self._meta_cache[activity_id]
        found = activity_metadata_for_ids([activity_id], app.metadata.dataframe)
        if activity_id in found:
            self._meta_cache[activity_id] = found[activity_id]
            return found[activity_id]
        return {}

    def _redraw_sankey_display(self) -> None:
        if not self._full_data:
            return
        if self._included_uids is None:
            self._included_uids = self._display_uids_for(self._full_data)
        self.graph.new_graph(
            self._full_data,
            included_uids=self._included_uids,
            **self._graph_style_kwargs(),
        )
        self.has_sankey = bool(self.graph.json_data)
        self.send_json()
        self._update_footer_stats()

    def _traversal_cutoff(self) -> float:
        """UI cutoff is percent; Brightway expects a fraction in (0, 1)."""
        return max(min(self.cutoff_sb.value() / 100.0, 0.999), 1e-12)

    @staticmethod
    def _root_uid(data: dict) -> int:
        return next((idx for idx in data.get("nodes", {}) if idx < 0), -1)

    def _sankey_direct_lookup(self, data: dict | None = None):
        data = data or self._full_data
        if not data:
            return None
        meta = data.setdefault("metadata", {})
        directs = meta.get("inventory_directs")
        if directs is None:
            lca = meta.get("lca")
            if lca is None:
                return None
            directs = activity_direct_impacts(lca)
            meta["inventory_directs"] = directs
        if not directs:
            return None
        return inventory_direct_lookup(data["nodes"], directs)

    def _display_uids_for(self, data: dict, *, mode=None, value=None) -> set:
        root = self._root_uid(data)
        score = float(data["metadata"]["lca"].score)
        included, _to_expand = graph_display_set(
            data["nodes"],
            data["edges"],
            mode=mode or self.expand_mode_cb.currentData() or EXPAND_MODE_TIER,
            value=float(self.expand_value_sb.value() if value is None else value),
            total_score=score,
            root_uid=root,
            visited=data.get("opened") or set(data["nodes"]),
            direct_lookup=self._sankey_direct_lookup(data),
        )
        return included

    def _show_sankey_data(
        self, data, method, demand_index, scenario_index, included_uids=None
    ) -> None:
        self._full_data = data
        if included_uids is None:
            self._included_uids = self._display_uids_for(data)
        else:
            valid = set(data.get("nodes") or {})
            self._included_uids = {uid for uid in included_uids if uid in valid}
        self._prefetch_metadata(data)
        self.graph.new_graph(data, included_uids=self._included_uids, **self._graph_style_kwargs())
        self.has_sankey = bool(self.graph.json_data)
        self.update_plot_name("Sankey", method, demand_index, scenario_index)
        self.send_json()
        self._update_footer_stats()

    def _update_footer_stats(self) -> None:
        if not self.graph.json_data:
            self._stats_label.setText("")
            self.show_all_btn.setEnabled(False)
            return
        payload = json.loads(self.graph.json_data)
        m = len(payload.get("edges") or [])
        if not self._full_data:
            n = len(payload.get("nodes") or [])
            self._stats_label.setText(f"Shown: {n} processes, {m} flows")
            self.show_all_btn.setEnabled(False)
            return
        root = self._root_uid(self._full_data)
        score = float(self._full_data["metadata"]["lca"].score)
        stats = unique_process_stats(
            self._full_data["nodes"],
            self._full_data["edges"],
            root,
            score,
            self._included_uids,
            direct_lookup=self._sankey_direct_lookup(),
        )
        calc_part = (
            f"Calculated: {stats['calc_n']} processes, "
            f"{stats['calc_cov'] * 100:.1f}% of direct impacts, "
            f"max tier {stats['calc_tier']}"
        )
        target = self._last_expand_target_pct
        mode = self.expand_mode_cb.currentData()
        if (
            target is not None
            and mode == EXPAND_MODE_CUMULATIVE
            and stats["calc_cov"] * 100.0 + 0.05 < target
        ):
            calc_part += f" (target {target:.0f}% — not reached)"
        self._stats_label.setText(
            f"Shown: {stats['shown_n']} processes, {stats['shown_cov'] * 100:.1f}% of direct impacts, "
            f"max tier {stats['shown_tier']}, {m} flows"
            f"  |  {calc_part}"
        )
        self.show_all_btn.setEnabled(stats["shown_n"] < stats["calc_n"])

    def _on_expand_mode_changed(self) -> None:
        self._apply_expand_mode_defaults(reset_value=True)

    def _apply_expand_mode_defaults(self, *, reset_value: bool) -> None:
        mode = self.expand_mode_cb.currentData()
        self.expand_value_sb.blockSignals(True)
        if mode == EXPAND_MODE_TIER:
            self.expand_value_sb.setDecimals(0)
            self.expand_value_sb.setRange(0, 20)
            self.expand_value_sb.setSingleStep(1)
            self.expand_value_sb.setSuffix("")
            if reset_value:
                self.expand_value_sb.setValue(SANKEY_STARTUP_TIER)
            self.expand_value_sb.setToolTip("Maximum tier to show")
        elif mode == EXPAND_MODE_PATH:
            self.expand_value_sb.setDecimals(1)
            self.expand_value_sb.setRange(0.1, 100.0)
            self.expand_value_sb.setSingleStep(0.5)
            self.expand_value_sb.setSuffix(" %")
            if reset_value:
                self.expand_value_sb.setValue(1.0)
            self.expand_value_sb.setToolTip(
                "Show processes whose path impact is at least this % of total; "
                "siblings below that % are hidden (Show all reveals them)"
            )
        else:
            self.expand_value_sb.setDecimals(0)
            self.expand_value_sb.setRange(1, 99)
            self.expand_value_sb.setSingleStep(1)
            self.expand_value_sb.setSuffix(" %")
            if reset_value:
                self.expand_value_sb.setValue(50)
            self.expand_value_sb.setToolTip(
                "Largest-first remaining upstream until direct-impact coverage reaches this %"
            )
        self.expand_value_sb.blockSignals(False)

    @Slot()
    def _on_adjust_clicked(self) -> None:
        self.new_sankey(apply_adjust=True)

    @Slot()
    def _on_show_all_clicked(self) -> None:
        if not self._full_data:
            return
        root = self._root_uid(self._full_data)
        universe = {uid for uid in self._full_data["nodes"] if uid != root}
        self._included_uids = keep_best_visit_per_activity(
            self._full_data["nodes"],
            self._full_data["edges"],
            universe,
            root,
        )
        self._persist_included_uids()
        self._redraw_sankey_display()

    def _selection_history_key(self) -> tuple:
        return (
            self.func_unit_cb.currentIndex(),
            self.method_cb.currentIndex(),
            self.scenario_cb.currentIndex() if self.has_scenarios else None,
        )

    def _sync_selection_history_buttons(self) -> None:
        self.button_back.setEnabled(self._selection_history.can_back())
        self.button_forward.setEnabled(self._selection_history.can_forward())

    def _seed_selection_history(self) -> None:
        self._selection_history.seed(self._selection_history_key())
        self._sync_selection_history_buttons()

    def _apply_selection_history_key(self, key: tuple) -> None:
        fu_idx, method_idx, scenario_idx = key
        self._suppress_selection = True
        self._selection_history.suppress_push()
        try:
            if 0 <= fu_idx < self.func_unit_cb.count():
                self.func_unit_cb.setCurrentIndex(fu_idx)
            if 0 <= method_idx < self.method_cb.count():
                self.method_cb.setCurrentIndex(method_idx)
            if self.has_scenarios and scenario_idx is not None:
                if 0 <= scenario_idx < self.scenario_cb.count():
                    self.scenario_cb.setCurrentIndex(scenario_idx)
        finally:
            self._suppress_selection = False
            self._selection_history.resume_push()
        self._sync_selection_history_buttons()
        self.new_sankey()

    @Slot()
    def _on_selection_changed(self) -> None:
        if self._suppress_selection:
            return
        self._selection_history.push(self._selection_history_key())
        self._sync_selection_history_buttons()
        self.new_sankey()

    @Slot()
    def _on_selection_back(self) -> None:
        key = self._selection_history.back()
        if key is None:
            return
        self._apply_selection_history_key(key)

    @Slot()
    def _on_selection_forward(self) -> None:
        key = self._selection_history.forward()
        if key is None:
            return
        self._apply_selection_history_key(key)

    @Slot()
    def _export_plot_copy(self) -> None:
        self.view.page().runJavaScript(
            "buildNavigatorSvgExport()", self._on_png_clipboard
        )

    @Slot()
    def _export_plot_png(self) -> None:
        self.view.page().runJavaScript(
            "buildNavigatorSvgExport()", self._on_png_export
        )

    @Slot()
    def _export_plot_svg(self) -> None:
        self.view.page().runJavaScript(
            "buildNavigatorSvgExport()", self._on_svg_export
        )

    def _on_svg_export(self, svg) -> None:
        if svg:
            to_svg(svg, default_file_name=self.plot_name)

    def _on_png_clipboard(self, svg) -> None:
        image = self._sankey_png_image(svg)
        if image is None or image.isNull():
            return
        QtWidgets.QApplication.clipboard().setImage(image)

    def _on_png_export(self, svg) -> None:
        image = self._sankey_png_image(svg)
        if image is None or image.isNull():
            return
        filepath = savefilepath(self.plot_name, file_filter="PNG (*.png)")
        if not filepath:
            return
        if not filepath.lower().endswith(".png"):
            filepath += ".png"
        image.save(filepath, "PNG")

    def _sankey_png_image(self, svg) -> QtGui.QImage | None:
        image = _rasterize_svg(svg) if svg else None
        if image is not None and not image.isNull():
            return image
        pix = self.view.grab()
        return pix.toImage() if pix and not pix.isNull() else None

    def _activities_for_open_process(self, click_dict: dict) -> list:
        """Brightway nodes for **Open process** on a Sankey box."""
        nodes = (self._full_data or {}).get("nodes") or {}
        refs = open_process_refs(
            is_aggregate=bool(click_dict.get("is_aggregate")),
            activity_id=click_dict.get("activity_id"),
            database=click_dict.get("database"),
            code=click_dict.get("code"),
            nodes=nodes,
            uid=click_dict.get("visit_id", click_dict.get("id")),
            constituent_uids=click_dict.get("constituent_uids"),
        )
        return activities_from_open_refs(refs)

    @Slot(object)
    def _on_node_clicked(self, click_dict: dict) -> None:
        if not isinstance(click_dict, dict):
            return
        if click_dict.get("mouse") == 2:
            show_open_process_menu(
                self, self._activities_for_open_process(click_dict)
            )
            return
        if not self._full_data:
            return
        uid = click_dict.get("id")
        try:
            uid = int(uid)
        except (TypeError, ValueError):
            return
        root = self._root_uid(self._full_data)
        current = set(self._included_uids) if self._included_uids else {
            idx for idx in self._full_data["nodes"] if idx != root
        }
        opened = self._full_data.get("opened") or set(self._full_data["nodes"])
        new_included, hop = apply_graph_display_click(
            current,
            self._full_data["nodes"],
            self._full_data["edges"],
            uid,
            opened=opened,
            root_uid=root,
        )
        if hop is not None:
            state = self._full_data.get("state")
            if state is None:
                return
            snap = state.snapshot()
            hops = unopened_same_activity_hops(
                self._full_data["nodes"], uid, opened
            )
            if hop not in hops:
                hops = [hop, *hops]
            progress = self._busy_dialog("Calculating Sankey…")
            try:
                self._busy_tick(progress, "Traversing supply chain…")
                trav = state._trav
                try:
                    trav._should_continue = lambda: not progress.wasCanceled()
                    with suppress_graph_traversal_warnings():
                        for h in hops:
                            if progress.wasCanceled():
                                state.restore(snap)
                                return
                            if h in state.visited_nodes:
                                continue
                            safe_traverse_from_node(state, h, depth=1)
                finally:
                    trav._should_continue = None
                if progress.wasCanceled():
                    state.restore(snap)
                    return
                new_included = include_new_unique_suppliers(
                    current,
                    state.nodes,
                    state.edges,
                    uid,
                    root_uid=root,
                )
                self._full_data["nodes"] = state.nodes
                self._full_data["edges"] = state.edges
                self._full_data["opened"] = set(state.visited_nodes)
                self._prefetch_metadata(self._full_data)
                n_nodes = max(0, len(state.nodes) - 1)
                self._busy_rebuild(progress, n_nodes)
            finally:
                progress.close()
                progress.deleteLater()
        elif new_included == current:
            return
        self._included_uids = new_included
        self._persist_included_uids()
        self.graph.json_data = Graph.get_json_data(
            self._full_data,
            included_uids=self._included_uids,
            preserve_view=True,
            **self._graph_style_kwargs(),
        )
        self.has_sankey = bool(self.graph.json_data)
        self.send_json()
        self._update_footer_stats()


class Graph(widgets.ABAbstractGraph):
    """
    Python side representation of the graph.
    Functionality for graph navigation (e.g. adding and removing nodes).
    A JSON representation of the graph (edges and nodes) enables its use in javascript/html/css.
    """

    def new_graph(
        self,
        data,
        included_uids=None,
        *,
        aggregate_by=None,
        color_by="direct",
        metadata_lookup=None,
    ):
        self.json_data = Graph.get_json_data(
            data,
            included_uids=included_uids,
            aggregate_by=aggregate_by,
            color_by=color_by,
            metadata_lookup=metadata_lookup,
        )
        self.update()

    @staticmethod
    def get_json_data(
        data,
        included_uids=None,
        *,
        aggregate_by=None,
        color_by="direct",
        metadata_lookup=None,
        preserve_view=False,
    ) -> str:
        """JSON for the Sankey web view: ``d3_graph_payload`` plus edge amounts."""
        lca_score = data["metadata"]["lca"].score
        lcia_unit = data["metadata"]["unit"]
        root_uid = next((idx for idx in data.get("nodes", {}) if idx < 0), -1)
        payload = d3_graph_payload(
            data["nodes"],
            data["edges"],
            float(lca_score),
            root_uid=root_uid,
            included_uids=included_uids,
            metadata_lookup=metadata_lookup,
            aggregate_by=aggregate_by,
            color_by=color_by or "direct",
            unit=lcia_unit,
            visited=set(data["nodes"]),
            opened_uids=data.get("opened"),
        )
        overlay_inventory_directs(payload, data["metadata"]["lca"], float(lca_score))
        amounts = mapped_edge_amounts(
            data["nodes"], data["edges"], payload.get("nodes") or []
        )
        by_pair = {
            (edge.producer_unique_id, edge.consumer_unique_id): edge
            for edge in data.get("edges") or []
        }
        lca = data["metadata"]["lca"]
        for rec in payload.get("edges") or []:
            pair = (rec.get("source_id"), rec.get("target_id"))
            orig = by_pair.get((rec.get("producer_unique_id"), rec.get("consumer_unique_id")))
            if orig is None:
                orig = by_pair.get(pair)
            if orig is not None:
                rec["amount"] = orig.amount
            elif pair in amounts:
                rec["amount"] = amounts[pair]
            rec.setdefault("amount_unit", "")
            if orig is not None and not rec.get("product"):
                rec["product"] = _flow_product_name_from_edge(
                    lca, orig, metadata_lookup=metadata_lookup
                )
        if preserve_view:
            payload["preserve_view"] = True
        return json.dumps(payload)


def _rasterize_svg(svg: str) -> QtGui.QImage | None:
    """Turn SVG markup into a PNG-ready QImage. None if QtSvg is unavailable."""
    if not svg:
        return None
    try:
        from qtpy.QtSvg import QSvgRenderer
    except ImportError:
        return None
    renderer = QSvgRenderer(QtCore.QByteArray(svg.encode("utf-8")))
    if not renderer.isValid():
        return None
    size = renderer.defaultSize()
    if size.width() < 1 or size.height() < 1:
        size = QtCore.QSize(1200, 800)
    image = QtGui.QImage(size.width() * 2, size.height() * 2, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))
    painter = QtGui.QPainter(image)
    try:
        renderer.render(painter)
    finally:
        painter.end()
    return image
