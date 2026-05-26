"""
Parameter Monte Carlo overlay for ``bw2calc.MultiLCA``.

Each iteration, after technosphere / biosphere / CF resampling, ``bind_parameter_hook``
samples uncertain Brightway parameters, recalculates formula exchanges, and writes amounts
into the LCA matrices.

For ``functional_sqlite``, exchange keys often use **process** codes while matrix columns
use **reference product** activity ids — resolved via ``bw_functional`` (AB loads it at
startup in ``__main__.py``).
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

import bw2calc as bc
import bw2data as bd
import numpy as np
from loguru import logger

from bw2data.backends import ActivityDataset, ExchangeDataset

# Legacy type code in parameter MC rows (see ``Index.exchange_type`` in ``utils.py``).
BIOSPHERE_EXCHANGE_TYPE = 2


def activity_key_parts(key: Any) -> Tuple[str, str]:
    """Return ``(database, code)`` from a Brightway activity key or datapackage key."""
    if hasattr(key, "database"):
        return key.database, key.code
    return key[0], key[1]


def activity_id_from_database_code(database: str, code: str) -> int:
    """``ActivityDataset.id`` for a technosphere or biosphere activity."""
    return ActivityDataset.get(
        ActivityDataset.database == database,
        ActivityDataset.code == code,
    ).id


def activity_id_from_key(key: Any) -> int:
    """``ActivityDataset.id`` for a functional-unit or exchange activity key."""
    database, code = activity_key_parts(key)
    return activity_id_from_database_code(database, code)


def _is_functional_sqlite_database(database: str) -> bool:
    return bd.databases[database].get("backend", "sqlite") == "functional_sqlite"


def _functional_process_and_product(
    database: str, code: str
) -> Tuple[Optional[Any], Optional[Any]]:
    """Return ``(Process, Product)`` for a process or reference-product code."""
    try:
        node = bd.get_activity((database, code))
    except Exception:
        return None, None

    from bw_functional import Process, Product

    if isinstance(node, Product):
        return node.processor, node

    if isinstance(node, Process):
        products = node.products()
        if not products:
            return node, None
        if len(products) == 1:
            return node, products[0]
        for product in products:
            if product.get("processor") == node.key:
                return node, product
        return node, products[0]

    return None, None


def _reference_product_activity_id(database: str, code: str) -> Optional[int]:
    """Matrix column id for the reference product behind a process or product code."""
    if not _is_functional_sqlite_database(database):
        return None
    _, product = _functional_process_and_product(database, code)
    return product.id if product is not None else None


def _activity_ids_for_matrix_lookup(
    database: str,
    code: str,
    preferred_id: Optional[int] = None,
) -> List[int]:
    """Candidate ``ActivityDataset.id`` values to match ``lca.dicts.activity`` / ``product``."""
    ordered: List[int] = []
    seen: set[int] = set()

    def add(activity_id: Optional[int]) -> None:
        if activity_id is not None and activity_id not in seen:
            seen.add(activity_id)
            ordered.append(activity_id)

    add(preferred_id)
    if _is_functional_sqlite_database(database):
        add(_reference_product_activity_id(database, code))
    try:
        add(activity_id_from_database_code(database, code))
    except ActivityDataset.DoesNotExist:
        pass
    return ordered


def _matrix_index(
    mapping: dict,
    database: str,
    code: str,
    preferred_id: Optional[int] = None,
) -> Optional[int]:
    for activity_id in _activity_ids_for_matrix_lookup(database, code, preferred_id):
        index = mapping.get(activity_id)
        if index is not None:
            return index
    return None


def activity_col_in_lca(
    lca: bc.MultiLCA,
    database: str,
    code: str,
    activity_id: Optional[int] = None,
) -> Optional[int]:
    """Technosphere / biosphere column index in ``lca.dicts.activity``."""
    return _matrix_index(lca.dicts.activity, database, code, activity_id)


def product_row_in_lca(
    lca: bc.MultiLCA,
    database: str,
    code: str,
    activity_id: Optional[int] = None,
) -> Optional[int]:
    """Product row index in ``lca.dicts.product``."""
    return _matrix_index(lca.dicts.product, database, code, activity_id)


def exchange_from_param_row(row: np.void) -> ExchangeDataset:
    """Load the ``ExchangeDataset`` row described by a parameter MC numpy row."""
    inp, out = row["input"], row["output"]
    if hasattr(inp, "database"):
        in_db, in_code, out_db, out_code = inp.database, inp.code, out.database, out.code
    else:
        in_db, in_code, out_db, out_code = inp[0], inp[1], out[0], out[1]
    return ExchangeDataset.get(
        ExchangeDataset.input_code == in_code,
        ExchangeDataset.input_database == in_db,
        ExchangeDataset.output_code == out_code,
        ExchangeDataset.output_database == out_db,
    )


def matrix_coords_for_param_row(
    lca: bc.MultiLCA, row: np.void
) -> Optional[Tuple[str, int, int]]:
    """Return ``(matrix_name, row_index, col_index)`` or ``None`` if not in this LCA."""
    if row["type"] == BIOSPHERE_EXCHANGE_TYPE:
        return _biosphere_matrix_coords(lca, row)
    return _technosphere_matrix_coords(lca, row)


def _biosphere_matrix_coords(
    lca: bc.MultiLCA, row: np.void
) -> Optional[Tuple[str, int, int]]:
    input_id = activity_id_from_key(row["input"])
    out_db, out_code = activity_key_parts(row["output"])
    output_id = activity_id_from_key(row["output"])
    bio_row = lca.dicts.biosphere.get(input_id)
    act_col = activity_col_in_lca(lca, out_db, out_code, output_id)
    if bio_row is None or act_col is None:
        return None
    return ("biosphere_matrix", bio_row, act_col)


def _technosphere_matrix_coords(
    lca: bc.MultiLCA, row: np.void
) -> Optional[Tuple[str, int, int]]:
    in_db, in_code = activity_key_parts(row["input"])
    out_db, out_code = activity_key_parts(row["output"])
    input_id = activity_id_from_key(row["input"])
    output_id = activity_id_from_key(row["output"])

    prod_row = product_row_in_lca(lca, in_db, in_code, input_id)
    if prod_row is None:
        prod_row = product_row_in_lca(lca, out_db, out_code, output_id)
    act_col = activity_col_in_lca(lca, out_db, out_code, output_id)
    if prod_row is None or act_col is None:
        return None
    return ("technosphere_matrix", prod_row, act_col)


def signed_exchange_amount(row: np.void) -> float:
    """Amount with technosphere sign convention (negative edge types)."""
    amount = float(row["amount"])
    if exchange_from_param_row(row).type in bd.labels.technosphere_negative_edge_types:
        return -amount
    return amount


def apply_parameter_exchanges(lca: bc.MultiLCA, param_rows: np.ndarray) -> int:
    """Write recalculated parameter amounts into ``MultiLCA`` matrices. Returns cells updated."""
    updated = 0
    for row in param_rows:
        coords = matrix_coords_for_param_row(lca, row)
        if coords is None:
            continue
        matrix_name, i, j = coords
        amount = signed_exchange_amount(row)
        if matrix_name == "technosphere_matrix":
            lca.technosphere_matrix[i, j] = amount
        else:
            lca.biosphere_matrix[i, j] = amount
        updated += 1
    # if updated:
    #     logger.debug("Parameter MC updated {} matrix cells".format(updated))
    return updated


def bind_parameter_hook(lca: bc.MultiLCA, monte_carlo_lca: Any) -> None:
    """
    Attach ``after_matrix_iteration`` on ``lca`` to apply parameter draws from ``monte_carlo_lca``.

    Expects ``monte_carlo_lca.include_parameters`` and ``monte_carlo_lca.parameter_mc_manager``.
    """

    def after_matrix_iteration() -> None:
        manager = monte_carlo_lca.parameter_mc_manager
        if not monte_carlo_lca.include_parameters or manager is None:
            return
        apply_parameter_exchanges(lca, manager.next())

    lca.after_matrix_iteration = after_matrix_iteration
