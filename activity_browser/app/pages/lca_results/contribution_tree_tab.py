"""Contribution Tree tab for the LCA Results page.

Shows the contribution tree as a hierarchical table with an optional contribution-tree plot.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import bw2data as bd
import bw2calc as bc
from loguru import logger
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Slot

from bw_graph_tools.graph_traversal import (
    SameNodeEachVisitGraphTraversal,
    GraphTraversalSettings,
)

from activity_browser import app
from activity_browser.bwutils.graph_traversal.engine import (
    PLOT_AGGREGATE_FIELDS,
    PLOT_AGGREGATE_LABELS,
    activity_metadata_for_ids,
    activities_from_open_refs,
    compute_node_tiers,
    d3_graph_payload,
    direct_impact_coverage,
    is_terminal_node,
    open_process_refs,
    run_expand_policy,
    suppress_graph_traversal_warnings,
)
from activity_browser.bwutils.graph_traversal.partition_plots import (
    build_plot_segments,
    d3_plot_payload,
    plot_click_target_uid,
)
from activity_browser.bwutils.lca_inputs import demand_database_names, prepared_lca_inputs
from activity_browser.bwutils.export_names import lca_export_basename
from activity_browser.ui.delegates.impact_background import ImpactBackgroundDelegate
from activity_browser.ui.icons import qicons
from activity_browser.ui.selection_history import IndexSelectionHistory

from .combobox_utils import configure_scenario_widgets, scenario_labels, update_combobox
from .contribution_tree_model import (
    BAR_COLUMNS,
    COL_CUMULATIVE,
    COL_CUMULATIVE_PCT,
    COL_DIRECT,
    COL_DIRECT_PCT,
    COL_PROCESS,
    EXPAND_MODE_CUMULATIVE,
    EXPAND_MODE_PATH,
    EXPAND_MODE_TIER,
    TIER_ROLE,
    UID_ROLE,
    ContributionTreeModel,
)
from .contribution_tree_d3_plot import ContributionTreeD3Plot
from .contribution_tree_plot import (
    PLOT_GRAPH,
    PLOT_MODES,
)
from .style import (
    SmallComboBox,
    apply_lca_combo_width,
    configure_lca_tab_layout,
    lca_header_layout,
    lca_help_tool_button,
    lca_run_button,
    lca_tab_control_row,
    show_open_process_menu,
)

HELP_TEXT = """
<html><body>
<p><b>Tree</b> shows supply-chain impact for one reference flow, impact
category, and scenario. Back/Forward are selection history. Each row is a
process on a supply path (SNEV); the plot matches the visible table.</p>
<p><b>Legend</b>
<ul>
  <li><i>Flows</i>: red = path impact (green = avoided).</li>
  <li><i>Processes</i>: blue = direct impact (green = benefit, white = none).</li>
  <li><i>Triangles</i>: expand or collapse that process.</li>
</ul></p>
<p><b>Table</b> — <i>Cumulative %</i> is path impact; <i>Direct %</i> is
characterised emissions at that process. Tier&nbsp;0 is the reference flow;
tier&nbsp;1 its suppliers. Expand a row to calculate its suppliers.</p>
<p><b>Adjust to</b> — <b>Tier</b> opens to a chosen tier.
<b>Individual path impact</b> opens nodes at/above the threshold (siblings
below that % are hidden; a terminal node stays collapsed until you expand it).
<b>Cumulative impact</b> opens the largest paths until visible direct impact
hits the target. Stop keeps the tree calculated so far.
<b>Show all</b> (footer) draws every calculated node.</p>
<p><b>Cutoff</b> prunes branches below this share of the total score.</p>
<p><b>Plot</b> — Tree is a node-link view of the table. Click a box or
triangle to expand/collapse. Right-click <b>Open process</b> opens Activity
Details (same as the table). <b>Aggregate by</b> rolls up siblings in the
plot; <b>Color by</b> tints without merging.</p>
<p><b>Footer</b> — Shown: visible rows. Calculated: traversal so far.</p>
</body></html>
"""


# ---------------------------------------------------------------------------
# Per-selection cache (RF / IC / scenario / cutoff)
# ---------------------------------------------------------------------------

@dataclass
class ContributionTreeCacheEntry:
    """Cached graph plus the Qt tree view snapshot for one selection.

    ``model_uids`` is the set of rows that were in the tree (e.g. after path
    prune). ``None`` means unrestricted — use whatever ``load_state`` builds.
    """

    state: SameNodeEachVisitGraphTraversal
    expanded_uids: set[int] = field(default_factory=set)
    model_uids: set[int] | None = None


# ---------------------------------------------------------------------------
# Per-selection cache entry lives above; tab widget below.
# ---------------------------------------------------------------------------

class ContributionTreeTab(QtWidgets.QWidget):
    """Contribution Tree tab for the LCA Results page.

    Shows a QTreeView (lazy, expandable by tier) with an optional contribution-tree plot.
    Cache key: (fu_index, method_index, scenario_index, cutoff_percent).
    Each entry stores the Brightway traversal and the set of expanded row uids
    so switching RF / IC / scenario restores both calculation and open branches.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.has_scenarios: bool = getattr(parent, "has_scenarios", False)

        # State
        self._cache: dict[tuple, ContributionTreeCacheEntry] = {}
        self._active_cache_key: tuple | None = None
        self._current_state: Optional[SameNodeEachVisitGraphTraversal] = None
        self._cached_lca: Optional[bc.LCA] = None
        self._cached_lca_scope: frozenset[str] | None = None
        self._lca_selection_key: tuple | None = None
        self.has_been_opened: bool = False
        self.plot_name: str = "Contribution Tree"
        # Skip lazy-fetch / leaf-collapse while applying Expand-to view state
        self._suppress_expand_handler: bool = False
        self._view_refresh_pending: bool = False

        # --- Controls ---
        self.fu_cb = SmallComboBox()
        self.method_cb = SmallComboBox()
        self.scenario_cb = SmallComboBox()
        self.scenario_label = QtWidgets.QLabel("Scenario:")

        # Graph-traversal cutoff as percent of total score (Brightway needs (0, 1))
        self.cutoff_sb = QtWidgets.QDoubleSpinBox()
        self.cutoff_sb.setRange(0.001, 99.0)
        self.cutoff_sb.setDecimals(3)
        self.cutoff_sb.setSingleStep(0.01)
        self.cutoff_sb.setValue(0.1)
        self.cutoff_sb.setSuffix(" %")
        self.cutoff_sb.setKeyboardTracking(False)
        self.cutoff_sb.setToolTip(
            "Graph traversal cutoff: prune branches whose cumulative impact "
            "is below this percent of the total LCA score"
        )

        self.plot_type_cb = SmallComboBox()
        for mode_id, label in PLOT_MODES:
            self.plot_type_cb.addItem(label, mode_id)
        for i in range(self.plot_type_cb.count()):
            if self.plot_type_cb.itemData(i) == PLOT_GRAPH:
                self.plot_type_cb.setCurrentIndex(i)
                break
        self.plot_type_cb.setToolTip("Contribution tree visualization type")

        self.aggregate_by_cb = SmallComboBox()
        self.aggregate_by_cb.addItem("None", None)
        for field in PLOT_AGGREGATE_FIELDS:
            self.aggregate_by_cb.addItem(PLOT_AGGREGATE_LABELS[field], field)
        self.aggregate_by_cb.setToolTip(
            "Roll up sibling plot segments by metadata (plot only; table unchanged)"
        )

        self.color_by_cb = SmallComboBox()
        self.color_by_cb.addItem("Direct impact", "direct")
        self.color_by_cb.addItem("Product", "product")
        self.color_by_cb.addItem("Process", "process")
        self.color_by_cb.addItem("Location", "location")
        self.color_by_cb.addItem("Database", "database")
        self.color_by_cb.setToolTip(
            "Tint plot boxes/segments (plot only). Ribbons stay red/green by path impact."
        )

        self.expand_mode_cb = SmallComboBox()
        self.expand_mode_cb.addItem("Tier", EXPAND_MODE_TIER)
        self.expand_mode_cb.addItem("Individual path impact", EXPAND_MODE_PATH)
        self.expand_mode_cb.addItem("Cumulative impact", EXPAND_MODE_CUMULATIVE)
        self.expand_mode_cb.setToolTip("How far Adjust calculates and opens the tree")

        self.expand_value_sb = QtWidgets.QDoubleSpinBox()
        self.expand_value_sb.setKeyboardTracking(False)
        self.expand_btn = lca_run_button(self, text="Adjust")
        self.expand_btn.setToolTip("Calculate and open branches according to the adjust policy")

        self.show_plot_cb = QtWidgets.QCheckBox("Plot")
        self.show_plot_cb.setChecked(True)
        self.show_table_cb = QtWidgets.QCheckBox("Table")
        self.show_table_cb.setChecked(True)
        self._last_expand_target_pct: float | None = None

        # Export buttons
        self.export_table_btn = QtWidgets.QPushButton("Export table…")
        self.export_plot_btn = QtWidgets.QPushButton("Export plot…")

        self._selection_history = IndexSelectionHistory()
        self._suppress_selection = False
        self.button_back = QtWidgets.QPushButton(qicons.backward, "")
        self.button_forward = QtWidgets.QPushButton(qicons.forward, "")
        self.button_back.setToolTip("Previous reference flow, impact category, or scenario")
        self.button_forward.setToolTip("Next reference flow, impact category, or scenario")
        self.button_back.setEnabled(False)
        self.button_forward.setEnabled(False)

        self._stats_label = QtWidgets.QLabel("")
        self._stats_label.setToolTip(
            "Shown = visible rows / Direct impact (%) sum / deepest visible tier. "
            "Calculated = traversal nodes / their coverage / deepest calculated tier."
        )
        self.show_all_btn = QtWidgets.QPushButton("Show all")
        self.show_all_btn.setToolTip(
            "Show every calculated node in the table and graph (Adjust may have hidden some)."
        )
        self.show_all_btn.setEnabled(False)
        # --- Tree view ---
        self._tree_model = ContributionTreeModel(self)
        self._tree_view = QtWidgets.QTreeView()
        self._tree_view.setModel(self._tree_model)
        self._tree_view.setUniformRowHeights(False)
        self._tree_view.setAlternatingRowColors(True)
        self._tree_view.setSortingEnabled(False)
        self._tree_view.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._tree_view.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self._tree_view.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._tree_view.header().setStretchLastSection(False)
        self._tree_view.header().setSectionResizeMode(COL_PROCESS, QtWidgets.QHeaderView.Stretch)

        # Impact-tint delegates: red = cumulative, blue = direct (% and absolute)
        self._delegates: dict[int, ImpactBackgroundDelegate] = {
            COL_CUMULATIVE_PCT: ImpactBackgroundDelegate(
                column_max=100.0,
                positive_rgb=(210, 85, 85),
                parent=self._tree_view,
            ),
            COL_DIRECT_PCT: ImpactBackgroundDelegate(
                column_max=100.0,
                positive_rgb=(70, 130, 210),
                parent=self._tree_view,
            ),
            COL_CUMULATIVE: ImpactBackgroundDelegate(
                column_max=1.0,
                positive_rgb=(210, 85, 85),
                parent=self._tree_view,
            ),
            COL_DIRECT: ImpactBackgroundDelegate(
                column_max=1.0,
                positive_rgb=(70, 130, 210),
                parent=self._tree_view,
            ),
        }
        for col, d in self._delegates.items():
            self._tree_view.setItemDelegateForColumn(col, d)

        self._d3_plot = ContributionTreeD3Plot(self)
        self._d3_plot.setMinimumHeight(180)
        self._d3_plot.set_segment_click_handler(self._on_plot_segment_clicked)
        self._d3_plot.set_segment_context_handler(self._on_plot_segment_context)

        self._tree_view.setMinimumHeight(120)

        # --- Splitter ---
        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self._splitter.addWidget(self._d3_plot)
        self._splitter.addWidget(self._tree_view)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 2)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.splitterMoved.connect(self._on_splitter_moved)

        self._build_layout()
        self._connect_signals()
        self._apply_expand_mode_defaults(reset_value=True)
        self._update_calculation_setup()
        QtCore.QTimer.singleShot(0, self._update_view_visibility)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        QtCore.QTimer.singleShot(0, self._apply_splitter_sizes)

    # ------------------------------------------------------------------
    # Plot / table visibility
    # ------------------------------------------------------------------

    @Slot()
    def _update_view_visibility(self, *_args) -> None:
        """Show or hide plot/table and redistribute splitter space."""
        show_plot = self.show_plot_cb.isChecked()
        show_table = self.show_table_cb.isChecked()
        was_hidden = not self._d3_plot.isVisible()
        self._d3_plot.setVisible(show_plot)
        self._tree_view.setVisible(show_table)
        if show_plot and was_hidden and self._current_state is not None:
            self._reload_plot()
        QtCore.QTimer.singleShot(0, self._apply_splitter_sizes)

    def _apply_splitter_sizes(self) -> None:
        show_plot = self.show_plot_cb.isChecked()
        show_table = self.show_table_cb.isChecked()
        if show_plot and show_table:
            self._splitter.setStretchFactor(0, 1)
            self._splitter.setStretchFactor(1, 2)
            total = max(self._splitter.height(), 1)
            plot_h = max(total // 3, self._d3_plot.minimumHeight())
            table_h = max(total - plot_h, self._tree_view.minimumHeight())
            self._splitter.setSizes([plot_h, table_h])
        else:
            self._splitter.setStretchFactor(0, 1 if show_plot else 0)
            self._splitter.setStretchFactor(1, 1 if show_table else 0)
        self._notify_plot_resized(reset_zoom=True)
        if show_plot:
            QtCore.QTimer.singleShot(0, lambda: self._notify_plot_resized(reset_zoom=True))
            QtCore.QTimer.singleShot(50, lambda: self._notify_plot_resized(reset_zoom=False))

    def _on_splitter_moved(self, *_args) -> None:
        self._notify_plot_resized(reset_zoom=False)

    def _notify_plot_resized(self, *, reset_zoom: bool = False) -> None:
        if not self.show_plot_cb.isChecked():
            return
        self._d3_plot.notify_viewport(
            reset_zoom=reset_zoom,
            force=True,
        )

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        main = QtWidgets.QVBoxLayout(self)
        configure_lca_tab_layout(main)

        # Header + help
        help_btn = lca_help_tool_button(
            self,
            "Left click for help on the Tree tab",
            self._show_help,
        )
        main.addLayout(lca_header_layout("Tree", help_btn))

        # Control row 1: FU / method / scenario (left-aligned like other LCA tabs)
        row1 = lca_tab_control_row()
        row1.addWidget(QtWidgets.QLabel("Reference flow:"))
        row1.addWidget(self.fu_cb)
        row1.addWidget(QtWidgets.QLabel("Impact category:"))
        row1.addWidget(self.method_cb)
        row1.addWidget(self.scenario_label)
        row1.addWidget(self.scenario_cb)
        row1.addWidget(self.button_back)
        row1.addWidget(self.button_forward)
        row1.addStretch(1)
        main.addLayout(row1)

        # Control row 2: plot/table, cutoff, adjust, plot type, aggregate/color
        row2 = lca_tab_control_row()
        row2.addWidget(self.show_plot_cb)
        row2.addWidget(self.show_table_cb)
        row2.addSpacing(12)
        row2.addWidget(QtWidgets.QLabel("Cutoff:"))
        row2.addWidget(self.cutoff_sb)
        row2.addSpacing(12)
        row2.addWidget(QtWidgets.QLabel("Adjust to:"))
        row2.addWidget(self.expand_mode_cb)
        row2.addWidget(self.expand_value_sb)
        row2.addWidget(self.expand_btn)
        row2.addSpacing(12)
        row2.addWidget(QtWidgets.QLabel("Plot:"))
        row2.addWidget(self.plot_type_cb)
        row2.addSpacing(12)
        row2.addWidget(QtWidgets.QLabel("Aggregate by:"))
        row2.addWidget(self.aggregate_by_cb)
        row2.addWidget(QtWidgets.QLabel("Color by:"))
        row2.addWidget(self.color_by_cb)
        row2.addStretch(1)
        main.addLayout(row2)

        # Splitter (plot + tree)
        main.addWidget(self._splitter, 1)

        # Footer: stats + export
        footer = QtWidgets.QHBoxLayout()
        footer.addWidget(self._stats_label)
        footer.addWidget(self.show_all_btn)
        footer.addStretch(1)
        footer.addWidget(self.export_table_btn)
        footer.addWidget(self.export_plot_btn)
        main.addLayout(footer)

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self.fu_cb.currentIndexChanged.connect(self._on_selection_changed)
        self.method_cb.currentIndexChanged.connect(self._on_selection_changed)
        self.scenario_cb.currentIndexChanged.connect(self._on_selection_changed)
        self.button_back.clicked.connect(self._on_selection_back)
        self.button_forward.clicked.connect(self._on_selection_forward)
        self.cutoff_sb.valueChanged.connect(self._on_cutoff_changed)
        self.plot_type_cb.currentIndexChanged.connect(self._on_plot_type_changed)
        self.aggregate_by_cb.currentIndexChanged.connect(self._on_aggregate_by_changed)
        self.color_by_cb.currentIndexChanged.connect(self._on_color_by_changed)
        self.expand_mode_cb.currentIndexChanged.connect(self._on_expand_mode_changed)
        self.expand_btn.clicked.connect(self._on_expand_clicked)
        self.show_all_btn.clicked.connect(self._on_show_all_clicked)
        self.show_plot_cb.toggled.connect(self._update_view_visibility)
        self.show_table_cb.toggled.connect(self._update_view_visibility)
        # Queued so model mutations do not run inside QTreeView's expand stack
        # (synchronous removeRow/appendRow there causes access violations on Windows).
        self._tree_view.expanded.connect(
            self._on_row_expanded, QtCore.Qt.ConnectionType.QueuedConnection
        )
        self._tree_view.collapsed.connect(self._on_row_collapsed)
        self._tree_view.customContextMenuRequested.connect(self._on_tree_context_menu)
        self._tree_model.column_max_changed.connect(self._update_delegate_maxima)
        self.export_table_btn.clicked.connect(self._export_table)
        self.export_plot_btn.clicked.connect(self._export_plot)
        app.application.theme_changed.connect(self.update_tab)

    # ------------------------------------------------------------------
    # Calculation-setup population
    # ------------------------------------------------------------------

    def update_tab(self) -> None:
        """Called when the tab is shown or the theme changes.

        Guarded by ``has_been_opened`` so the generic ``_update_tabs`` loop
        in ``LCAResultsPage`` does not trigger a traversal at construction
        time (same pattern as Sankey / Tree Navigator).
        ``has_been_opened`` is set to True by ``LCAResultsPage.generate_content_on_click``
        before this method is called on first open.
        """
        if not self.has_been_opened:
            return
        if self._current_state is None:
            self._run_traversal()
        else:
            self._save_view_snapshot()
            uids = None
            model_uids = None
            if self._active_cache_key is not None and self._active_cache_key in self._cache:
                entry = self._cache[self._active_cache_key]
                uids = entry.expanded_uids
                model_uids = entry.model_uids
            self._reload_from_state(expanded_uids=uids, model_uids=model_uids)

    def configure_scenario(self) -> None:
        configure_scenario_widgets(
            has_scenarios=self.has_scenarios,
            scenario_box=self.scenario_cb,
            scenario_label=self.scenario_label,
            parent=self.parent,
        )

    update_combobox = staticmethod(update_combobox)

    def _update_calculation_setup(self, cs_name: str = None) -> None:
        for w in (self.fu_cb, self.method_cb, self.scenario_cb):
            w.blockSignals(True)

        cs = cs_name or (self.parent.cs_name if self.parent else None)
        if cs is None:
            for w in (self.fu_cb, self.method_cb, self.scenario_cb):
                w.blockSignals(False)
            return

        setup = bd.calculation_setups.get(cs, {})
        fu_acts = [
            list({bd.get_activity(k): v for k, v in fu.items()}.keys())[0]
            for fu in setup.get("inv", [])
        ]
        self.fu_cb.clear()
        self.fu_cb.addItems([f"{repr(a)} | {a._data.get('database')}" for a in fu_acts])
        self.method_cb.clear()
        self.method_cb.addItems([repr(m) for m in setup.get("ia", [])])
        self.configure_scenario()

        for w in (self.fu_cb, self.method_cb, self.scenario_cb):
            w.blockSignals(False)
        self._seed_selection_history()

    # ------------------------------------------------------------------
    # Cache key
    # ------------------------------------------------------------------

    def _cache_key(self) -> tuple:
        return (
            self.fu_cb.currentIndex(),
            self.method_cb.currentIndex(),
            self.scenario_cb.currentIndex() if self.has_scenarios else None,
            round(self.cutoff_sb.value(), 6),
        )

    def _traversal_cutoff(self) -> float:
        """UI cutoff is percent; Brightway expects a fraction in (0, 1)."""
        return max(min(self.cutoff_sb.value() / 100.0, 0.999), 1e-12)

    def _selection_inputs(self, key: tuple):
        """Resolve demand dict and method tuple for a cache key."""

        fu_idx, method_idx, scenario_idx, _cutoff_pct = key
        cs = self.parent.cs_name
        setup = bd.calculation_setups[cs]
        demand_raw = setup["inv"][fu_idx]
        method = setup["ia"][method_idx]
        demand = {bd.get_activity(k).id: v for k, v in demand_raw.items()}
        return demand, method, scenario_idx

    def _ensure_lca(
        self,
        demand: dict,
        method,
        scenario_idx,
        method_idx: int | None = None,
        *,
        selection_key: tuple | None = None,
    ) -> None:
        """Keep the shared LCA object in sync with the current RF/method/scenario.

        Demand is mapped to product keys (``functional_sqlite`` process ids are
        not in the product dictionary). Switching RF without ``redo_lci``
        leaves ``state.lca.score`` belonging to another demand. If the demand
        databases change (e.g. ecoinvent → a small circular db), the cached
        LCA is rebuilt so ``redo_lci`` cannot raise ``OutsideTechnosphere``.

        Cached tree/plot scores live on the traversal nodes; restore skips this.
        Call before any further ``traverse_from_node`` / Adjust.
        ``selection_key`` is ``(fu_idx, method_idx, scenario_idx)`` so a no-op
        when the shared LCA is already that selection.
        """

        if (
            selection_key is not None
            and selection_key == self._lca_selection_key
            and self._cached_lca is not None
        ):
            return

        if self.has_scenarios and scenario_idx is not None:
            mi = method_idx if method_idx is not None else self.method_cb.currentIndex()
            self.parent.mlca.update_lca_calculation_for_sankey(
                scenario_idx, demand, mi
            )

        fu_input, data_objs, _ = prepared_lca_inputs(demand, method)
        scope = demand_database_names(demand)
        if self._cached_lca is None or self._cached_lca_scope != scope:
            self._cached_lca = bc.LCA(demand=fu_input, data_objs=data_objs)
            self._cached_lca.lci(factorize=True)
            self._cached_lca.lcia()
            self._cached_lca_scope = scope
        else:
            self._cached_lca.redo_lci(fu_input)
            self._cached_lca.switch_method(method)
            self._cached_lca.lcia()
        self._lca_selection_key = selection_key

    def _sync_lca_to_current_selection(self) -> None:
        """Solve LCI/LCIA for the combobox selection (needed before traverse)."""
        key = self._cache_key()
        demand, method, scenario_idx = self._selection_inputs(key)
        self._ensure_lca(
            demand, method, scenario_idx, key[1], selection_key=key[:3]
        )

    @staticmethod
    def _state_total_score(state: SameNodeEachVisitGraphTraversal) -> float:
        meta = getattr(state, "metadata", None) or {}
        if "total_score" in meta:
            return float(meta["total_score"])
        return float(state.lca.score)

    @staticmethod
    def _store_total_score(state: SameNodeEachVisitGraphTraversal) -> None:
        if state.metadata is None:
            state.metadata = {}
        state.metadata["total_score"] = float(state.lca.score)

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    def _busy_dialog(self, label: str) -> QtWidgets.QProgressDialog:
        """Indeterminate busy spinner with a Stop button (range 0–0)."""
        progress = QtWidgets.QProgressDialog(label, "Stop", 0, 0, self)
        progress.setWindowTitle("Contribution Tree")
        # Window-modal: Stop stays clickable; the rest of the app is blocked.
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
        """Pump the event loop so Stop can be clicked. Return False if stopped."""
        if label is not None:
            progress.setLabelText(label)
        QtWidgets.QApplication.processEvents()
        return not progress.wasCanceled()

    def _busy_rebuild(self, progress: QtWidgets.QProgressDialog, n_nodes: int | None = None) -> None:
        """Hide Stop and keep the dialog while the table and plot are built."""
        if progress.wasCanceled():
            progress.reset()
            progress.setRange(0, 0)
        progress.setCancelButton(None)
        label = "Building table and plot…"
        if n_nodes:
            label = f"{label} ({n_nodes} nodes)"
        self._busy_tick(progress, label)

    def _run_traversal(self) -> None:
        key = self._cache_key()
        if key in self._cache:
            logger.debug(f"Contribution tree cache hit: {key}")
            # Node scores are already on the cached graph. Do not redo LCI here
            # (Sankey cache-hit path). Sync the shared LCA on the next traverse.
            entry = self._cache[key]
            self._active_cache_key = key
            self._current_state = entry.state
            self._reload_from_state(
                expanded_uids=entry.expanded_uids,
                model_uids=entry.model_uids,
            )
            return

        logger.debug(f"Contribution tree traversal start: {key}")
        _, method, _ = self._selection_inputs(key)
        progress = self._busy_dialog("Calculating contribution tree…")

        try:
            self._busy_tick(progress, "Running LCI / LCIA…")
            self._sync_lca_to_current_selection()
            if progress.wasCanceled():
                return

            self._busy_tick(progress, "Traversing supply chain…")
            t0 = time.time()
            state = SameNodeEachVisitGraphTraversal(
                lca=self._cached_lca,
                settings=GraphTraversalSettings(cutoff=self._traversal_cutoff()),
            )
            with suppress_graph_traversal_warnings():
                state.traverse(depth=2)
            state.metadata = {"unit": bd.methods[method].get("unit", "")}
            self._store_total_score(state)
            logger.debug(f"Traversal done in {time.time()-t0:.2f}s")

            self._cache[key] = ContributionTreeCacheEntry(state=state)
            self._active_cache_key = key
            self._current_state = state
            self._last_expand_target_pct = None
            n_nodes = sum(1 for uid in state.nodes if uid >= 0)
            self._busy_rebuild(progress, n_nodes)
            self._reload_from_state(expanded_uids=None, model_uids=None)
            self._save_view_snapshot()

        except Exception as exc:
            logger.exception("Contribution tree traversal failed")
            QtWidgets.QMessageBox.warning(
                self,
                "Contribution Tree",
                f"Traversal failed: {exc}",
            )
        finally:
            progress.close()
            progress.deleteLater()

    def _reload_from_state(
        self,
        expanded_uids: set[int] | None = None,
        model_uids: set[int] | None = None,
    ) -> None:
        """Rebuild the tree model and plot from the current cached state.

        ``model_uids`` restores a filtered model (e.g. after path prune).
        ``expanded_uids`` restores which branches were open.
        """
        state = self._current_state
        if state is None:
            return
        total = self._state_total_score(state)
        self._tree_view.setUpdatesEnabled(False)
        try:
            self._tree_model.load_state(state, total, included_uids=model_uids)
            self._update_delegate_maxima()
            self._tree_view.collapseAll()
            if expanded_uids:
                self._restore_expanded_uids(expanded_uids)
            if self.show_plot_cb.isChecked():
                self._reload_plot()
            self._update_footer_stats()
        finally:
            self._tree_view.setUpdatesEnabled(True)
            self._tree_view.viewport().update()
        QtCore.QTimer.singleShot(0, self._apply_splitter_sizes)
        QtCore.QTimer.singleShot(0, self._fit_cumulative_column)

    def _collect_expanded_uids(self) -> set[int]:
        """Return unique_ids of rows currently expanded in the tree view."""
        expanded: set[int] = set()
        for uid, item in self._tree_model.iter_uid_items():
            idx = self._tree_model.indexFromItem(item)
            if idx.isValid() and self._tree_view.isExpanded(idx):
                expanded.add(uid)
        return expanded

    def _release_expand_handler(self) -> None:
        """Unblock expand slots after queued ``expanded`` signals from a restore."""
        self._suppress_expand_handler = False

    def _restore_expanded_uids(self, uids: set[int]) -> None:
        """Open cached branches (parents before children). Skips missing uids."""
        if not uids:
            return
        self._suppress_expand_handler = True
        try:
            to_expand: list[tuple[int, QtGui.QStandardItem]] = []
            for uid in uids:
                item = self._tree_model.item_for_uid(uid)
                if item is None or not self._tree_model.has_real_children(item):
                    continue
                to_expand.append((int(item.data(TIER_ROLE) or 0), item))
            to_expand.sort(key=lambda pair: pair[0])
            for _, item in to_expand:
                idx = self._tree_model.indexFromItem(item)
                if idx.isValid():
                    self._tree_view.expand(idx)
        finally:
            QtCore.QTimer.singleShot(0, self._release_expand_handler)

    def _save_view_snapshot(self) -> None:
        """Persist model rows + expanded branches for the active cache key."""
        key = self._active_cache_key
        if key is None or key not in self._cache:
            return
        entry = self._cache[key]
        entry.expanded_uids = self._collect_expanded_uids()
        entry.model_uids = self._tree_model.model_uids()

    # ------------------------------------------------------------------
    # Slot handlers
    # ------------------------------------------------------------------

    def _selection_history_key(self) -> tuple:
        return (
            self.fu_cb.currentIndex(),
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
            if 0 <= fu_idx < self.fu_cb.count():
                self.fu_cb.setCurrentIndex(fu_idx)
            if 0 <= method_idx < self.method_cb.count():
                self.method_cb.setCurrentIndex(method_idx)
            if self.has_scenarios and scenario_idx is not None:
                if 0 <= scenario_idx < self.scenario_cb.count():
                    self.scenario_cb.setCurrentIndex(scenario_idx)
        finally:
            self._suppress_selection = False
            self._selection_history.resume_push()
        self._sync_selection_history_buttons()
        self._save_view_snapshot()
        self._current_state = None
        self._active_cache_key = None
        self._run_traversal()

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
    def _on_selection_changed(self) -> None:
        if self._suppress_selection:
            return
        self._selection_history.push(self._selection_history_key())
        self._sync_selection_history_buttons()
        self._save_view_snapshot()
        self._current_state = None
        self._active_cache_key = None
        self._run_traversal()

    @Slot()
    def _on_cutoff_changed(self) -> None:
        self._save_view_snapshot()
        self._current_state = None
        self._active_cache_key = None
        self._run_traversal()

    @Slot()
    def _on_plot_type_changed(self) -> None:
        if self.show_plot_cb.isChecked() and self._current_state is not None:
            self._reload_plot()

    @Slot()
    def _on_color_by_changed(self) -> None:
        if self._current_state is not None:
            self._reload_plot()

    @Slot()
    def _on_aggregate_by_changed(self) -> None:
        self._reload_plot()

    @Slot(object)
    def _on_plot_segment_context(self, payload: dict) -> None:
        """Right-click Open process on a plot box or segment."""
        if not isinstance(payload, dict):
            return
        uid = payload.get("visit_id", payload.get("unique_id"))
        try:
            uid = int(uid)
        except (TypeError, ValueError):
            uid = None
        if uid is not None and not payload.get("is_aggregate"):
            self._select_tree_row(uid)
        nodes = getattr(self._current_state, "nodes", None) or {}
        refs = open_process_refs(
            is_aggregate=bool(payload.get("is_aggregate")),
            activity_id=payload.get("activity_id"),
            database=payload.get("database"),
            code=payload.get("code"),
            nodes=nodes,
            uid=uid,
            constituent_uids=payload.get("constituent_uids"),
        )
        activities = activities_from_open_refs(refs)
        show_open_process_menu(self._d3_plot, activities)

    @Slot()
    def _on_plot_segment_clicked(self, segment: dict) -> None:
        """Expand/collapse tree branch from plot click; select matching row."""
        if self._current_state is None:
            return
        uid = plot_click_target_uid(segment)
        state = self._current_state
        if is_terminal_node(state.nodes, state.edges, state.visited_nodes, uid):
            self._expand_tree_node_only(uid)
        else:
            self._toggle_tree_node(uid)

    def _select_tree_row(self, uid: int) -> QtCore.QModelIndex | None:
        item = self._tree_model.item_for_uid(uid)
        if item is None:
            return None
        idx = self._tree_model.indexFromItem(item)
        if not idx.isValid():
            return None
        sm = self._tree_view.selectionModel()
        if sm is not None:
            sm.select(
                idx,
                QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect
                | QtCore.QItemSelectionModel.SelectionFlag.Rows,
            )
        self._tree_view.scrollTo(
            idx,
            QtWidgets.QAbstractItemView.ScrollHint.PositionAtCenter,
        )
        return idx

    def _expand_tree_node_only(self, uid: int) -> None:
        """Expand-only (terminal segments): traverse once; never collapse from plot."""
        idx = self._select_tree_row(uid)
        if idx is None or not idx.isValid():
            return
        if not self._tree_view.isExpanded(idx):
            self._tree_view.expand(idx)

    def _toggle_tree_node(self, uid: int) -> None:
        idx = self._select_tree_row(uid)
        if idx is None or not idx.isValid():
            return
        if self._tree_view.isExpanded(idx):
            self._tree_view.collapse(idx)
        else:
            self._tree_view.expand(idx)

    @Slot()
    def _on_expand_mode_changed(self) -> None:
        self._apply_expand_mode_defaults(reset_value=True)

    def _apply_expand_mode_defaults(self, *, reset_value: bool) -> None:
        mode = self.expand_mode_cb.currentData()
        self.expand_value_sb.blockSignals(True)
        if mode == EXPAND_MODE_TIER:
            self.expand_value_sb.setDecimals(0)
            self.expand_value_sb.setRange(1, 20)
            self.expand_value_sb.setSingleStep(1)
            self.expand_value_sb.setSuffix("")
            if reset_value:
                self.expand_value_sb.setValue(3)
            self.expand_value_sb.setToolTip("Maximum tier to open")
        elif mode == EXPAND_MODE_PATH:
            self.expand_value_sb.setDecimals(1)
            self.expand_value_sb.setRange(0.1, 100.0)
            self.expand_value_sb.setSingleStep(0.5)
            self.expand_value_sb.setSuffix(" %")
            if reset_value:
                self.expand_value_sb.setValue(1.0)
            self.expand_value_sb.setToolTip(
                "Auto-expand nodes whose path impact is at least this % of total; "
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
                "Largest-first expand until direct-impact coverage reaches this % (max 99)"
            )
        self.expand_value_sb.blockSignals(False)

    @Slot()
    def _on_expand_clicked(self) -> None:
        if self._current_state is None:
            return
        mode = self.expand_mode_cb.currentData()
        value = float(self.expand_value_sb.value())
        state = self._current_state
        self._sync_lca_to_current_selection()
        self._store_total_score(state)
        total = self._state_total_score(state)

        progress = self._busy_dialog("Adjusting contribution tree…")
        self._last_expand_target_pct = (
            value if mode in (EXPAND_MODE_PATH, EXPAND_MODE_CUMULATIVE) else None
        )
        try:
            def _tick(step, n_nodes):
                label = (
                    f"Traversing supply chain… ({n_nodes} nodes)"
                    if step % 10 == 0
                    else None
                )
                return self._busy_tick(progress, label)

            self._busy_tick(progress, "Traversing supply chain…")
            included, to_expand = run_expand_policy(
                state,
                mode=mode,
                value=value,
                total_score=total,
                on_progress=_tick,
            )
            self._busy_rebuild(progress, sum(1 for uid in state.nodes if uid >= 0))

            self._tree_view.setUpdatesEnabled(False)
            try:
                self._tree_model.load_state(state, total, included_uids=included)
                self._update_delegate_maxima()
                if mode == EXPAND_MODE_TIER:
                    self._apply_expand_view_state(max_tier=int(value))
                elif to_expand is not None:
                    self._restore_expanded_uids(to_expand)
                if self.show_plot_cb.isChecked():
                    self._reload_plot()
                self._update_footer_stats()
            finally:
                self._tree_view.setUpdatesEnabled(True)
                self._tree_view.viewport().update()
            QtCore.QTimer.singleShot(0, self._fit_cumulative_column)
            self._save_view_snapshot()
        finally:
            progress.close()
            progress.deleteLater()

    @Slot()
    def _on_show_all_clicked(self) -> None:
        """Put every calculated node in the table and expand so the graph shows them."""
        state = self._current_state
        if state is None:
            return
        root_uid = self._tree_model.root_uid
        all_uids = {uid for uid in state.nodes if uid != root_uid}
        total = self._state_total_score(state)
        self._tree_view.setUpdatesEnabled(False)
        try:
            self._tree_model.load_state(state, total, included_uids=all_uids)
            self._update_delegate_maxima()
            to_expand = {
                uid
                for uid, item in self._tree_model.iter_uid_items()
                if self._tree_model.has_real_children(item)
            }
            self._restore_expanded_uids(to_expand)
            if self.show_plot_cb.isChecked():
                self._reload_plot()
            self._update_footer_stats()
        finally:
            self._tree_view.setUpdatesEnabled(True)
            self._tree_view.viewport().update()
        self._save_view_snapshot()

    def _apply_expand_view_state(self, max_tier: int) -> None:
        """Collapse, then open rows with real children whose display tier is ``< max_tier``."""
        self._suppress_expand_handler = True
        self._tree_view.setUpdatesEnabled(False)
        try:
            self._tree_view.collapseAll()
            to_expand: list[tuple[int, QtGui.QStandardItem]] = []
            for uid, item in self._tree_model.iter_uid_items():
                if not self._tree_model.has_real_children(item):
                    continue
                tier_i = int(item.data(TIER_ROLE) or 0)
                if tier_i >= max_tier:
                    continue
                to_expand.append((tier_i, item))
            to_expand.sort(key=lambda pair: pair[0])
            for _, item in to_expand:
                idx = self._tree_model.indexFromItem(item)
                if idx.isValid():
                    self._tree_view.expand(idx)
        finally:
            self._tree_view.setUpdatesEnabled(True)
            QtCore.QTimer.singleShot(0, self._release_expand_handler)

    @Slot()
    def _show_help(self) -> None:
        QtWidgets.QMessageBox.question(
            self,
            "Contribution Tree",
            HELP_TEXT.strip(),
            QtWidgets.QMessageBox.Ok,
            QtWidgets.QMessageBox.Ok,
        )

    def _fit_cumulative_column(self) -> None:
        """Widen Cumulative impact (%) to fit header, values, and tree indentation."""
        self._tree_view.resizeColumnToContents(COL_CUMULATIVE_PCT)

    @Slot(QtCore.QPoint)
    def _on_tree_context_menu(self, pos: QtCore.QPoint) -> None:
        index = self._tree_view.indexAt(pos)
        if index.isValid():
            # Right-click on an unselected row selects it (standard table UX)
            sm = self._tree_view.selectionModel()
            if sm is not None and not sm.isSelected(index):
                sm.select(
                    index,
                    QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect
                    | QtCore.QItemSelectionModel.SelectionFlag.Rows,
                )

        activities = self._selected_activities()
        show_open_process_menu(
            self._tree_view,
            activities,
            self._tree_view.viewport().mapToGlobal(pos),
        )

    def _selected_activities(self) -> list:
        """Brightway nodes for the currently selected contribution-tree rows."""
        state = self._current_state
        if state is None:
            return []
        sm = self._tree_view.selectionModel()
        if sm is None:
            return []
        seen: set[int] = set()
        refs: list[dict] = []
        for index in sm.selectedRows(0):
            item = self._tree_model.itemFromIndex(index)
            if item is None:
                continue
            uid = item.data(UID_ROLE)
            if uid is None or uid in seen:
                continue
            seen.add(uid)
            node = state.nodes.get(uid)
            aid = getattr(node, "activity_datapackage_id", None) if node is not None else None
            meta = {}
            if aid is not None:
                meta = activity_metadata_for_ids([aid], app.metadata.dataframe).get(aid, {})
            refs.extend(
                open_process_refs(
                    nodes=state.nodes,
                    uid=uid,
                    activity_id=aid,
                    database=meta.get("database"),
                    code=meta.get("code"),
                )
            )
        return activities_from_open_refs(refs)

    @Slot(QtCore.QModelIndex)
    def _on_row_expanded(self, index: QtCore.QModelIndex) -> None:
        """Lazily traverse when the user expands a row (queued; safe to mutate model)."""
        if self._suppress_expand_handler:
            return
        if not index.isValid():
            return
        first_col_idx = index.siblingAtColumn(0)
        if not first_col_idx.isValid():
            return
        first_col_item = self._tree_model.itemFromIndex(first_col_idx)
        if first_col_item is None:
            return
        uid = first_col_item.data(UID_ROLE)
        if uid is None:
            return

        state = self._current_state
        need_traverse = (
            state is not None and uid not in getattr(state, "visited_nodes", set())
        )
        progress = self._busy_dialog("Expanding branch…") if need_traverse else None
        try:
            # Materialize any known children not yet in the model (path prune /
            # cumulative "only as many siblings as needed" leftovers). Safe when
            # the row already has some children — collapse/re-expand reveals rest.
            if need_traverse:
                self._sync_lca_to_current_selection()
            added = self._tree_model.expand_node(uid)
        finally:
            if progress is not None:
                progress.close()
                progress.deleteLater()
        if added or self._tree_model.has_real_children(first_col_item):
            self._update_delegate_maxima()
            self._schedule_refresh_view_from_tree()
            return

        # Leaf: collapse after the current event finishes
        persistent = QtCore.QPersistentModelIndex(first_col_idx)

        def _collapse_leaf():
            if persistent.isValid():
                self._tree_view.collapse(QtCore.QModelIndex(persistent))

        QtCore.QTimer.singleShot(0, _collapse_leaf)

    @Slot(QtCore.QModelIndex)
    def _on_row_collapsed(self, index: QtCore.QModelIndex) -> None:
        """Footer coverage is view-scoped; refresh when branches hide."""
        if self._suppress_expand_handler:
            return
        self._schedule_refresh_view_from_tree()

    # ------------------------------------------------------------------
    # Plot helpers
    # ------------------------------------------------------------------

    def _schedule_refresh_view_from_tree(self) -> None:
        """Coalesce expand/collapse plot rebuilds onto the next event-loop tick."""
        if self._view_refresh_pending:
            return
        self._view_refresh_pending = True
        QtCore.QTimer.singleShot(0, self._flush_refresh_view_from_tree)

    def _flush_refresh_view_from_tree(self) -> None:
        self._view_refresh_pending = False
        self._refresh_view_from_tree()

    def _refresh_view_from_tree(self) -> None:
        row_stats = self._visible_row_stats()
        if self.show_plot_cb.isChecked():
            self._reload_plot(row_stats, preserve_view=True)
        self._update_footer_stats(row_stats)

    def _visible_row_stats(self) -> tuple[int, float, int, set[int]]:
        """Single pass: shown count, direct coverage, max tier, visible uids."""
        state = self._current_state
        if state is None:
            return 0, 0.0, 0, set()
        total = self._state_total_score(state)
        shown_n = 0
        direct_sum = 0.0
        max_tier = 0
        visible_uids: set[int] = set()
        for uid, item in self._tree_model.iter_uid_items():
            if not self._is_row_visible(item):
                continue
            shown_n += 1
            visible_uids.add(uid)
            max_tier = max(max_tier, int(item.data(TIER_ROLE) or 0))
            node = state.nodes.get(uid)
            if node is not None:
                direct_sum += getattr(node, "direct_emissions_score", 0.0)
        coverage = direct_sum / abs(total) if total else 0.0
        return shown_n, coverage, max_tier, visible_uids

    def _reload_plot(
        self,
        row_stats: tuple[int, float, int, set[int]] | None = None,
        *,
        preserve_view: bool = False,
    ) -> None:
        if self._current_state is None:
            self._d3_plot.show_empty()
            return
        self._reload_d3_plot(row_stats, preserve_view=preserve_view)

    def _reload_d3_plot(
        self,
        row_stats: tuple[int, float, int, set[int]] | None = None,
        *,
        preserve_view: bool = False,
    ) -> None:
        d3 = self._d3_plot
        state = self._current_state
        if state is None:
            d3.show_empty()
            return
        meta = state.metadata or {}
        if row_stats is None:
            row_stats = self._visible_row_stats()
        _, _, max_tier, visible_uids = row_stats
        plot_depth = max(1, max_tier + 1)
        color_by = self.color_by_cb.currentData() or "direct"
        self._tree_model._prefetch_meta_for_uids(visible_uids, state.nodes)
        if self.plot_type_cb.currentData() == PLOT_GRAPH:
            payload = d3_graph_payload(
                state.nodes,
                state.edges,
                self._state_total_score(state),
                root_uid=state._root_node.unique_id,
                included_uids=visible_uids,
                metadata_lookup=self._tree_model.lookup_activity_meta,
                aggregate_by=self.aggregate_by_cb.currentData(),
                color_by=color_by,
                unit=meta.get("unit", ""),
                empty_message="" if visible_uids else "Use Adjust to explore the supply chain.",
                style=d3.style_from_palette(),
                visited=getattr(state, "visited_nodes", None),
            )
            if preserve_view:
                payload["preserve_view"] = True
            d3.set_payload(payload)
            return
        segments = build_plot_segments(
            state.nodes,
            state.edges,
            self._state_total_score(state),
            max_depth=plot_depth,
            root_uid=state._root_node.unique_id,
            metadata_lookup=self._tree_model.lookup_activity_meta,
            included_uids=visible_uids,
            aggregate_by=self.aggregate_by_cb.currentData(),
        )
        payload = d3_plot_payload(
            segments,
            self.plot_type_cb.currentData() or PLOT_GRAPH,
            unit=meta.get("unit", ""),
            empty_message="" if segments else "Use Adjust to explore the supply chain.",
            style=d3.style_from_palette(),
            plot_depth=plot_depth,
            color_by=color_by,
        )
        d3.set_payload(payload)

    # ------------------------------------------------------------------
    # Delegate maxima
    # ------------------------------------------------------------------

    @Slot()
    def _update_delegate_maxima(self) -> None:
        for col in BAR_COLUMNS:
            mx = self._tree_model.col_max.get(col, 1.0)
            if col in self._delegates:
                self._delegates[col].column_max = max(mx, 1e-12)
        self._tree_view.viewport().update()

    # ------------------------------------------------------------------
    # Footer stats
    # ------------------------------------------------------------------

    def _update_footer_stats(
        self,
        row_stats: tuple[int, float, int, set[int]] | None = None,
    ) -> None:
        state = self._current_state
        if state is None:
            self._stats_label.setText("")
            self.show_all_btn.setEnabled(False)
            return
        root_uid = self._tree_model.root_uid
        total = self._state_total_score(state)
        if row_stats is None:
            row_stats = self._visible_row_stats()
        shown_n, shown_cov, shown_tier, _ = row_stats
        calc_cov = direct_impact_coverage(state.nodes, total, root_uid)
        calc_n = sum(1 for uid in state.nodes if uid != root_uid)
        calc_tier = self._max_calculated_tier()

        calc_part = (
            f"Calculated: {calc_n} nodes, {calc_cov * 100:.1f}% of direct impacts, "
            f"max tier {calc_tier}"
        )
        target = self._last_expand_target_pct
        if (
            target is not None
            and self.expand_mode_cb.currentData() == EXPAND_MODE_CUMULATIVE
            and calc_cov * 100.0 + 0.05 < target
        ):
            calc_part += f" (target {target:.0f}% — not reached)"

        self._stats_label.setText(
            f"Shown: {shown_n} nodes, {shown_cov * 100:.1f}% of direct impacts, "
            f"max tier {shown_tier}"
            f"  |  {calc_part}"
        )
        self.show_all_btn.setEnabled(shown_n < calc_n)

    def _is_row_visible(self, item: QtGui.QStandardItem) -> bool:
        """True when every ancestor index is expanded in the tree view."""
        idx = self._tree_model.indexFromItem(item)
        if not idx.isValid():
            return False
        parent = idx.parent()
        while parent.isValid():
            if not self._tree_view.isExpanded(parent):
                return False
            parent = parent.parent()
        return True

    def _max_calculated_tier(self) -> int:
        """Deepest edge-based display tier among all discovered traversal nodes."""
        state = self._current_state
        if state is None:
            return 0
        root_uid = self._tree_model.root_uid
        if root_uid is None:
            return 0
        meta = state.metadata
        if meta is not None:
            cached_n = meta.get("_max_tier_node_count")
            if cached_n == len(state.nodes) and "max_tier" in meta:
                return int(meta["max_tier"])
        tiers = compute_node_tiers(state.nodes, state.edges, root_uid)
        result = max(tiers.values(), default=0)
        if meta is not None:
            meta["max_tier"] = result
            meta["_max_tier_node_count"] = len(state.nodes)
        return result

    # ------------------------------------------------------------------
    # Export (Ticket 06)
    # ------------------------------------------------------------------

    @Slot()
    def _export_table(self) -> None:
        if self._current_state is None:
            return
        df = self._tree_model.to_dataframe()
        if df.empty:
            return
        default_name = (
            lca_export_basename(self.parent.cs_name, "ContributionTree")
            if self.parent
            else "contribution_tree"
        )
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Contribution Tree",
            default_name,
            "Excel (*.xlsx);;CSV (*.csv)",
        )
        if not path:
            return
        try:
            if path.endswith(".csv"):
                df.to_csv(path, index=False)
            else:
                df.to_excel(path, index=False)
            logger.info(f"Contribution tree exported to {path}")
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Export failed", str(exc))

    @Slot()
    def _export_plot(self) -> None:
        if self._current_state is None:
            return
        default_name = (
            lca_export_basename(self.parent.cs_name, "ContributionTreePlot")
            if self.parent
            else "contribution_tree_plot"
        )
        file_filter = "SVG (*.svg);;PNG (*.png)"
        path, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Contribution Tree Plot",
            default_name,
            file_filter,
        )
        if not path:
            return
        self._d3_plot.export_figure(path, selected_filter)
