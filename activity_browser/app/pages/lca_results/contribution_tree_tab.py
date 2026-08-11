"""Contribution Tree tab for the LCA Results page.

Shows the contribution tree as a hierarchical QTreeView (one row per
traversed upstream supplier) with a sunburst plot above it.
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
from activity_browser.bwutils.contribution_tree import (
    compute_node_tiers,
    cumulative_percent,
    direct_impact_coverage,
    plan_cumulative_expand,
    path_display_set,
    next_expand_candidates,
    suppress_graph_traversal_warnings,
)
from activity_browser.bwutils.export_names import lca_export_basename
from activity_browser.ui.delegates.impact_background import ImpactBackgroundDelegate

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
from .contribution_tree_plot import SunburstPlot
from .style import SmallComboBox, apply_lca_combo_width, lca_header_layout, lca_help_tool_button, lca_tab_control_row

HELP_TEXT = """
<html><body>
<p><b>Contribution Tree</b> shows how impact accumulates along the supply chain
of one reference flow and impact category (and scenario, when present).</p>

<p><b>Tree table</b><br>
Each row is a process on a supply path. <i>Cumulative impact (%)</i> is the share
of the total score that flows through that path (path impact).
<i>Direct impact (%)</i> is only the characterised emissions of that process itself.
The reference flow is <b>tier 0</b>; its suppliers are tier 1, and so on.
Expand a row manually to calculate and list all of its suppliers.</p>

<p><b>Cutoff</b><br>
Engine threshold for Brightway graph traversal: branches whose path impact is
below this percent of the total score are not followed further during calculation.</p>

<p><b>Expand to</b><br>
• <b>Tier</b> — calculate and open the tree down to the chosen tier.<br>
• <b>Individual path impact</b> — calculate and open every node whose
path (cumulative) impact is at least X% of the total <i>and</i> that still
has a child ≥ X% (the high-impact path continues). Under those opened nodes
list all discovered siblings (including below X%). A terminal ≥ X% node
stays collapsed until you expand it manually. Only the engine <b>Cutoff</b>
omits smaller branches from calculation.<br>
• <b>Cumulative impact</b> — from the reference flow, open the
<i>largest</i> paths first until Σ(direct impact) of the rows in that tree
reaches X% of the total. Children of an opened node are added largest-first
and stop once the target is met (collapse and re-expand a row to list every
child). Further Brightway traversal runs only when the next node to open
is not yet calculated. If the engine cutoff stops discovery early, the
footer shows that the target was not reached.</p>

<p><b>Sunburst</b><br>
Layers match tiers. <i>Plot tiers</i> controls how many rings are drawn; it does
not change the table.</p>

<p><b>Footer</b><br>
<b>Shown</b> = visible rows, their direct-impact share, and deepest visible
tier (updates on expand/collapse). <b>Calculated</b> = all nodes discovered
by graph traversal, their direct-impact coverage, and deepest calculated
tier. </p>
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

    Shows a QTreeView (lazy, expandable by tier) with a sunburst plot above.
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
        self.has_been_opened: bool = False
        self.plot_name: str = "Contribution Tree"
        # Skip lazy-fetch / leaf-collapse while applying Expand-to view state
        self._suppress_expand_handler: bool = False

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
        self.cutoff_sb.setValue(0.01)
        self.cutoff_sb.setSuffix(" %")
        self.cutoff_sb.setKeyboardTracking(False)
        self.cutoff_sb.setToolTip(
            "Graph traversal cutoff: prune branches whose cumulative impact "
            "is below this percent of the total LCA score"
        )

        self.plot_depth_sb = QtWidgets.QSpinBox()
        self.plot_depth_sb.setRange(1, 20)
        self.plot_depth_sb.setValue(3)
        self.plot_depth_sb.setToolTip("Number of tiers shown in the sunburst plot")

        self.expand_mode_cb = SmallComboBox()
        self.expand_mode_cb.addItem("Tier", EXPAND_MODE_TIER)
        self.expand_mode_cb.addItem("Individual path impact", EXPAND_MODE_PATH)
        self.expand_mode_cb.addItem("Cumulative impact", EXPAND_MODE_CUMULATIVE)
        self.expand_mode_cb.setToolTip("How far auto-expand calculates and opens the tree")

        self.expand_value_sb = QtWidgets.QDoubleSpinBox()
        self.expand_value_sb.setKeyboardTracking(False)
        self.expand_btn = QtWidgets.QPushButton("Expand")
        self.expand_btn.setToolTip("Calculate and open branches according to the expand policy")

        self.show_plot_cb = QtWidgets.QCheckBox("Show plot")
        self.show_plot_cb.setChecked(False)
        self.show_table_cb = QtWidgets.QCheckBox("Show table")
        self.show_table_cb.setChecked(True)
        self._last_expand_target_pct: float | None = None

        # Export buttons
        self.export_table_btn = QtWidgets.QPushButton("Export table…")
        self.export_plot_btn = QtWidgets.QPushButton("Export plot…")

        self._stats_label = QtWidgets.QLabel("")
        self._stats_label.setToolTip(
            "Shown = visible rows / Direct impact (%) sum / deepest visible tier. "
            "Calculated = traversal nodes / their coverage / deepest calculated tier."
        )
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

        # --- Sunburst plot ---
        self._plot = SunburstPlot(self)
        self._plot.setMinimumHeight(180)

        self._tree_view.setMinimumHeight(120)

        # --- Splitter ---
        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self._splitter.addWidget(self._plot)
        self._splitter.addWidget(self._tree_view)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 2)
        self._splitter.setChildrenCollapsible(False)

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
        self._plot.setVisible(show_plot)
        self._tree_view.setVisible(show_table)
        QtCore.QTimer.singleShot(0, self._apply_splitter_sizes)

    def _apply_splitter_sizes(self) -> None:
        show_plot = self.show_plot_cb.isChecked()
        show_table = self.show_table_cb.isChecked()
        total = max(self._splitter.height(), 1)
        if show_plot and show_table:
            plot_h = max(total // 3, self._plot.minimumHeight())
            table_h = max(total - plot_h, self._tree_view.minimumHeight())
            self._splitter.setSizes([plot_h, table_h])
        elif show_plot:
            self._splitter.setSizes([total, 0])
        elif show_table:
            self._splitter.setSizes([0, total])
        if show_plot:
            self._plot.sync_figure_to_widget()
            self._plot.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        main = QtWidgets.QVBoxLayout(self)
        main.setContentsMargins(4, 4, 4, 4)

        # Header + help
        help_btn = lca_help_tool_button(
            self,
            "Left click for help on the Contribution Tree",
            self._show_help,
        )
        main.addLayout(lca_header_layout("Contribution Tree", help_btn))

        # Control row 1: FU / method / scenario (left-aligned like other LCA tabs)
        row1 = lca_tab_control_row()
        row1.addWidget(QtWidgets.QLabel("Reference flow:"))
        row1.addWidget(self.fu_cb)
        row1.addWidget(QtWidgets.QLabel("Impact category:"))
        row1.addWidget(self.method_cb)
        row1.addWidget(self.scenario_label)
        row1.addWidget(self.scenario_cb)
        row1.addStretch()
        main.addLayout(row1)

        # Control row 2: cutoff / plot tiers / expand policy
        row2 = lca_tab_control_row()
        row2.addWidget(QtWidgets.QLabel("Cutoff:"))
        row2.addWidget(self.cutoff_sb)
        row2.addSpacing(12)
        row2.addWidget(QtWidgets.QLabel("Plot tiers:"))
        row2.addWidget(self.plot_depth_sb)
        row2.addSpacing(12)
        row2.addWidget(QtWidgets.QLabel("Expand to:"))
        row2.addWidget(self.expand_mode_cb)
        row2.addWidget(self.expand_value_sb)
        row2.addWidget(self.expand_btn)
        row2.addSpacing(12)
        row2.addWidget(self.show_plot_cb)
        row2.addWidget(self.show_table_cb)
        row2.addStretch()
        main.addLayout(row2)

        # Splitter (plot + tree)
        main.addWidget(self._splitter, 1)

        # Footer: stats + export
        footer = QtWidgets.QHBoxLayout()
        footer.addWidget(self._stats_label)
        footer.addStretch()
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
        self.cutoff_sb.valueChanged.connect(self._on_cutoff_changed)
        self.plot_depth_sb.valueChanged.connect(self._on_plot_depth_changed)
        self.expand_mode_cb.currentIndexChanged.connect(self._on_expand_mode_changed)
        self.expand_btn.clicked.connect(self._on_expand_clicked)
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

    def _ensure_lca(self, demand: dict, method, scenario_idx, method_idx: int | None = None) -> None:
        """Keep the shared LCA object in sync with the current RF/method/scenario.

        All cached traversal states hold a reference to this same LCA. Switching
        RF without ``redo_lci`` leaves ``state.lca.score`` belonging to another
        demand, which breaks coverage checks and further ``traverse_from_node``.
        """

        if self.has_scenarios and scenario_idx is not None:
            mi = method_idx if method_idx is not None else self.method_cb.currentIndex()
            self.parent.mlca.update_lca_calculation_for_sankey(
                scenario_idx, demand, mi
            )

        if self._cached_lca is None:
            fu_input, data_objs, _ = bd.prepare_lca_inputs(demand=demand, method=method)
            self._cached_lca = bc.LCA(demand=fu_input, data_objs=data_objs)
            self._cached_lca.lci(factorize=True)
            self._cached_lca.lcia()
        else:
            self._cached_lca.redo_lci(demand)
            self._cached_lca.switch_method(method)
            self._cached_lca.lcia()

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
        """Indeterminate busy spinner (QProgressDialog with range 0–0)."""
        progress = QtWidgets.QProgressDialog(label, None, 0, 0, self)
        progress.setWindowTitle("Contribution Tree")
        # Non-modal so tree expand/collapse still applies while it is visible.
        progress.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)
        progress.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, False)
        progress.show()
        progress.raise_()
        QtWidgets.QApplication.processEvents()
        return progress

    @staticmethod
    def _busy_tick(progress: QtWidgets.QProgressDialog, label: str | None = None) -> None:
        if label is not None:
            progress.setLabelText(label)
        QtWidgets.QApplication.processEvents(
            QtCore.QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
        )

    def _run_traversal(self) -> None:
        key = self._cache_key()
        demand, method, scenario_idx = self._selection_inputs(key)
        method_idx = key[1]

        if key in self._cache:
            logger.debug(f"Contribution tree cache hit: {key}")
            # Shared LCA may have been switched to another RF — restore it
            # before using the cached graph (scores, further expand).
            self._ensure_lca(demand, method, scenario_idx, method_idx)
            entry = self._cache[key]
            self._store_total_score(entry.state)
            self._active_cache_key = key
            self._current_state = entry.state
            self._reload_from_state(
                expanded_uids=entry.expanded_uids,
                model_uids=entry.model_uids,
            )
            self._fit_cumulative_column()
            return

        logger.debug(f"Contribution tree traversal start: {key}")
        progress = self._busy_dialog("Calculating contribution tree…")

        try:
            self._busy_tick(progress, "Running LCI / LCIA…")
            self._ensure_lca(demand, method, scenario_idx, method_idx)

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
            self._busy_tick(progress, "Building tree…")
            self._reload_from_state(expanded_uids=None, model_uids=None)
            self._save_view_snapshot()
            self._fit_cumulative_column()

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
        self._tree_model.load_state(state, total)
        if model_uids is not None:
            self._tree_model.restrict_to_uids(model_uids)
        self._update_delegate_maxima()
        self._tree_view.collapseAll()
        if expanded_uids:
            self._restore_expanded_uids(expanded_uids)
        self._reload_plot()
        self._update_footer_stats()
        QtCore.QTimer.singleShot(0, self._apply_splitter_sizes)

    def _collect_expanded_uids(self) -> set[int]:
        """Return unique_ids of rows currently expanded in the tree view."""
        expanded: set[int] = set()
        for uid, item in self._tree_model.iter_uid_items():
            idx = self._tree_model.indexFromItem(item)
            if idx.isValid() and self._tree_view.isExpanded(idx):
                expanded.add(uid)
        return expanded

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
            self._suppress_expand_handler = False

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

    @Slot()
    def _on_selection_changed(self) -> None:
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

    @Slot(int)
    def _on_plot_depth_changed(self, depth: int) -> None:
        self._reload_plot()

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
                "siblings below that % are still listed (engine cutoff still applies)"
            )
        else:
            self.expand_value_sb.setDecimals(0)
            self.expand_value_sb.setRange(1, 99)
            self.expand_value_sb.setSingleStep(1)
            self.expand_value_sb.setSuffix(" %")
            if reset_value:
                self.expand_value_sb.setValue(60)
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
        # Ensure shared LCA matches this cached graph before any further traverse.
        key = self._cache_key()
        demand, method, scenario_idx = self._selection_inputs(key)
        self._ensure_lca(demand, method, scenario_idx, key[1])
        self._store_total_score(state)
        total = self._state_total_score(state)
        root_uid = state._root_node.unique_id

        progress = self._busy_dialog("Expanding contribution tree…")
        self._last_expand_target_pct = (
            value if mode in (EXPAND_MODE_PATH, EXPAND_MODE_CUMULATIVE) else None
        )
        try:
            cumulative_included: set[int] | None = None
            cumulative_expand: set[int] | None = None
            path_included: set[int] | None = None
            path_expand: set[int] | None = None

            if mode == EXPAND_MODE_CUMULATIVE:
                self._busy_tick(progress, "Traversing supply chain…")
                cumulative_included, cumulative_expand = (
                    self._expand_cumulative_brightway(value, progress)
                )
            else:
                self._busy_tick(progress, "Traversing supply chain…")
                self._expand_policy_brightway(mode, value, progress)
                if mode == EXPAND_MODE_PATH:
                    path_included, path_expand = path_display_set(
                        state.nodes,
                        state.edges,
                        root_uid,
                        total,
                        value,
                        state.visited_nodes,
                    )

            # Rebuild tree once from traversal state (already-known nodes are free)
            self._busy_tick(progress, "Building tree…")
            self._tree_model.load_state(state, total)
            if mode == EXPAND_MODE_PATH and path_included is not None:
                # Keep high-path nodes + all their siblings; drop unrelated deep cache
                self._tree_model.restrict_to_uids(path_included)
            elif mode == EXPAND_MODE_CUMULATIVE and cumulative_included is not None:
                # Show only the largest-first set that meets the target — not
                # every node ever calculated in this RF's cached graph.
                self._tree_model.restrict_to_uids(cumulative_included)

            self._busy_tick(progress, "Updating tree view…")
            self._update_delegate_maxima()
            if mode == EXPAND_MODE_TIER:
                self._apply_expand_view_state(max_tier=int(value))
            elif mode == EXPAND_MODE_PATH and path_expand is not None:
                self._restore_expanded_uids(path_expand)
            elif cumulative_expand is not None:
                self._restore_expanded_uids(cumulative_expand)
            if self.show_plot_cb.isChecked():
                self._busy_tick(progress, "Updating plot…")
                self._reload_plot()
            self._update_footer_stats()
            self._fit_cumulative_column()
            self._save_view_snapshot()
        finally:
            progress.close()
            progress.deleteLater()

    def _expand_cumulative_brightway(
        self,
        target_pct: float,
        progress: QtWidgets.QProgressDialog,
    ) -> tuple[set[int], set[int]]:
        """Largest-first from RFs until display-set coverage meets ``target_pct``.

        Reuses already-calculated edges when possible; only calls
        ``traverse_from_node`` when the next node to open is still unvisited.
        Returns ``(included_uids, visually_expanded_uids)``.
        """
        state = self._current_state
        assert state is not None
        total = self._state_total_score(state)
        root_uid = state._root_node.unique_id
        failed: set[int] = set()
        included: set[int] = set()
        to_expand: set[int] = set()

        for step in range(10_000):
            included, to_expand, need = plan_cumulative_expand(
                state.nodes,
                state.edges,
                root_uid,
                total,
                target_pct,
                state.visited_nodes,
                exclude=failed,
            )
            if need is None:
                break
            if step % 10 == 0:
                self._busy_tick(
                    progress,
                    f"Traversing supply chain… ({len(state.nodes)} nodes)",
                )
            node = state.nodes.get(need)
            if node is None or need in state.visited_nodes:
                failed.add(need)
                continue
            node.depth = 0
            with suppress_graph_traversal_warnings():
                if not state.traverse_from_node(need, depth=1):
                    failed.add(need)

        return included, to_expand

    def _expand_policy_brightway(
        self,
        mode: str,
        value: float,
        progress: QtWidgets.QProgressDialog,
    ) -> None:
        """Run tier/path expand policy against Brightway state only.

        Cumulative mode uses :meth:`_expand_cumulative_brightway` instead.
        """
        state = self._current_state
        if state is None:
            return
        total = self._state_total_score(state)
        root_uid = state._root_node.unique_id
        failed: set[int] = set()

        for step in range(10_000):
            candidates = next_expand_candidates(
                state.nodes,
                state.edges,
                state.visited_nodes,
                mode=mode,
                value=value,
                total_score=total,
                root_uid=root_uid,
                exclude=failed,
            )
            if not candidates:
                break

            if step % 10 == 0:
                self._busy_tick(
                    progress,
                    f"Traversing supply chain… ({len(state.nodes)} nodes)",
                )

            made_progress = False
            for uid in candidates:
                node = state.nodes.get(uid)
                if node is None or uid in state.visited_nodes:
                    failed.add(uid)
                    continue
                node.depth = 0
                with suppress_graph_traversal_warnings():
                    if state.traverse_from_node(uid, depth=1):
                        made_progress = True
                    else:
                        failed.add(uid)
            if not made_progress:
                break

    def _apply_expand_view_state(
        self,
        max_tier: int | None = None,
        *,
        min_path_pct: float | None = None,
        only_visited: bool = False,
    ) -> None:
        """Collapse, then open calculated branches according to the expand policy.

        * Tier: open rows with real children whose display tier is ``< max_tier``.
        * Individual path impact: prefer ``path_display_set`` + restore expands
          on the Expand button path; this helper is mainly for Tier.
        * Cumulative: open visited nodes that have real children.
        """
        state = self._current_state
        total = self._state_total_score(state) if state is not None else 0.0
        visited = state.visited_nodes if state is not None else set()

        self._suppress_expand_handler = True
        try:
            self._tree_view.collapseAll()
            to_expand: list[tuple[int, QtGui.QStandardItem]] = []
            for uid, item in self._tree_model.iter_uid_items():
                if not self._tree_model.has_real_children(item):
                    continue
                tier = item.data(TIER_ROLE)
                tier_i = int(tier) if tier is not None else 0
                if max_tier is not None and tier_i >= max_tier:
                    continue
                if only_visited and uid not in visited:
                    continue
                if min_path_pct is not None and state is not None:
                    node = state.nodes.get(uid)
                    if node is None:
                        continue
                    if abs(cumulative_percent(node, total)) < min_path_pct:
                        continue
                to_expand.append((tier_i, item))
            to_expand.sort(key=lambda pair: pair[0])
            for _, item in to_expand:
                idx = self._tree_model.indexFromItem(item)
                if idx.isValid():
                    self._tree_view.expand(idx)
        finally:
            self._suppress_expand_handler = False

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
        menu = QtWidgets.QMenu(self._tree_view)
        menu.addAction(
            app.actions.ActivityOpen.get_QAction(
                activities,
                parent=menu,
                text="Open process" if len(activities) <= 1 else "Open processes",
                enabled=bool(activities),
            )
        )
        menu.exec_(self._tree_view.viewport().mapToGlobal(pos))

    def _selected_activities(self) -> list:
        """Brightway nodes for the currently selected contribution-tree rows."""
        state = self._current_state
        if state is None:
            return []
        sm = self._tree_view.selectionModel()
        if sm is None:
            return []
        seen: set[int] = set()
        activities = []
        for index in sm.selectedRows(0):
            item = self._tree_model.itemFromIndex(index)
            if item is None:
                continue
            uid = item.data(UID_ROLE)
            if uid is None or uid in seen:
                continue
            seen.add(uid)
            node = state.nodes.get(uid)
            if node is None:
                continue
            aid = getattr(node, "activity_datapackage_id", None)
            if aid is None or aid < 0:
                continue
            try:
                activities.append(bd.get_node(id=aid))
            except Exception:
                logger.debug(f"Could not resolve activity id {aid} for Open process")
        return activities

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

        # Materialize any known children not yet in the model (path prune /
        # cumulative "only as many siblings as needed" leftovers). Safe when
        # the row already has some children — collapse/re-expand reveals rest.
        added = self._tree_model.expand_node(uid)
        if added or self._tree_model.has_real_children(first_col_item):
            self._update_delegate_maxima()
            self._reload_plot()
            self._update_footer_stats()
            self._fit_cumulative_column()
            self._save_view_snapshot()
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
        self._update_footer_stats()
        self._save_view_snapshot()

    # ------------------------------------------------------------------
    # Plot helpers
    # ------------------------------------------------------------------

    def _reload_plot(self) -> None:
        if self._current_state is None:
            return
        if not self.show_plot_cb.isChecked():
            return
        self._plot.set_state(
            self._current_state,
            self._state_total_score(self._current_state),
            self.plot_depth_sb.value(),
        )

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

    def _update_footer_stats(self) -> None:
        state = self._current_state
        if state is None:
            self._stats_label.setText("")
            return
        root_uid = self._tree_model.root_uid
        total = self._state_total_score(state)
        shown_cov = self._visible_direct_impact_coverage()
        shown_n = sum(
            1
            for _, item in self._tree_model.iter_uid_items() 
            if self._is_row_visible(item)
        )
        calc_cov = direct_impact_coverage(state.nodes, total, root_uid)
        calc_n = sum(1 for uid in state.nodes if uid != root_uid)
        shown_tier = self._max_visible_tier()
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

    def _visible_direct_impact_coverage(self) -> float:
        """Σ(direct impact of visible rows) / |total| — same as summing the column."""
        state = self._current_state
        if state is None:
            return 0.0
        total = self._state_total_score(state)
        if total == 0.0:
            return 0.0
        direct_sum = 0.0
        for uid, item in self._tree_model.iter_uid_items():
            if not self._is_row_visible(item):
                continue
            node = state.nodes.get(uid)
            if node is None:
                continue
            direct_sum += getattr(node, "direct_emissions_score", 0.0)
        return direct_sum / abs(total)

    def _max_visible_tier(self) -> int:
        """Deepest tier among rows whose ancestor chain is expanded in the view."""
        max_tier = 0
        for _, item in self._tree_model.iter_uid_items():
            if self._is_row_visible(item):
                max_tier = max(max_tier, int(item.data(TIER_ROLE) or 0))
        return max_tier

    def _max_calculated_tier(self) -> int:
        """Deepest edge-based display tier among all discovered traversal nodes."""
        state = self._current_state
        if state is None:
            return 0
        root_uid = self._tree_model.root_uid
        if root_uid is None:
            return 0
        tiers = compute_node_tiers(state.nodes, state.edges, root_uid)
        return max(tiers.values(), default=0)

    # ------------------------------------------------------------------
    # Export (Ticket 06)
    # ------------------------------------------------------------------

    @Slot()
    def _export_table(self) -> None:
        if self._current_state is None:
            return
        df = self._tree_model.to_dataframe(metadata_lookup=None)
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
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Sunburst Plot",
            default_name,
            "SVG (*.svg);;PNG (*.png)",
        )
        if not path:
            return
        try:
            self._plot.figure.savefig(path, bbox_inches="tight")
            logger.info(f"Contribution tree plot exported to {path}")
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Export failed", str(exc))
