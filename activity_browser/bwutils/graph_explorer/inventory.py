"""Brightway inventory adapter for the Graph explorer. No Qt."""

from __future__ import annotations

from collections import defaultdict

import bw2data as bd
from bw2data.backends import ActivityDataset, ExchangeDataset

from activity_browser.bwutils.commontasks import (
    identify_activity_type,
    is_node_process,
    is_node_product,
    is_node_waste,
)
from activity_browser.bwutils.graph_explorer.explorer import (
    Counterpart,
    FlowKey,
    PairFlow,
)

_PROCESS_TYPES = {
    "process",
    "nonfunctional",
    "multifunctional",
    "processwithreferenceproduct",
}


def _is_process(node) -> bool:
    raw = getattr(getattr(node, "_document", None), "type", None)
    if raw in _PROCESS_TYPES:
        return True
    try:
        return is_node_process(node)
    except Exception:
        return False


def _product_unit(exc, node) -> tuple[str, str]:
    product = node.get("reference product") or node.get("product") or node.get("name") or ""
    unit = exc.get("unit") or node.get("unit") or ""
    return str(product), str(unit)


def _physical_side(
    host_id: int,
    other_id: int,
    amount: float,
    *,
    role: str = "product",
    host_treats_waste: bool = False,
    other_treats_waste: bool = False,
    host_is_market: bool = False,
) -> str:
    source, target = _physical_endpoints(
        host_id, other_id, amount,
        role=role,
        host_treats_waste=host_treats_waste,
        other_treats_waste=other_treats_waste,
        host_is_market=host_is_market,
    )
    return "upstream" if target == host_id else "downstream"


def _exchange_type(exc) -> str | None:
    return exc.get("type") or getattr(getattr(exc, "_document", None), "type", None)


def _physical_endpoints(
    host_id: int,
    other_id: int,
    amount: float,
    *,
    role: str = "product",
    host_treats_waste: bool = False,
    other_treats_waste: bool = False,
    host_is_market: bool = False,
) -> tuple[int, int]:
    """Physical source → target. Waste: generator → treatment.

    A waste *market*'s technosphere inputs of the same waste are the
    treatments/regional markets it mixes — onward (downstream), not suppliers.
    A transforming treatment's input of a waste market stays upstream.
    """
    if host_treats_waste and other_treats_waste and host_is_market:
        return host_id, other_id
    if host_treats_waste:
        return other_id, host_id
    if other_treats_waste or role == "waste":
        return host_id, other_id
    source, target = other_id, host_id
    if amount < 0:
        source, target = target, source
    return source, target


def _host_treats_waste(prod_map: dict[tuple[str, str], float], product: str, unit: str) -> bool:
    amt = prod_map.get((product, unit))
    return amt is not None and amt < 0


def _functional_end(role: str) -> str:
    """Black circle: waste / production-as-input at the receiver; product at the producer."""
    return "target" if role == "waste" else "source"


def _production_map(act) -> dict[tuple[str, str], float]:
    out: dict[tuple[str, str], float] = {}
    for pe in act.production():
        product, unit = _product_unit(pe, pe.input)
        out[(product, unit)] = float(pe.get("amount") or 0)
    return out


def _merge_counterparts(primary: list[Counterpart], extra: list[Counterpart]) -> list[Counterpart]:
    by_id: dict[int, Counterpart] = {c.process_id: c for c in primary}
    for c in extra:
        prev = by_id.get(c.process_id)
        if prev is None:
            by_id[c.process_id] = c
            continue
        if c.abs_amount > prev.abs_amount:
            by_id[c.process_id] = Counterpart(
                c.process_id, c.amount, c.role, c.functional_at,
                from_exchange=prev.from_exchange,
            )
    return sorted(by_id.values(), key=lambda c: (-c.abs_amount, c.process_id))


class BrightwayInventory:
    def __init__(self, metadata_lookup=None):
        self._metadata_lookup = metadata_lookup
        self._prod_cache: dict[int, dict[tuple[str, str], float]] = {}
        self._flow_heads_cache: dict[int, list[tuple[FlowKey, int]]] = {}
        self._node_cache: dict[int, object] = {}
        self._card_cache: dict[int, dict] = {}
        self._other_id_cache: dict[int, int | None] = {}
        self._role_cache: dict[int, str] = {}
        self._techno_cache: dict[int, list[tuple]] = {}
        self._consumer_rows_cache: dict[tuple[str, str], list[tuple[int, float]]] = {}
        self._consumer_count_cache: dict[tuple[str, str], int] = {}
        self._counterparts_cache: dict[tuple[int, FlowKey], list[Counterpart]] = {}
        self._market_cache: dict[int, bool] = {}

    def invalidate(self, process_id: int | None = None) -> None:
        """Drop cached inventory for one process, or all processes."""
        if process_id is None:
            self._prod_cache.clear()
            self._flow_heads_cache.clear()
            self._node_cache.clear()
            self._card_cache.clear()
            self._other_id_cache.clear()
            self._role_cache.clear()
            self._techno_cache.clear()
            self._consumer_rows_cache.clear()
            self._consumer_count_cache.clear()
            self._counterparts_cache.clear()
            self._market_cache.clear()
            return
        pid = int(process_id)
        self._prod_cache.pop(pid, None)
        self._flow_heads_cache.pop(pid, None)
        self._node_cache.pop(pid, None)
        self._card_cache.pop(pid, None)
        self._other_id_cache.pop(pid, None)
        self._role_cache.pop(pid, None)
        self._techno_cache.pop(pid, None)
        self._market_cache.pop(pid, None)
        self._consumer_rows_cache.clear()
        self._consumer_count_cache.clear()
        self._counterparts_cache = {
            key: value for key, value in self._counterparts_cache.items() if key[0] != pid
        }

    def _node(self, process_id: int):
        cached = self._node_cache.get(process_id)
        if cached is None:
            cached = bd.get_node(id=process_id)
            self._node_cache[process_id] = cached
        return cached

    def _is_waste_market(self, process_id: int) -> bool:
        cached = self._market_cache.get(process_id)
        if cached is not None:
            return cached
        try:
            kind = identify_activity_type(self._node(process_id))
        except Exception:
            kind = ""
        cached = kind in {"market", "marketgroup"}
        self._market_cache[process_id] = cached
        return cached

    def _prod_map(self, process_id: int) -> dict[tuple[str, str], float]:
        cached = self._prod_cache.get(process_id)
        if cached is None:
            cached = _production_map(self._node(process_id))
            self._prod_cache[process_id] = cached
        return cached

    def _other_process_id(self, exc) -> int | None:
        source = exc.input
        sid = getattr(source, "id", None)
        if sid is not None and sid in self._other_id_cache:
            return self._other_id_cache[sid]
        if _is_process(source):
            oid = source.id
        else:
            processors = list(source.upstream(kinds=["production"]))
            oid = processors[0].output.id if processors else None
        if sid is not None:
            self._other_id_cache[sid] = oid
        return oid

    def _flow_role(self, exc) -> str:
        inp = exc.input
        iid = getattr(inp, "id", None)
        if iid is not None and iid in self._role_cache:
            return self._role_cache[iid]
        raw = getattr(getattr(inp, "_document", None), "type", None)
        if raw == "waste":
            role = "waste"
        elif raw == "product":
            role = "product"
        else:
            role = None
            try:
                if is_node_waste(inp):
                    role = "waste"
                elif is_node_product(inp):
                    role = "product"
            except Exception:
                pass
            if role is None:
                amount = float(exc.get("amount") or 0)
                if _exchange_type(exc) == "production":
                    role = "waste" if amount < 0 else "product"
                elif amount < 0:
                    role = "waste"
                else:
                    role = "product"
        if iid is not None:
            self._role_cache[iid] = role
        return role

    def _style_pair(self, exc, source_id: int, target_id: int) -> tuple[str, str]:
        product, unit = _product_unit(exc, exc.input)
        key = (product, unit)
        amount = float(exc.get("amount") or 0)
        tgt_amt = self._prod_cache.get(target_id, {}).get(key)
        src_amt = self._prod_cache.get(source_id, {}).get(key)
        if _exchange_type(exc) == "production" and amount < 0:
            return "waste", "target"
        if tgt_amt is not None and tgt_amt < 0:
            return "waste", "target"
        if src_amt is not None and src_amt >= 0:
            return "product", "source"
        role = self._flow_role(exc)
        return role, _functional_end(role)

    def _exchange_layout(self, host_act, other_id: int, amount: float, exc) -> tuple:
        hid = host_act.id
        if hid not in self._prod_cache:
            self._prod_cache[hid] = _production_map(host_act)
        product, unit = _product_unit(exc, exc.input)
        if _exchange_type(exc) == "substitution":
            if amount >= 0:
                source, target = hid, other_id
            else:
                source, target = other_id, hid
            side = "upstream" if target == hid else "downstream"
            return side, source, target, product, unit, "substitution", None, amount
        role = self._flow_role(exc)
        host_treats = _host_treats_waste(self._prod_cache[hid], product, unit)
        other_treats = False
        if role == "waste" or host_treats or amount < 0:
            if other_id not in self._prod_cache:
                try:
                    self._prod_cache[other_id] = _production_map(self._node(other_id))
                except Exception:
                    self._prod_cache[other_id] = {}
            other_treats = _host_treats_waste(self._prod_cache[other_id], product, unit)
        source, target = _physical_endpoints(
            hid, other_id, amount,
            role=role,
            host_treats_waste=host_treats,
            other_treats_waste=other_treats,
            host_is_market=self._is_waste_market(hid),
        )
        styled_role, functional_at = self._style_pair(exc, source, target)
        side = "upstream" if target == hid else "downstream"
        return side, source, target, product, unit, styled_role, functional_at, amount

    def _techno_links(self, process_id: int) -> list[tuple]:
        cached = self._techno_cache.get(process_id)
        if cached is not None:
            return cached
        act = self._node(process_id)
        links = []
        for exc in list(act.technosphere()) + list(act.substitution()):
            oid = self._other_process_id(exc)
            if oid is None:
                continue
            amount = float(exc.get("amount") or 0)
            links.append(self._exchange_layout(act, oid, amount, exc))
        self._techno_cache[process_id] = links
        return links

    def _consumer_count(self, db: str, code: str) -> int:
        key = (db, code)
        cached = self._consumer_count_cache.get(key)
        if cached is not None:
            return cached
        n = (
            ExchangeDataset.select()
            .where(
                (ExchangeDataset.input_database == db)
                & (ExchangeDataset.input_code == code)
                & (ExchangeDataset.type != "production")
            )
            .count()
        )
        self._consumer_count_cache[key] = n
        return n

    def _consumer_rows(self, db: str, code: str) -> list[tuple[int, float]]:
        key = (db, code)
        cached = self._consumer_rows_cache.get(key)
        if cached is not None:
            return cached
        query = (
            ExchangeDataset
            .select(ActivityDataset.id.alias("process_id"), ExchangeDataset.data)
            .join(
                ActivityDataset,
                on=(
                    (ActivityDataset.database == ExchangeDataset.output_database)
                    & (ActivityDataset.code == ExchangeDataset.output_code)
                ),
            )
            .where(
                (ExchangeDataset.input_database == db)
                & (ExchangeDataset.input_code == code)
                & (ExchangeDataset.type != "production")
            )
        )
        found: dict[int, float] = {}
        for rec in query.dicts():
            amt = float((rec.get("data") or {}).get("amount") or 0)
            pid = rec.get("process_id")
            if pid is None:
                continue
            prev = found.get(pid)
            if prev is None or abs(amt) > abs(prev):
                found[int(pid)] = amt
        rows = list(found.items())
        self._consumer_rows_cache[key] = rows
        self._consumer_count_cache[key] = len(rows)
        return rows

    def _consumer_heads(self, act) -> list[tuple[FlowKey, int]]:
        heads = []
        for pe in act.production():
            inp = pe.input
            product, unit = _product_unit(pe, inp)
            amount = float(pe.get("amount") or 0)
            side = "upstream" if amount < 0 else "downstream"
            n = self._consumer_count(inp["database"], inp["code"])
            if n:
                heads.append((FlowKey(side, product, unit), n))
        return heads

    def _consumer_counterparts(self, act, key: FlowKey) -> list[Counterpart]:
        found: dict[int, float] = {}
        role = "product"
        for pe in act.production():
            inp = pe.input
            product, unit = _product_unit(pe, inp)
            if product != key.product or unit != key.unit:
                continue
            prod_amt = float(pe.get("amount") or 0)
            if prod_amt < 0:
                role = "waste"
                if key.side != "upstream":
                    continue
            elif key.side != "downstream":
                continue
            for pid, amt in self._consumer_rows(inp["database"], inp["code"]):
                prev = found.get(pid)
                if prev is None or abs(amt) > abs(prev):
                    found[pid] = amt
        return sorted(
            (
                Counterpart(pid, amt, role=role, functional_at=None, from_exchange=False)
                for pid, amt in found.items()
            ),
            key=lambda c: (-c.abs_amount, c.process_id),
        )

    def label(self, process_id: int) -> tuple[str, str | None]:
        card = self.card(process_id)
        return card["name"], card["location"] or None

    def card(self, process_id: int) -> dict:
        cached = self._card_cache.get(process_id)
        if cached is not None:
            return cached
        looked = self._metadata_lookup(int(process_id)) if self._metadata_lookup else None
        if looked:
            node_type = str(looked.get("type") or "")
            cached = {
                "name": str(looked.get("name") or ""),
                "location": str(looked.get("location") or ""),
                "database": str(looked.get("database") or ""),
                "product": str(looked.get("product") or ""),
                "multifunctional": node_type == "multifunctional",
            }
            if not cached["multifunctional"] and looked.get("type") is None:
                cached["multifunctional"] = len(self.functional_flows(process_id)) > 1
            self._card_cache[process_id] = cached
            return cached
        node = self._node(process_id)
        cached = {
            "name": node.get("name") or "",
            "location": node.get("location") or "",
            "database": node.get("database") or "",
            "product": node.get("reference product") or node.get("product") or "",
            "multifunctional": (
                (node.get("type") or "") == "multifunctional"
                or len(self.functional_flows(process_id)) > 1
            ),
        }
        self._card_cache[process_id] = cached
        return cached

    def flow_heads(self, process_id: int) -> list[tuple[FlowKey, int]]:
        cached = self._flow_heads_cache.get(process_id)
        if cached is not None:
            return cached
        buckets: dict[FlowKey, set[int]] = defaultdict(set)
        for side, source, target, product, unit, _role, _at, _amt in self._techno_links(process_id):
            oid = source if target == process_id else target
            buckets[FlowKey(side, product, unit)].add(oid)
        heads = [(key, len(ids)) for key, ids in buckets.items()]
        heads.extend(self._consumer_heads(self._node(process_id)))
        merged: dict[FlowKey, int] = {}
        for key, n in heads:
            merged[key] = max(merged.get(key, 0), n)
        cached = list(merged.items())
        self._flow_heads_cache[process_id] = cached
        return cached

    def counterparts_ranked(self, process_id: int, key: FlowKey) -> list[Counterpart]:
        cache_key = (process_id, key)
        cached = self._counterparts_cache.get(cache_key)
        if cached is not None:
            return cached
        act = self._node(process_id)
        found: dict[int, tuple[float, str, str | None]] = {}
        for side, source, target, product, unit, role, functional_at, amount in self._techno_links(process_id):
            if FlowKey(side, product, unit) != key:
                continue
            oid = source if target == process_id else target
            prev = found.get(oid)
            if prev is None or abs(amount) > abs(prev[0]):
                found[oid] = (amount, role, functional_at)
        techno = sorted(
            (
                Counterpart(pid, amt, role=role, functional_at=functional_at)
                for pid, (amt, role, functional_at) in found.items()
            ),
            key=lambda c: (-c.abs_amount, c.process_id),
        )
        cached = _merge_counterparts(techno, self._consumer_counterparts(act, key))
        self._counterparts_cache[cache_key] = cached
        return cached

    def host_flow_amount(self, process_id: int, key: FlowKey) -> float | None:
        found: list[float] = []
        for side, _source, _target, product, unit, _role, _at, amount in self._techno_links(process_id):
            if FlowKey(side, product, unit) == key:
                found.append(amount)
        if not found:
            return None
        return found[0] if len(found) == 1 else sum(found)

    def host_flow_style(self, process_id: int, key: FlowKey) -> tuple[str, str | None]:
        prod_amt = self._prod_map(process_id).get((key.product, key.unit))
        if prod_amt is not None and prod_amt < 0:
            return "waste", "target"
        if prod_amt is not None and prod_amt >= 0 and key.side == "downstream":
            return "product", "source"
        for side, _source, _target, product, unit, role, functional_at, _amount in self._techno_links(process_id):
            if FlowKey(side, product, unit) == key:
                return role, functional_at
        if key.side == "downstream":
            return "product", "source"
        return "product", None

    def functional_flows(self, process_id: int) -> list[tuple[FlowKey, float, str, str]]:
        act = self._node(process_id)
        out: list[tuple[FlowKey, float, str, str]] = []
        for pe in act.production():
            product, unit = _product_unit(pe, pe.input)
            amount = float(pe.get("amount") or 0)
            if amount < 0:
                out.append((FlowKey("upstream", product, unit), amount, "waste", "target"))
            else:
                out.append((FlowKey("downstream", product, unit), amount, "product", "source"))
        return out

    def pair_flows(self, process_ids: set[int]) -> list[PairFlow]:
        out: list[PairFlow] = []
        seen: set[tuple] = set()
        for pid in process_ids:
            for _side, source, target, product, unit, role, functional_at, amount in self._techno_links(pid):
                if source not in process_ids or target not in process_ids or source == target:
                    continue
                sig = (source, target, product, unit, amount)
                if sig in seen:
                    continue
                seen.add(sig)
                out.append(PairFlow(
                    source, target, product, amount, unit,
                    role=role, functional_at=functional_at,
                ))
        return out
