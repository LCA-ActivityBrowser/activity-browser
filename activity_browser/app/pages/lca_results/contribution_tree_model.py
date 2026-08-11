"""Qt item model for the Contribution Tree tab."""

from __future__ import annotations

from typing import Optional

import bw2data as bd
from qtpy import QtCore, QtGui

from bw_graph_tools.graph_traversal import SameNodeEachVisitGraphTraversal

from activity_browser.bwutils.contribution_tree import (
    build_parent_child_map,
    compute_node_tiers,
    cumulative_percent,
    direct_percent,
    flatten_to_dataframe,
    suppress_graph_traversal_warnings,
)
from activity_browser.ui.delegates.impact_background import ImpactBackgroundDelegate

COL_CUMULATIVE_PCT = 0
COL_DIRECT_PCT = 1
COL_PRODUCT = 2
COL_PROCESS = 3
COL_LOCATION = 4
COL_DATABASE = 5
COL_FLOW_AMOUNT = 6
COL_UNIT = 7
COL_CUMULATIVE = 8
COL_DIRECT = 9
COL_TIER = 10

COLUMNS = [
    "Cumulative impact (%)",
    "Direct impact (%)",
    "Product",
    "Process",
    "Location",
    "Database",
    "Flow amount",
    "Unit",
    "Cumulative impact",
    "Direct impact",
    "Tier",
]

# Columns that get the impact-background delegate (signed magnitude values)
BAR_COLUMNS = (COL_CUMULATIVE_PCT, COL_DIRECT_PCT, COL_CUMULATIVE, COL_DIRECT)

EXPAND_MODE_TIER = "tier"
EXPAND_MODE_PATH = "path"
EXPAND_MODE_CUMULATIVE = "cumulative"

# Role for contribution-tree node unique_id on the first-column item
UID_ROLE = QtCore.Qt.UserRole + 1
PLACEHOLDER_ROLE = QtCore.Qt.UserRole + 2
TIER_ROLE = QtCore.Qt.UserRole + 3



class ContributionTreeModel(QtGui.QStandardItemModel):
    """QStandardItemModel backed by a SameNodeEachVisitGraphTraversal state.

    Populated lazily: call ``load_state`` after initial traversal, then
    ``expand_node`` from a queued ``expanded`` handler. Empty placeholder
    children provide expand chevrons without visible ellipsis text.
    """

    column_max_changed = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(0, len(COLUMNS), parent)
        self.setHorizontalHeaderLabels(COLUMNS)
        self._state: Optional[SameNodeEachVisitGraphTraversal] = None
        self._total_score: float = 0.0
        self._root_uid: int | None = None
        self._tiers: dict[int, int] = {}
        # Maps unique_id → QStandardItem (the first-column item for that row)
        self._uid_to_item: dict[int, QtGui.QStandardItem] = {}
        # Column max values for the bar-background delegates
        self.col_max: dict[int, float] = {c: 1.0 for c in BAR_COLUMNS}
        self._expanding: bool = False
        self._meta_cache: dict = {}
        self._batch_updating: bool = False

    @staticmethod
    def has_real_children(item: QtGui.QStandardItem) -> bool:
        for row in range(item.rowCount()):
            child = item.child(row, 0)
            if child is not None and not child.data(PLACEHOLDER_ROLE):
                return True
        return False

    def _strip_placeholders(self, parent_item: QtGui.QStandardItem) -> None:
        for row in range(parent_item.rowCount() - 1, -1, -1):
            child = parent_item.child(row, 0)
            if child is not None and child.data(PLACEHOLDER_ROLE):
                parent_item.removeRow(row)

    def _ensure_placeholder(self, first: QtGui.QStandardItem) -> None:
        """Empty child so the view shows a chevron (no visible ellipsis text)."""
        if first.rowCount() > 0:
            return
        ph = QtGui.QStandardItem("")
        ph.setEditable(False)
        ph.setData(True, PLACEHOLDER_ROLE)
        ph.setFlags(QtCore.Qt.ItemFlag.NoItemFlags)
        first.appendRow(
            [ph] + [QtGui.QStandardItem("") for _ in range(len(COLUMNS) - 1)]
        )

    def _refresh_tiers(self) -> None:
        if self._state is None or self._root_uid is None:
            self._tiers = {}
            return
        self._tiers = compute_node_tiers(
            self._state.nodes, self._state.edges, self._root_uid
        )


    # ------------------------------------------------------------------
    # Public accessors (for the tab; avoid reading private maps)
    # ------------------------------------------------------------------

    @property
    def root_uid(self) -> int | None:
        return self._root_uid

    def item_for_uid(self, unique_id: int) -> QtGui.QStandardItem | None:
        return self._uid_to_item.get(unique_id)

    def iter_uid_items(self):
        """Yield ``(unique_id, first_column_item)`` for rows currently in the model."""
        return self._uid_to_item.items()

    def model_uids(self) -> set[int]:
        return set(self._uid_to_item.keys())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_state(
        self,
        state: SameNodeEachVisitGraphTraversal,
        total_score: float,
    ) -> None:
        """Rebuild the model from a (possibly cached) traversal state."""
        self.clear()
        self.setHorizontalHeaderLabels(COLUMNS)
        self._state = state
        self._total_score = total_score
        self._uid_to_item = {}
        self.col_max = {c: 1.0 for c in BAR_COLUMNS}
        self._meta_cache = {}
        self._root_uid = state._root_node.unique_id
        self._refresh_tiers()

        pcm = build_parent_child_map(state.nodes, state.edges)
        root_children = [
            state.nodes[uid]
            for uid in pcm.get(self._root_uid, [])
            if uid in state.nodes
        ]
        root_children.sort(key=lambda n: abs(n.cumulative_score), reverse=True)
        self._batch_updating = True
        try:
            for child in root_children:
                self._add_node(child, self.invisibleRootItem(), pcm)
        finally:
            self._batch_updating = False

    def expand_node(
        self,
        unique_id: int,
        min_path_pct: float | None = None,
    ) -> bool:
        """Traverse from the given node and add its direct children to the model.

        All children discovered by graph traversal are listed (the engine cutoff
        already limits which edges exist). ``min_path_pct`` is ignored for
        listing — it only affects auto-expand policy elsewhere.
        """
        if self._state is None or self._expanding:
            return False

        parent_item = self._uid_to_item.get(unique_id)
        if parent_item is None:
            return False

        self._expanding = True
        try:
            self._strip_placeholders(parent_item)

            if unique_id not in self._state.visited_nodes:
                node = self._state.nodes.get(unique_id)
                if node is None:
                    parent_item.emitDataChanged()
                    return False
                # Brightway computes max_depth from node.depth *before* resetting
                # depth to 0. Without zeroing here, traverse_from_node(depth=1) on
                # a mid-tree node walks old_depth+1 levels and marks direct
                # children as visited — they then get no expand chevrons.
                node.depth = 0
                with suppress_graph_traversal_warnings():
                    if not self._state.traverse_from_node(unique_id, depth=1):
                        parent_item.emitDataChanged()
                        return False

            # Avoid full-graph tier BFS on every expand; new rows use parent+1.
            pcm = build_parent_child_map(self._state.nodes, self._state.edges)
            child_nodes = [
                self._state.nodes[uid]
                for uid in pcm.get(unique_id, [])
                if uid not in self._uid_to_item and uid in self._state.nodes
            ]
            child_nodes.sort(key=lambda n: abs(n.cumulative_score), reverse=True)
            for child_node in child_nodes:
                self._add_node(child_node, parent_item, pcm, recurse_known=False)

            if self.has_real_children(parent_item):
                if not self._batch_updating:
                    self.column_max_changed.emit()
                return True

            parent_item.emitDataChanged()
            return False
        finally:
            self._expanding = False

    def restrict_to_uids(self, keep: set[int]) -> None:
        """Remove rows whose unique_id is not in ``keep`` (deepest first).

        Used when restoring a cached view after path/cumulative display-set
        restrict (or any filter that left a subset of the traversal in the model).
        """
        if self._state is None:
            return
        to_remove = [uid for uid in self._uid_to_item if uid not in keep]
        to_remove.sort(
            key=lambda u: int(self._uid_to_item[u].data(TIER_ROLE) or 0),
            reverse=True,
        )
        for uid in to_remove:
            item = self._uid_to_item.get(uid)
            if item is None:
                continue
            parent = item.parent()
            if parent is None:
                parent = self.invisibleRootItem()
            row = item.row()
            self._forget_subtree(item)
            parent.removeRow(row)

        pcm = build_parent_child_map(self._state.nodes, self._state.edges)
        for uid, item in list(self._uid_to_item.items()):
            if self.has_real_children(item):
                continue
            if self._has_hidden_children(uid, pcm):
                self._ensure_placeholder(item)

    def _forget_subtree(self, item: QtGui.QStandardItem) -> None:
        for row in range(item.rowCount()):
            child = item.child(row, 0)
            if child is not None and not child.data(PLACEHOLDER_ROLE):
                self._forget_subtree(child)
        uid = item.data(UID_ROLE)
        if uid is not None:
            self._uid_to_item.pop(uid, None)

    def _has_hidden_children(self, unique_id: int, pcm: dict | None = None) -> bool:
        if self._state is None:
            return False
        if pcm is None:
            pcm = build_parent_child_map(self._state.nodes, self._state.edges)
        return any(
            cid not in self._uid_to_item and cid in self._state.nodes
            for cid in pcm.get(unique_id, [])
        )

    def to_dataframe(self, metadata_lookup=None):
        """Return a flat DataFrame of all traversed nodes."""
        if self._state is None:
            import pandas as pd
            return pd.DataFrame(columns=COLUMNS)
        return flatten_to_dataframe(
            self._state.nodes,
            self._state.edges,
            self._total_score,
            metadata_lookup=metadata_lookup,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add_node(
        self,
        node,
        parent_item: QtGui.QStandardItem,
        pcm: dict,
        *,
        recurse_known: bool = True,
    ) -> None:
        """Create a row of QStandardItems for ``node`` under ``parent_item``."""
        if node.unique_id in self._uid_to_item:
            return

        meta = self._resolve_meta(node)
        total = self._total_score
        # Tier from edge distance to FU — never Brightway node.depth after lazy expand
        tier = self._tiers.get(node.unique_id)
        if tier is None:
            if parent_item is self.invisibleRootItem():
                tier = 0
            else:
                parent_tier = parent_item.data(TIER_ROLE)
                tier = (int(parent_tier) + 1) if parent_tier is not None else 0

        cum_pct = cumulative_percent(node, total)
        dir_pct = direct_percent(node, total)

        def _item(text, value=None, numeric=False):
            it = QtGui.QStandardItem()
            it.setText(str(text))
            it.setEditable(False)
            if value is not None:
                it.setData(value, ImpactBackgroundDelegate.VALUE_ROLE)
            if numeric and isinstance(value, float):
                it.setData(value, QtCore.Qt.UserRole)
            return it

        row = [
            _item(f"{cum_pct:.2f}", value=cum_pct, numeric=True),
            _item(f"{dir_pct:.2f}", value=dir_pct, numeric=True),
            _item(meta.get("product", "")),
            _item(meta.get("name", "")),
            _item(meta.get("location", "")),
            _item(meta.get("database", "")),
            _item(f"{node.supply_amount:.4g}"),
            _item(meta.get("unit", "")),
            _item(f"{node.cumulative_score:.4g}", value=node.cumulative_score, numeric=True),
            _item(
                f"{node.direct_emissions_score:.4g}",
                value=node.direct_emissions_score,
                numeric=True,
            ),
            _item(str(tier)),
        ]

        is_visited = node.unique_id in (self._state.visited_nodes if self._state else set())
        has_children = bool(pcm.get(node.unique_id))
        is_leaf = is_visited and not has_children
        if not is_visited and tier > 0:
            row[COL_PROCESS].setForeground(QtGui.QBrush(QtGui.QColor("#888888")))
            row[COL_PROCESS].setToolTip("Not yet expanded — click to explore")

        if is_leaf:
            for item in row:
                font = item.font()
                font.setItalic(True)
                item.setFont(font)

        parent_item.appendRow(row)
        first = row[COL_CUMULATIVE_PCT]
        first.setData(node.unique_id, UID_ROLE)
        first.setData(tier, TIER_ROLE)
        self._uid_to_item[node.unique_id] = first

        self._update_col_max(COL_CUMULATIVE_PCT, abs(cum_pct))
        self._update_col_max(COL_DIRECT_PCT, abs(dir_pct))
        self._update_col_max(COL_CUMULATIVE, abs(node.cumulative_score))
        self._update_col_max(COL_DIRECT, abs(node.direct_emissions_score))

        if recurse_known:
            known_children = pcm.get(node.unique_id, [])
            child_nodes = [
                self._state.nodes[uid]
                for uid in known_children
                if self._state and uid in self._state.nodes and uid not in self._uid_to_item
            ]
            child_nodes.sort(key=lambda n: abs(n.cumulative_score), reverse=True)
            for child_node in child_nodes:
                self._add_node(child_node, first, pcm, recurse_known=True)

        # Chevron when not yet listing children: unvisited (lazy), or visited with
        # known edges not shown under this row (e.g. prior over-deep traverse).
        if not self.has_real_children(first) and (not is_visited or has_children):
            self._ensure_placeholder(first)

    def _resolve_meta(self, node) -> dict:
        """Fetch activity metadata from bw2data (cached; empty dict on failure)."""
        aid = getattr(node, "activity_datapackage_id", None)
        if aid in self._meta_cache:
            return self._meta_cache[aid]
        try:
            act = bd.get_node(id=aid)
            meta = {
                "product": act.get("reference product") or act.get("name", ""),
                "name": act.get("name", ""),
                "location": act.get("location", ""),
                "database": act.get("database", ""),
                "unit": act.get("unit", ""),
            }
        except Exception:
            meta = {}
        if aid is not None:
            self._meta_cache[aid] = meta
        return meta

    def _update_col_max(self, col: int, value: float) -> None:
        if value > self.col_max.get(col, 0.0):
            self.col_max[col] = value

