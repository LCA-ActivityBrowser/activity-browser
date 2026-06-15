"""LCIA characterization-factor helpers (Brightway ``Method`` / ``methods``).

Brightway stores characterization factors (CFs) as rows ``(elementary_flow, amount)``
on impact assessment methods. Activity Browser uses these helpers when adding or
removing CFs and when cleaning up references to deleted elementary flows.
"""

from __future__ import annotations

from bw2data.backends.schema import get_id
from bw2data.errors import UnknownObject

import bw2data as bd

from activity_browser.bwutils.commontasks import refresh_node


def elementary_flow_activity_id(key: tuple | int) -> int:
    """Return the Brightway activity id for an elementary-flow key or id."""
    if isinstance(key, tuple):
        return refresh_node(key).id
    if isinstance(key, int):
        return get_id(key)
    raise ValueError(f"Unexpected elementary flow identifier: {key!r}")


def cf_row_references_flow_ids(row, flow_ids: set[int]) -> bool:
    """Return whether a CF row references any of *flow_ids*.

    Integer keys are compared directly so we do not hit the database for every
    row when scanning LCIA methods.
    """
    key = row[0]
    if isinstance(key, int):
        return key in flow_ids
    try:
        return elementary_flow_activity_id(key) in flow_ids
    except UnknownObject:
        return False


def valid_characterization_factor_rows(rows: list) -> tuple[list, set[int], int]:
    """Normalize CF rows to integer activity ids and drop orphaned references.

    Returns ``(rows, site_generic_flow_ids, dropped_count)``. Site-generic CFs
    are rows with fewer than three elements (no regionalization location).
    """
    valid_rows: list = []
    site_generic_ids: set[int] = set()
    dropped = 0

    for row in rows:
        try:
            flow_id = elementary_flow_activity_id(row[0])
        except UnknownObject:
            dropped += 1
            continue
        valid_rows.append((flow_id, *row[1:]))
        if len(row) < 3:
            site_generic_ids.add(flow_id)

    return valid_rows, site_generic_ids, dropped


def remove_orphaned_characterization_factors(method: bd.Method) -> int:
    """Drop CFs whose elementary flow no longer exists. Returns rows removed."""
    data, _, dropped = valid_characterization_factor_rows(list(method.load()))
    if not dropped:
        return 0
    method.write(data)
    return dropped


def impact_methods_with_flows(flow_ids: set[int]) -> list[tuple]:
    """Return LCIA method names that contain a CF for any of *flow_ids*."""
    if not flow_ids:
        return []
    matches: list[tuple] = []
    for name in bd.methods:
        for row in bd.Method(name).load():
            if cf_row_references_flow_ids(row, flow_ids):
                matches.append(name)
                break
    return matches


def remove_characterization_factors_for_flows(flow_ids: set[int]) -> int:
    """Remove CFs for the given elementary flows from all LCIA methods.

    Returns the number of methods updated.
    """
    if not flow_ids:
        return 0

    updated = 0
    for method_name in bd.methods:
        method = bd.Method(method_name)
        data = list(method.load())
        if not any(cf_row_references_flow_ids(row, flow_ids) for row in data):
            continue
        valid, _, _ = valid_characterization_factor_rows(data)
        new_data = [row for row in valid if row[0] not in flow_ids]
        method.write(new_data)
        updated += 1
    return updated


def activity_ids_in_database(database_name: str) -> set[int]:
    """Brightway activity ids for all nodes in *database_name*."""
    if database_name not in bd.databases:
        return set()
    return {node.id for node in bd.Database(database_name)}


def remove_characterization_factors_for_database(db_name: str) -> int:
    """Remove CFs for all elementary flows in *db_name* from every LCIA method."""
    return remove_characterization_factors_for_flows(activity_ids_in_database(db_name))
