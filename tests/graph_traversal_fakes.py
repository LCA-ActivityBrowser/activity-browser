"""Shared fake traversal nodes/edges for graph_traversal unit tests (no Qt)."""

from __future__ import annotations

from types import SimpleNamespace


def node(uid, depth, cumulative, direct, supply=1.0, activity_id=None):
    return SimpleNamespace(
        unique_id=uid,
        depth=depth,
        cumulative_score=cumulative,
        direct_emissions_score=direct,
        supply_amount=supply,
        activity_datapackage_id=activity_id or uid,
    )


def edge(consumer_uid, producer_uid):
    return SimpleNamespace(
        consumer_unique_id=consumer_uid,
        producer_unique_id=producer_uid,
    )


# Keep the names existing tests used.
_node = node
_edge = edge


def _simple_tree():
    """Two-tier tree: root → A(6), B(4); A → C(3), D(2)."""
    nodes = {
        -1: _node(-1, 0, 10.0, 0.0),
        1: _node(1, 1, 6.0, 1.0),
        2: _node(2, 1, 4.0, 1.0),
        3: _node(3, 2, 3.0, 1.0),
        4: _node(4, 2, 2.0, 1.0),
    }
    edges = [
        _edge(-1, 1), _edge(-1, 2),
        _edge(1, 3), _edge(1, 4),
    ]
    return nodes, edges


def _rf_supplier_tree():
    """Virtual root → RF (uid 0) → suppliers; parent uid 0 must not be falsy."""
    nodes = {
        -1: _node(-1, 0, 10.0, 0.0),
        0: _node(0, 1, 10.0, 3.0, activity_id=100),
        1: _node(1, 2, 6.0, 1.0, activity_id=101),
        2: _node(2, 2, 3.0, 1.0, activity_id=102),
    }
    edges = [_edge(-1, 0), _edge(0, 1), _edge(0, 2)]
    return nodes, edges


def _circular_ab_visits():
    """NNEV-style cycle: A → B → A (second visit of A)."""
    nodes = {
        -1: _node(-1, 0, 10.0, 0.0),
        0: _node(0, 1, 10.0, 2.0, activity_id=100),
        1: _node(1, 2, 7.0, 1.0, activity_id=101),
        2: _node(2, 3, 5.0, 5.0, activity_id=100),
    }
    edges = [_edge(-1, 0), _edge(0, 1), _edge(1, 2)]
    return nodes, edges


class _FakeTraversalState:
    """Minimal stand-in for SameNodeEachVisitGraphTraversal."""

    def __init__(self, nodes, edges, visited):
        self.nodes = nodes
        self.edges = list(edges)
        self.visited_nodes = set(visited)
        self._root_node = nodes[-1]
        self.traversed: list[int] = []

    def traverse_from_node(self, unique_id, depth=1):
        self.traversed.append(unique_id)
        self.visited_nodes.add(unique_id)
        return True


def _expand_chain_state(*, visited=None):
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 90.0, 5.0),
        2: _node(2, 2, 80.0, 10.0),
        3: _node(3, 3, 60.0, 40.0),
    }
    edges = [_edge(-1, 1), _edge(1, 2), _edge(2, 3)]
    return _FakeTraversalState(nodes, edges, visited or {-1})


def _two_visits_different_suppliers():
    """Same process P via a small and a large path; each visit has a distinct supplier."""
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 0.5, 0.1, activity_id=10),
        2: _node(2, 1, 36.0, 0.17, activity_id=10),
        3: _node(3, 2, 0.4, 0.4, activity_id=20),
        4: _node(4, 2, 30.0, 1.0, activity_id=30),
    }
    edges = [_edge(-1, 1), _edge(-1, 2), _edge(1, 3), _edge(2, 4)]
    return nodes, edges


def _meta(uid):
    return {
        "product": f"product_{uid}",
        "name": f"process_{uid}",
        "location": "GLO",
        "database": "testdb",
        "unit": "kg",
    }


def _visible_nodes():
    """Depth-0 virtual root + three tier-1 suppliers (no further children yet)."""
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 50.0, 20.0),
        2: _node(2, 1, 30.0, 10.0),
        3: _node(3, 1, 20.0, 5.0),
    }
    edges = [_edge(-1, 1), _edge(-1, 2), _edge(-1, 3)]
    return nodes, edges
