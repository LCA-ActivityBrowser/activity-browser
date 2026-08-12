"""Qt item model for the Contribution Tree tab."""

from __future__ import annotations

from types import SimpleNamespace
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
    safe_traverse_from_node,
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
        self._pcm_cache: dict | None = None
        self._pcm_node_count: int = 0

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
        included_uids: set[int] | None = None,
    ) -> None:
        """Rebuild the model from a (possibly cached) traversal state.

        When ``included_uids`` is set, only those nodes are materialized
        (avoids building the full tree then pruning).
        """
        self.clear()
        self.setHorizontalHeaderLabels(COLUMNS)
        self._state = state
        self._total_score = total_score
        self._uid_to_item = {}
        self.col_max = {c: 1.0 for c in BAR_COLUMNS}
        self._root_uid = state._root_node.unique_id
        self._invalidate_pcm_cache()
        self._refresh_tiers()

        pcm = self._parent_child_map()
        root_children = [
            state.nodes[uid]
            for uid in pcm.get(self._root_uid, [])
            if uid in state.nodes
            and (included_uids is None or uid in included_uids)
        ]
        root_children.sort(key=lambda n: abs(n.cumulative_score), reverse=True)
        self._prefetch_meta_for_uids(included_uids, state.nodes)
        self._batch_updating = True
        try:
            for child in root_children:
                self._add_node(
                    child,
                    self.invisibleRootItem(),
                    pcm,
                    included_uids=included_uids,
                )
        finally:
            self._batch_updating = False

    def _parent_child_map(self) -> dict:
        if self._state is None:
            return {}
        n = len(self._state.nodes)
        if self._pcm_cache is not None and self._pcm_node_count == n:
            return self._pcm_cache
        pcm = build_parent_child_map(self._state.nodes, self._state.edges)
        self._pcm_cache = pcm
        self._pcm_node_count = n
        return pcm

    def _invalidate_pcm_cache(self) -> None:
        self._pcm_cache = None
        self._pcm_node_count = 0

    def expand_node(self, unique_id: int) -> bool:
        """Traverse from the given node and add its direct children to the model.

        All children discovered by graph traversal are listed (the engine cutoff
        already limits which edges exist).
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
                if not safe_traverse_from_node(self._state, unique_id):
                    parent_item.emitDataChanged()
                    return False
                self._invalidate_pcm_cache()

            pcm = self._parent_child_map()
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
        if metadata_lookup is None:
            metadata_lookup = self.lookup_activity_meta
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
        included_uids: set[int] | None = None,
    ) -> None:
        """Create a row of QStandardItems for ``node`` under ``parent_item``."""
        if node.unique_id in self._uid_to_item:
            return
        if included_uids is not None and node.unique_id not in included_uids:
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
        if not is_visited and tier > 0:
            row[COL_PROCESS].setForeground(QtGui.QBrush(QtGui.QColor("#888888")))
            row[COL_PROCESS].setToolTip("Not yet expanded — click to explore")

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
                if included_uids is not None and child_node.unique_id not in included_uids:
                    continue
                self._add_node(
                    child_node,
                    first,
                    pcm,
                    recurse_known=True,
                    included_uids=included_uids,
                )

        # Chevron when not yet listing children: unvisited (lazy), or visited with
        # known edges not shown under this row (e.g. prior over-deep traverse).
        if not self.has_real_children(first) and (not is_visited or has_children):
            self._ensure_placeholder(first)

    def _prefetch_meta_for_uids(
        self,
        uids: set[int] | None,
        nodes: dict,
    ) -> None:
        """Warm metadata cache for a filtered display set before building rows."""
        if uids is None:
            return
        for uid in uids:
            node = nodes.get(uid)
            if node is None:
                continue
            aid = getattr(node, "activity_datapackage_id", None)
            if aid is not None and aid not in self._meta_cache:
                self._resolve_meta(node)

    def lookup_activity_meta(self, activity_datapackage_id) -> dict:
        """Public metadata lookup for plot tooltips (by activity id)."""
        if activity_datapackage_id is None:
            return {}
        return self._resolve_meta(
            SimpleNamespace(activity_datapackage_id=activity_datapackage_id)
        )

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

