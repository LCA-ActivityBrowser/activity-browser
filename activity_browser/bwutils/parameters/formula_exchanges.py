"""Rebuild Brightway's parameterized-flow index after a database write."""

from __future__ import annotations

import bw2data as bd
from bw2data.backends import ExchangeDataset
from bw2data.errors import UnknownObject
from bw2data.parameters import ActivityParameter, DatabaseParameter, ParameterizedExchange

# Skip rebuild when outgoing flows exceed this and the database has no parameters.
INDEX_FLOW_CAP = 1000


def flow_formula(exc: ExchangeDataset) -> str:
    """Return the stripped formula on a flow document, or ``""``.

    Parameters
    ----------
    exc : ExchangeDataset
        Brightway flow document.
    """
    data = getattr(exc, "data", None)
    if isinstance(data, dict):
        formula = str(data.get("formula") or "").strip()
        if formula:
            return formula
    return str(getattr(exc, "formula", "") or "").strip()


def _process_types() -> frozenset[str]:
    return frozenset(bd.labels.process_node_types) | {"multifunctional"}


def _should_rebuild(database: str) -> bool:
    has_params = (
        DatabaseParameter.select().where(DatabaseParameter.database == database).count()
        or ActivityParameter.select().where(ActivityParameter.database == database).count()
    )
    if has_params:
        return True
    return (
        ExchangeDataset.select()
        .where(ExchangeDataset.output_database == database)
        .count()
        <= INDEX_FLOW_CAP
    )


def _delete_index_rows_for_database(database: str) -> None:
    groups = [
        row.group
        for row in ActivityParameter.select(ActivityParameter.group).where(
            ActivityParameter.database == database
        )
    ]
    if groups:
        ParameterizedExchange.delete().where(
            ParameterizedExchange.group << groups
        ).execute()
    outgoing_ids = [
        row.id
        for row in ExchangeDataset.select(ExchangeDataset.id).where(
            ExchangeDataset.output_database == database
        )
    ]
    if outgoing_ids:
        ParameterizedExchange.delete().where(
            ParameterizedExchange.exchange << outgoing_ids
        ).execute()


def index_parameterized_flows_for_process(key: tuple) -> None:
    """Index formula-bearing flows on one process and recalculate that group.

    Parameters
    ----------
    key : tuple
        Process ``(database, code)``. Non-process nodes are ignored.
    """
    act = bd.get_activity(key)
    if act.get("type", "process") not in _process_types():
        return
    ap = ActivityParameter.get_or_none(database=key[0], code=key[1])
    group = ap.group if ap else act.id
    with bd.parameters.db.atomic():
        bd.parameters.remove_exchanges_from_group(group, act)
        bd.parameters.add_exchanges_to_group(group, act)
        ActivityParameter.recalculate_exchanges(group)


def rebuild_parameterized_flow_index(database: str) -> None:
    """Rebuild Brightway's parameterized-flow index for one database.

    Skips databases with more than ``INDEX_FLOW_CAP`` outgoing flows and no
    database or activity parameters. Does not delete project, database, or
    activity parameters.

    Parameters
    ----------
    database : str
        Name of the database that was written.
    """
    if database not in bd.databases or not _should_rebuild(database):
        return

    _delete_index_rows_for_database(database)

    process_codes = {
        exc.output_code
        for exc in ExchangeDataset.select().where(
            ExchangeDataset.output_database == database
        )
        if flow_formula(exc)
    }
    for code in process_codes:
        try:
            index_parameterized_flows_for_process((database, code))
        except UnknownObject:
            continue


def indexed_parameterized_flows():
    """Yield parameterized-flow index rows as dicts.

    Each dict has ``formula``, ``amount``, ``comment``, ``uncertainty``,
    ``input_key``, ``output_key``, and ``exchange`` (a live proxy, or ``None``).
    """
    for pe in ParameterizedExchange.select():
        try:
            doc = ExchangeDataset.get_by_id(int(pe.exchange))
        except Exception:
            continue
        data = doc.data if isinstance(doc.data, dict) else {}
        try:
            exchange = bd.Edge(document=doc)
        except Exception:
            exchange = None
        yield {
            "formula": pe.formula or flow_formula(doc),
            "amount": data.get("amount"),
            "comment": data.get("comment"),
            "uncertainty": data.get("uncertainty") if isinstance(data.get("uncertainty"), dict) else {},
            "input_key": (doc.input_database, doc.input_code),
            "output_key": (doc.output_database, doc.output_code),
            "exchange": exchange,
        }
