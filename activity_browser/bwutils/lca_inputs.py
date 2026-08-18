"""Product-keyed LCA demand for Brightway 2.5 / ``functional_sqlite``.

Stopgap used by Tree and Sankey: remap process datapackage ids to product ids
so demand keys match the product dictionary. MultiLCA, Monte Carlo, and GSA
still prepare demand independently.

Future: this mapping belongs in a shared place, preferably **bw_functional**,
not a new Activity Browser layering ADR. See
``docs/adr/0001-ui-app-bwutils-layering.md``.
"""

from __future__ import annotations

from typing import Any


def _as_node(key):
    from activity_browser.mod import bw2data as bd

    if hasattr(key, "id") and hasattr(key, "get"):
        return key
    if isinstance(key, int):
        return bd.get_node(id=key)
    return bd.get_activity(key)


def _product_id_for_demand(node) -> int:
    """Matrix product id for a process, product, or waste node."""
    products_fn = getattr(node, "products", None)
    if callable(products_fn):
        products = list(products_fn() or [])
        if products:
            if len(products) == 1:
                return products[0].id
            for product in products:
                if product.get("processor") == getattr(node, "key", None):
                    return product.id
            return products[0].id
    return node.id


def demand_as_product_ids(demand: dict) -> dict:
    """Rewrite a functional-unit dict so keys are product datapackage ids."""
    return {_product_id_for_demand(_as_node(key)): amount for key, amount in demand.items()}


def demand_database_names(demand: dict) -> frozenset[str]:
    """Database labels present in a functional-unit dict."""
    names: set[str] = set()
    for key in demand:
        node = _as_node(key)
        names.add(node["database"])
    return frozenset(names)


def prepared_lca_inputs(demand: dict, method: tuple | None = None, **kwargs: Any):
    """Map a functional-unit demand to product keys and datapackage objects.

    ``functional_sqlite`` process datapackage ids are not in the product
    dictionary. Always use the returned demand for ``LCA(...)`` and
    ``LCA.redo_lci`` — never pass process ids to ``redo_lci``.
    """
    from activity_browser.mod import bw2data as bd

    return bd.prepare_lca_inputs(
        demand=demand_as_product_ids(demand),
        method=method,
        **kwargs,
    )


def activity_direct_impacts(lca) -> dict[int, float]:
    """Solved-inventory direct LCIA per activity datapackage id."""
    import numpy as np

    inv = getattr(lca, "characterized_inventory", None)
    if inv is None:
        return {}
    totals = np.asarray(inv.sum(axis=0)).ravel()
    dicts = getattr(lca, "dicts", None)
    activity = getattr(dicts, "activity", None)
    reversed_map = getattr(activity, "reversed", None)
    if reversed_map is None:
        return {}
    out: dict[int, float] = {}
    for index, value in enumerate(totals):
        try:
            aid = int(reversed_map[index])
        except (KeyError, TypeError, ValueError):
            continue
        out[aid] = float(value)
    return out
