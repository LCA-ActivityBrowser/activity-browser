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


def lca_for_tree_selection(
    *,
    has_scenarios: bool,
    mlca: Any,
    demand: dict,
    method,
    scenario_idx: int | None,
    method_idx: int,
    cached_lca: Any = None,
    cached_scope: frozenset[str] | None = None,
) -> tuple[Any, frozenset[str] | None]:
    """LCA object for the Tree tab's current reference flow / method / scenario.

    With scenarios, reuse ``mlca.lca`` after ``update_lca_calculation_for_sankey``
    (same as Sankey). Without scenarios, solve a private ``bc.LCA`` via
    ``prepared_lca_inputs`` (rebuild when demand databases change).
    """
    if has_scenarios:
        if mlca is None:
            raise ValueError("Scenario Tree LCA requires SuperstructureMLCA")
        idx = 0 if scenario_idx is None else scenario_idx
        mlca.update_lca_calculation_for_sankey(idx, demand, method_idx)
        return mlca.lca, None

    import bw2calc as bc

    fu_input, data_objs, _ = prepared_lca_inputs(demand, method)
    scope = demand_database_names(demand)
    if cached_lca is None or cached_scope != scope:
        lca = bc.LCA(demand=fu_input, data_objs=data_objs)
        lca.lci(factorize=True)
        lca.lcia()
        return lca, scope
    cached_lca.redo_lci(fu_input)
    cached_lca.switch_method(method)
    cached_lca.lcia()
    return cached_lca, scope


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
