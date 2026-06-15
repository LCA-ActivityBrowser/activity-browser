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

from activity_browser.bwutils.commontasks import database_is_legacy


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
