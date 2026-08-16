"""Contribution Tree tab for the LCA Results page.

Shows the contribution tree as a hierarchical table with an optional supply-chain plot.
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
    PLOT_AGGREGATE_FIELDS,
    PLOT_AGGREGATE_LABELS,
    compute_node_tiers,
    direct_impact_coverage,
    is_terminal_node,
    plot_click_target_uid,
    run_expand_policy,
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
from .contribution_tree_plot import (
    PLOT_ICICLE,
    PLOT_MODES,
    ContributionTreePlot,
)
from .style import SmallComboBox, apply_lca_combo_width, lca_header_layout, lca_help_tool_button, lca_tab_control_row

HELP_TEXT = """
<html><body>
<p><b>Tree</b> shows how impact accumulates along the supply chain for one
reference flow, impact category, and scenario.</p>

<p><b>Table</b><br>
Each row is a process on a supply path. <i>Cumulative impact (%)</i> is
path impact (that process plus all upstream). <i>Direct impact (%)</i> is
only characterised emissions at that process. Tier&nbsp;0 is the reference
flow; tier&nbsp;1 its direct suppliers, and so on. Expand a row to calculate
and list its suppliers.</p>

<p><b>Cutoff</b><br>
During calculation, branches below this share of the total score are not
followed further.</p>

<p><b>Adjust to</b><br>
• <b>Tier</b> — open the tree to a chosen tier.<br>
• <b>Individual path impact</b> — open nodes whose path impact meets the
threshold and still have a qualifying child; list siblings under opened
nodes. A terminal node above the threshold stays collapsed until you expand
it.<br>
• <b>Cumulative impact</b> — open the largest paths first until the direct
impact of visible rows reaches the target.<br>
Stop a long calculation to keep the tree calculated so far.</p>

<p><b>Plot</b><br>
Vertical tiers or Horizontal tiers — mirrors the visible tree. Click a segment to
expand or collapse that branch (merged bands toggle the parent row).
<b>Aggregate by</b> rolls up sibling segments in the plot only. Hover for
product, process, path and direct impact.</p>

<p><b>Footer</b><br>
<b>Shown</b> — visible rows, their direct-impact share, deepest visible tier.
<b>Calculated</b> — all nodes found by traversal, coverage, deepest tier.</p>
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

    Shows a QTreeView (lazy, expandable by tier) with an optional supply-chain plot.
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

        self.plot_type_cb = SmallComboBox()
        for mode_id, label in PLOT_MODES:
            self.plot_type_cb.addItem(label, mode_id)
        for i in range(self.plot_type_cb.count()):
            if self.plot_type_cb.itemData(i) == PLOT_ICICLE:
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

        self.expand_mode_cb = SmallComboBox()
        self.expand_mode_cb.addItem("Tier", EXPAND_MODE_TIER)
        self.expand_mode_cb.addItem("Individual path impact", EXPAND_MODE_PATH)
        self.expand_mode_cb.addItem("Cumulative impact", EXPAND_MODE_CUMULATIVE)
        self.expand_mode_cb.setToolTip("How far Adjust calculates and opens the tree")

        self.expand_value_sb = QtWidgets.QDoubleSpinBox()
        self.expand_value_sb.setKeyboardTracking(False)
        self.expand_btn = QtWidgets.QPushButton("Adjust")
        self.expand_btn.setToolTip("Calculate and open branches according to the adjust policy")

        self.show_plot_cb = QtWidgets.QCheckBox("Show plot")
        self.show_plot_cb.setChecked(True)
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

        # --- Contribution tree plot ---
        self._plot = ContributionTreePlot(self)
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
        was_hidden = not self._plot.isVisible()
        self._plot.setVisible(show_plot)
        self._tree_view.setVisible(show_table)
        if show_plot and was_hidden and self._current_state is not None:
            self._reload_plot()
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
        row1.addStretch()
        main.addLayout(row1)

        # Control row 2: plot/table, cutoff, expand, plot type
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
        self.plot_type_cb.currentIndexChanged.connect(self._on_plot_type_changed)
        self.aggregate_by_cb.currentIndexChanged.connect(self._on_aggregate_by_changed)
        self.expand_mode_cb.currentIndexChanged.connect(self._on_expand_mode_changed)
        self.expand_btn.clicked.connect(self._on_expand_clicked)
        self._plot.set_segment_click_handler(self._on_plot_segment_clicked)
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

    def _busy_rebuild(self, progress: QtWidgets.QProgressDialog) -> None:
        """Hide Stop and keep the dialog while the table and plot are built."""
        if progress.wasCanceled():
            progress.reset()
            progress.setRange(0, 0)
        progress.setCancelButton(None)
        self._busy_tick(progress, "Building table and plot…")

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
            return

        logger.debug(f"Contribution tree traversal start: {key}")
        progress = self._busy_dialog("Calculating contribution tree…")

        try:
            self._busy_tick(progress, "Running LCI / LCIA…")
            self._ensure_lca(demand, method, scenario_idx, method_idx)
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
            self._busy_rebuild(progress)
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

    @Slot()
    def _on_plot_type_changed(self) -> None:
        mode = self.plot_type_cb.currentData()
        if mode:
            self._plot.set_mode(mode)

    @Slot()
    def _on_aggregate_by_changed(self) -> None:
        self._reload_plot()

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
            self._busy_rebuild(progress)

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
            self._refresh_view_from_tree()
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
        self._refresh_view_from_tree()

    # ------------------------------------------------------------------
    # Plot helpers
    # ------------------------------------------------------------------

    def _refresh_view_from_tree(self) -> None:
        row_stats = self._visible_row_stats()
        if self.show_plot_cb.isChecked():
            self._reload_plot(row_stats)
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
    ) -> None:
        if self._current_state is None:
            self._plot.show_empty()
            return
        state = self._current_state
        meta = state.metadata or {}
        if row_stats is None:
            row_stats = self._visible_row_stats()
        _, _, max_tier, visible_uids = row_stats
        self._plot.set_state(
            state,
            self._state_total_score(state),
            max(1, max_tier + 1),
            metadata_lookup=self._tree_model.lookup_activity_meta,
            unit=meta.get("unit", ""),
            included_uids=visible_uids,
            aggregate_by=self.aggregate_by_cb.currentData(),
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

    def _update_footer_stats(
        self,
        row_stats: tuple[int, float, int, set[int]] | None = None,
    ) -> None:
        state = self._current_state
        if state is None:
            self._stats_label.setText("")
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
        try:
            self._plot.export_figure(path, selected_filter)
            logger.info(f"Contribution tree plot exported to {path}")
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Export failed", str(exc))
