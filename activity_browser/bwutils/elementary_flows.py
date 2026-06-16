"""Elementary-flow (biosphere) helpers.

Brightway ``Activity.delete()`` removes technosphere upstream exchanges and
calculation-setup references, but not biosphere exchanges on other activities
nor characterization factors on LCIA methods. Activity Browser handles those
explicitly when deleting elementary flows.
"""

from __future__ import annotations

from uuid import uuid4

import bw2data as bd
from bw2data.configuration import labels

from activity_browser.bwutils.commontasks import (
    biosphere_node_types,
    database_is_legacy,
    is_node_biosphere,
    refresh_node,
)


def create_elementary_flow(
    db_name: str,
    *,
    name: str,
    unit: str,
    flow_type: str,
    categories: tuple[str, ...] = (),
) -> bd.Node:
    """Create and save an elementary flow (emission or resource) in *db_name*.

    On ``functional_sqlite`` backends, ``Database.new_node()`` returns a process
    wrapper whose ``save()`` overwrites biosphere ``type`` values. A plain
    ``bd.Node`` is used so the elementary-flow type is preserved.
    """
    code = uuid4().hex
    if database_is_legacy(db_name):
        flow = bd.Database(db_name).new_node(
            code=code,
            name=name,
            unit=unit,
            type=flow_type,
            categories=categories,
        )
    else:
        flow = bd.Node(
            database=db_name,
            code=code,
            name=name,
            unit=unit,
            type=flow_type,
            categories=categories,
        )
    flow.save()
    return flow


def update_elementary_flow(
    flow,
    *,
    name: str,
    unit: str,
    flow_type: str,
    categories: tuple[str, ...] = (),
) -> bd.Node:
    """Update metadata for an existing elementary flow, preserving biosphere type.

    On ``functional_sqlite`` backends, ``Process.save()`` overwrites biosphere
    ``type`` values. Updates go through ``MFActivity`` instead.
    """
    flow = refresh_node(flow)
    if not is_node_biosphere(flow):
        raise ValueError(f"Not an elementary flow: {flow.key}")
    if flow_type not in biosphere_node_types():
        raise ValueError(f"Invalid elementary-flow type: {flow_type}")

    db_name = flow["database"]
    code = flow["code"]
    if database_is_legacy(db_name):
        flow["name"] = name
        flow["unit"] = unit
        flow["categories"] = categories
        flow["type"] = flow_type
        flow.save()
        return flow

    import bw_functional  # noqa: F401
    from bw_functional.node_classes import MFActivity

    activity = MFActivity(document=flow._document)
    activity["name"] = name
    activity["unit"] = unit
    activity["type"] = flow_type
    activity["categories"] = categories
    activity.save()
    return refresh_node((db_name, code))


def count_biosphere_exchanges_for_flow(flow) -> int:
    """Count technosphere biosphere exchanges that reference *flow* as input."""
    return len(list(flow.upstream(kinds=labels.biosphere_edge_types)))


def delete_biosphere_exchanges_for_flow(flow) -> int:
    """Delete technosphere biosphere exchanges on other activities that use *flow*."""
    upstream = flow.upstream(kinds=labels.biosphere_edge_types)
    count = len(list(upstream))
    if count:
        upstream.delete()
    return count
