"""Graph explorer visible graph — technosphere expand/collapse, not LCA graph_traversal."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Protocol

EXPAND_CAP = 10


def _display_amount(amount: float | None) -> float | None:
    """Label amount: physical quantity. Geometry already used the Brightway sign."""
    if amount is None:
        return None
    return abs(float(amount))


@dataclass(frozen=True)
class FlowKey:
    side: str
    product: str
    unit: str

    def as_dict(self) -> dict:
        return {"side": self.side, "product": self.product, "unit": self.unit}

    @classmethod
    def from_dict(cls, data: dict) -> FlowKey:
        return cls(side=data["side"], product=data["product"], unit=data["unit"])


@dataclass(frozen=True)
class Counterpart:
    process_id: int
    amount: float
    role: str = "product"
    functional_at: str | None = None
    from_exchange: bool = True

    @property
    def abs_amount(self) -> float:
        return abs(self.amount)


@dataclass(frozen=True)
class PairFlow:
    source_id: int
    target_id: int
    product: str
    amount: float
    unit: str
    role: str = "product"
    functional_at: str | None = None


class Inventory(Protocol):
    def label(self, process_id: int) -> tuple[str, str | None]: ...
    def flow_heads(self, process_id: int) -> list[tuple[FlowKey, int]]: ...
    def counterparts_ranked(self, process_id: int, key: FlowKey) -> list[Counterpart]: ...
    def pair_flows(self, process_ids: set[int]) -> list[PairFlow]: ...
    def host_flow_amount(self, process_id: int, key: FlowKey) -> float | None: ...
    def host_flow_style(self, process_id: int, key: FlowKey) -> tuple[str, str | None]: ...
    def functional_flows(self, process_id: int) -> list[tuple[FlowKey, float, str, str]]: ...


def _pid(process_id: int) -> str:
    return str(int(process_id))


class GraphExplorer:
    """Visible processes and which counterparts have been revealed per flow."""

    def __init__(self, center_id: int, inventory: Inventory):
        self.center_id = int(center_id)
        self.inventory = inventory
        self.visible: set[int] = {self.center_id}
        self._revealed: dict[tuple[int, FlowKey], set[int]] = {}
        self.selected_id: int | None = None
        self._open_incoming: set[int] = {self.center_id}
        self.direct_only = True
        self._paint_direct_neighbours()
        self._listed_known = self._listed_exchange_ids(self.center_id)

    def _shown(self, host_id: int, key: FlowKey) -> set[int]:
        return self._revealed.setdefault((int(host_id), key), set())

    def _listed_exchange_ids(self, host_id: int) -> set[tuple[FlowKey, int]]:
        found: set[tuple[FlowKey, int]] = set()
        for key, _count in self.inventory.flow_heads(host_id):
            for c in self.inventory.counterparts_ranked(host_id, key):
                if c.from_exchange:
                    found.add((key, c.process_id))
        return found

    def refresh_listed_exchanges(self) -> None:
        """Re-read listed inputs/outputs: show new counterparts and drop deleted ones."""
        invalidate = getattr(self.inventory, "invalidate", None)
        if callable(invalidate):
            invalidate(self.center_id)
        after = self._listed_exchange_ids(self.center_id)
        for key, cid in after - self._listed_known:
            self._shown(self.center_id, key).add(cid)
            self.visible.add(cid)
        drop: set[int] = set()
        for key, cid in self._listed_known - after:
            self._shown(self.center_id, key).discard(cid)
            drop.add(cid)
        still: set[int] = set()
        for ids in self._revealed.values():
            still |= ids
        drop -= still
        drop.discard(self.center_id)
        self.visible -= drop
        if self.selected_id in drop:
            self.selected_id = None
        self._open_incoming -= drop
        self._listed_known = after
        self._drop_unreachable()

    def _paint_direct_neighbours(self) -> None:
        """Listed inputs/outputs of the opened process (capped), not product consumers."""
        for side in ("upstream", "downstream"):
            pending: list[tuple[float, int, FlowKey, int]] = []
            for key, _count in self.inventory.flow_heads(self.center_id):
                if key.side != side:
                    continue
                for c in self.inventory.counterparts_ranked(self.center_id, key):
                    if not c.from_exchange:
                        continue
                    pending.append((-c.abs_amount, c.process_id, key, c.process_id))
            pending.sort()
            for _neg, _pid, key, cid in pending[:EXPAND_CAP]:
                self._shown(self.center_id, key).add(cid)
                self.visible.add(cid)

    def expand_flow(self, host_id: int, key: FlowKey, *, all_remaining: bool = False) -> None:
        host_id = int(host_id)
        if host_id not in self.visible:
            return
        ranked = self.inventory.counterparts_ranked(host_id, key)
        shown = self._shown(host_id, key)
        pending = [c for c in ranked if c.process_id not in shown]
        if host_id == self.center_id:
            func_keys = {k for k, *_ in self.inventory.functional_flows(self.center_id)}
            if key in func_keys:
                pending = [c for c in pending if not c.from_exchange]
        if all_remaining:
            if len(pending) > EXPAND_CAP:
                return
            take = pending
        else:
            take = pending[:EXPAND_CAP]
        for c in take:
            shown.add(c.process_id)
            self.visible.add(c.process_id)
        if key.side == "upstream":
            self._open_incoming.add(host_id)

    def expand_listed_side(self, host_id: int, side: str) -> None:
        self._expand_side(host_id, side, listed=True)

    def expand_side(self, host_id: int, side: str) -> None:
        host_id = int(host_id)
        if host_id != self.center_id:
            self._expand_side(host_id, side, listed=True)
            return
        listed_hidden, listed_shown, _ch, _cs = self._side_partition(host_id, side)
        restore_listed = listed_shown == 0 and listed_hidden > 0
        self._expand_side(host_id, side, listed=restore_listed)

    def _expand_side(self, host_id: int, side: str, *, listed: bool) -> None:
        host_id = int(host_id)
        if host_id not in self.visible:
            return
        pending: list[tuple[float, int, FlowKey, int]] = []
        for key, _count in self.inventory.flow_heads(host_id):
            if key.side != side:
                continue
            shown = self._shown(host_id, key)
            for c in self.inventory.counterparts_ranked(host_id, key):
                if c.process_id in shown:
                    continue
                if c.from_exchange != listed:
                    continue
                pending.append((-c.abs_amount, c.process_id, key, c.process_id))
        pending.sort()
        take = pending[:EXPAND_CAP]
        for _neg, _pid, key, cid in take:
            self._shown(host_id, key).add(cid)
            self.visible.add(cid)
        if side == "upstream" and take:
            self._open_incoming.add(host_id)

    def collapse_side(self, host_id: int, side: str) -> None:
        host_id = int(host_id)
        drop: set[int] = set()
        for (pid, key), ids in list(self._revealed.items()):
            if pid == host_id and key.side == side:
                drop |= set(ids)
                self._revealed[(pid, key)] = set()
        drop.discard(self.center_id)
        self.visible -= drop
        if self.selected_id in drop:
            self.selected_id = None
        self._open_incoming -= drop
        self._drop_unreachable()

    def remove_process(self, process_id: int) -> None:
        process_id = int(process_id)
        if process_id == self.center_id or process_id not in self.visible:
            return
        self.visible.remove(process_id)
        if self.selected_id == process_id:
            self.selected_id = None
        for ids in self._revealed.values():
            ids.discard(process_id)
        self._open_incoming.discard(process_id)
        self._drop_unreachable()

    def select(self, process_id: int) -> None:
        process_id = int(process_id)
        if process_id in self.visible:
            self.selected_id = process_id

    def _adjacency(self) -> dict[int, set[int]]:
        adj = {i: set() for i in self.visible}
        for pf in self._pair_list():
            if pf.source_id in adj and pf.target_id in adj:
                adj[pf.source_id].add(pf.target_id)
                adj[pf.target_id].add(pf.source_id)
        for (host, _key), ids in self._revealed.items():
            if host not in adj:
                continue
            for cid in ids:
                if cid in adj:
                    adj[host].add(cid)
                    adj[cid].add(host)
        return adj

    def _drop_unreachable(self) -> None:
        adj = self._adjacency()
        seen = {self.center_id}
        stack = [self.center_id]
        while stack:
            node = stack.pop()
            for nxt in adj.get(node, ()):
                if nxt not in seen and nxt in self.visible:
                    seen.add(nxt)
                    stack.append(nxt)
        gone = self.visible - seen
        self.visible = seen
        self._open_incoming &= seen
        if self.selected_id in gone:
            self.selected_id = None
        for key in list(self._revealed):
            host, flow = key
            if host not in self.visible:
                del self._revealed[key]
            else:
                self._revealed[key] &= self.visible

    def _allowed_direct_edges(self) -> dict[int, set[tuple[int, str, str]]]:
        """host -> {(counterpart, product, unit)} from expands / first paint."""
        allowed: dict[int, set[tuple[int, str, str]]] = {}
        for (host, key), ids in self._revealed.items():
            if host not in self.visible:
                continue
            bucket = allowed.setdefault(host, set())
            for cid in ids:
                if cid in self.visible:
                    bucket.add((cid, key.product, key.unit))
        return allowed

    def _direct_pair_flows(self) -> list[PairFlow]:
        allowed = self._allowed_direct_edges()
        if not allowed:
            return []
        hosts = set(allowed)
        others = {cid for pairs in allowed.values() for cid, _p, _u in pairs}
        raw = self.inventory.pair_flows(hosts | others)
        out: list[PairFlow] = []
        seen: set[tuple] = set()
        for pf in raw:
            sig = (pf.source_id, pf.target_id, pf.product, pf.unit, pf.amount)
            if sig in seen:
                continue
            a = allowed.get(pf.source_id, ())
            b = allowed.get(pf.target_id, ())
            if (pf.target_id, pf.product, pf.unit) not in a and (
                pf.source_id, pf.product, pf.unit
            ) not in b:
                continue
            seen.add(sig)
            out.append(pf)
        return out

    def _pair_list(self) -> list[PairFlow]:
        if self.direct_only:
            return self._direct_pair_flows()
        return list(self.inventory.pair_flows(self.visible))

    def _key_split(self, host_id: int, key: FlowKey) -> tuple[int, int, int, int]:
        shown = self._shown(host_id, key)
        listed_hidden = listed_shown = cons_hidden = cons_shown = 0
        for c in self.inventory.counterparts_ranked(host_id, key):
            if c.from_exchange:
                visible = c.process_id in shown or c.process_id in self.visible
                if visible:
                    listed_shown += 1
                else:
                    listed_hidden += 1
            elif c.process_id in shown:
                cons_shown += 1
            else:
                cons_hidden += 1
        return listed_hidden, listed_shown, cons_hidden, cons_shown

    def _side_partition(
        self,
        host_id: int,
        side: str,
        *,
        heads: list[tuple[FlowKey, int]] | None = None,
    ) -> tuple[int, int, int, int]:
        if heads is None:
            heads = self.inventory.flow_heads(host_id)
        listed_hidden = listed_shown = cons_hidden = cons_shown = 0
        for key, _count in heads:
            if key.side != side:
                continue
            lh, ls, ch, cs = self._key_split(host_id, key)
            listed_hidden += lh
            listed_shown += ls
            cons_hidden += ch
            cons_shown += cs
        return listed_hidden, listed_shown, cons_hidden, cons_shown

    def _side_flags(
        self,
        host_id: int,
        side: str,
        *,
        heads: list[tuple[FlowKey, int]] | None = None,
    ) -> tuple[bool, bool]:
        listed_hidden, listed_shown, cons_hidden, cons_shown = self._side_partition(
            host_id, side, heads=heads,
        )
        collapse = (listed_shown + cons_shown) > 0
        if host_id == self.center_id:
            expand = cons_hidden > 0 or (listed_hidden > 0 and listed_shown == 0)
            return expand, collapse
        any_hidden = (listed_hidden + cons_hidden) > 0
        return any_hidden and not collapse, collapse

    def _layout_ranks(self, pair_list: list[PairFlow] | None = None) -> dict[int, int]:
        """Hop distance from center: upstream left (negative), downstream right (positive)."""
        if pair_list is None:
            pair_list = self._pair_list()
        center = self.center_id
        forward: dict[int, set[int]] = {i: set() for i in self.visible}
        backward: dict[int, set[int]] = {i: set() for i in self.visible}
        for pf in pair_list:
            if pf.source_id in self.visible and pf.target_id in self.visible:
                forward[pf.source_id].add(pf.target_id)
                backward[pf.target_id].add(pf.source_id)

        ranks: dict[int, int] = {center: 0}

        queue: deque[tuple[int, int]] = deque([(center, 0)])
        seen = {center}
        while queue:
            node, depth = queue.popleft()
            for nxt in forward.get(node, ()):
                if nxt in seen:
                    continue
                seen.add(nxt)
                ranks[nxt] = depth + 1
                queue.append((nxt, depth + 1))

        queue = deque([(center, 0)])
        seen = {center}
        while queue:
            node, depth = queue.popleft()
            for prev in backward.get(node, ()):
                if prev in seen:
                    continue
                seen.add(prev)
                ranks[prev] = -(depth + 1)
                queue.append((prev, depth + 1))

        for pid in self.visible:
            if pid in ranks:
                continue
            for (host, key), ids in self._revealed.items():
                if pid not in ids or host not in ranks:
                    continue
                ranks[pid] = ranks[host] - 1 if key.side == "upstream" else ranks[host] + 1
                break
            if pid not in ranks:
                ranks[pid] = 1
        return ranks

    def payload(self) -> dict:
        nodes: list[dict] = []
        edges: list[dict] = []
        edge_i = 0
        pair_list = self._pair_list()
        ranks = self._layout_ranks(pair_list)
        flow_heads_cache: dict[int, list[tuple[FlowKey, int]]] = {}

        def flow_heads(host_id: int) -> list[tuple[FlowKey, int]]:
            cached = flow_heads_cache.get(host_id)
            if cached is None:
                cached = self.inventory.flow_heads(host_id)
                flow_heads_cache[host_id] = cached
            return cached

        for pid in sorted(self.visible):
            card = self.inventory.card(pid) if hasattr(self.inventory, "card") else {}
            if not card:
                name, location = self.inventory.label(pid)
                card = {"name": name, "location": location or "", "database": "", "product": ""}
            heads = flow_heads(pid)
            up_exp, up_col = self._side_flags(pid, "upstream", heads=heads)
            down_exp, down_col = self._side_flags(pid, "downstream", heads=heads)
            nodes.append({
                "id": f"p:{_pid(pid)}",
                "kind": "process",
                "process_id": _pid(pid),
                "name": card.get("name") or "",
                "location": card.get("location") or "",
                "database": card.get("database") or "",
                "product": card.get("product") or "",
                "is_center": pid == self.center_id,
                "selected": pid == self.selected_id,
                "expand_upstream": up_exp,
                "collapse_upstream": up_col,
                "expand_downstream": down_exp,
                "collapse_downstream": down_col,
                "rank": ranks.get(pid, 0),
                "multifunctional": bool(card.get("multifunctional")),
            })

        emitted_pairs: set[tuple] = set()
        for pf in pair_list:
            sig = (pf.source_id, pf.target_id, pf.product, pf.unit, pf.amount)
            if sig in emitted_pairs:
                continue
            emitted_pairs.add(sig)
            func_key = self._center_functional_key(pf)
            edges.append({
                "id": f"e:{edge_i}",
                "source_id": f"p:{_pid(pf.source_id)}",
                "target_id": f"p:{_pid(pf.target_id)}",
                "product": pf.product,
                "amount": _display_amount(pf.amount),
                "unit": pf.unit,
                "amount_unit": pf.unit,
                "kind": "flow",
                "role": pf.role,
                "functional_at": pf.functional_at,
                "center_functional": func_key is not None,
                "flow": None if func_key is None else func_key.as_dict(),
            })
            edge_i += 1

        emitted_stubs: set[tuple[int, FlowKey]] = set()
        remainder_left: dict[tuple[int, str], tuple[int, int]] = {}

        def note_side_remainder(host_id: int, heads: list[tuple[FlowKey, int]]) -> None:
            for side in ("upstream", "downstream"):
                listed_hidden, listed_shown, _ch, _cs = self._side_partition(
                    host_id, side, heads=heads,
                )
                if listed_hidden > 0 and listed_shown > 0:
                    remainder_left[(host_id, side)] = (listed_hidden, listed_shown)

        for key, amount, role, functional_at in self.inventory.functional_flows(self.center_id):
            _lh, _ls, cons_hidden, cons_shown = self._key_split(self.center_id, key)
            covered = self._pair_covers_functional(self.center_id, key, pair_list)
            if cons_hidden > 0:
                rnode, redge = self._functional_remainder_payload(
                    edge_i, key, amount, role, functional_at, cons_hidden, cons_shown,
                )
                nodes.append(rnode)
                edges.append(redge)
                emitted_stubs.add((self.center_id, key))
                edge_i += 1
            elif not covered:
                edges.append(self._stub_payload(
                    edge_i, self.center_id, key, amount, cons_hidden, cons_shown,
                    role, functional_at,
                ))
                emitted_stubs.add((self.center_id, key))
                edge_i += 1

        note_side_remainder(self.center_id, flow_heads(self.center_id))

        for host_id in sorted(self.visible):
            heads = flow_heads(host_id)
            if host_id != self.center_id:
                note_side_remainder(host_id, heads)
            for key, _count in heads:
                if (host_id, key) in emitted_stubs:
                    continue
                if key.side == "upstream" and host_id not in self._open_incoming:
                    continue
                listed_hidden, listed_shown, _ch, _cs = self._key_split(host_id, key)
                if listed_hidden <= 0:
                    continue
                can_all = listed_hidden <= EXPAND_CAP
                amount = self.inventory.host_flow_amount(host_id, key)
                role, functional_at = self.inventory.host_flow_style(host_id, key)
                stub_functional_at = functional_at
                if role == "product" and key.side == "upstream":
                    stub_functional_at = None
                elif role == "waste" and key.side == "downstream":
                    stub_functional_at = None
                edges.append({
                    "id": f"s:{edge_i}",
                    "kind": "stub",
                    "host_process_id": _pid(host_id),
                    "side": key.side,
                    "product": key.product,
                    "amount": _display_amount(amount),
                    "unit": key.unit,
                    "amount_unit": key.unit,
                    "hidden_count": listed_hidden,
                    "expandable": True,
                    "can_expand_all": can_all and listed_shown > 0,
                    "flow": key.as_dict(),
                    "is_center_host": host_id == self.center_id,
                    "role": role,
                    "functional_at": stub_functional_at,
                })
                edge_i += 1

        for host_id, side in sorted(remainder_left):
            leftover, shown = remainder_left[(host_id, side)]
            rnode, redge = self._remainder_payload(edge_i, host_id, side, leftover, shown)
            nodes.append(rnode)
            edges.append(redge)
            edge_i += 1

        return {"nodes": nodes, "edges": edges, "center_id": _pid(self.center_id)}

    def _center_functional_key(self, pf: PairFlow) -> FlowKey | None:
        if pf.role == "substitution":
            return None
        for key, _amount, _role, _at in self.inventory.functional_flows(self.center_id):
            if pf.product != key.product or (pf.unit or "") != (key.unit or ""):
                continue
            if key.side == "downstream" and pf.source_id == self.center_id:
                return key
            if key.side == "upstream" and pf.target_id == self.center_id:
                return key
        return None

    def _pair_covers_functional(self, host_id: int, key: FlowKey, pairs: list[PairFlow]) -> bool:
        for pf in pairs:
            if pf.product != key.product or pf.unit != key.unit:
                continue
            if pf.role == "substitution" and host_id in (pf.source_id, pf.target_id):
                return True
            if key.side == "downstream" and pf.source_id == host_id:
                return True
            if key.side == "upstream" and pf.target_id == host_id:
                return True
        return False

    def _stub_payload(
        self,
        edge_i: int,
        host_id: int,
        key: FlowKey,
        amount: float | None,
        leftover: int,
        shown: int,
        role: str,
        functional_at: str | None,
    ) -> dict:
        can_all = leftover <= EXPAND_CAP
        center_func = host_id == self.center_id and bool(functional_at)
        return {
            "id": f"s:{edge_i}",
            "kind": "stub",
            "host_process_id": _pid(host_id),
            "side": key.side,
            "product": key.product,
            "amount": _display_amount(amount),
            "unit": key.unit,
            "amount_unit": key.unit,
            "hidden_count": leftover,
            "expandable": leftover > 0,
            "can_expand_all": can_all and shown > 0 and leftover > 0,
            "flow": key.as_dict(),
            "is_center_host": host_id == self.center_id,
            "center_functional": center_func,
            "role": role,
            "functional_at": functional_at,
        }

    def _remainder_payload(
        self,
        edge_i: int,
        host_id: int,
        side: str,
        leftover: int,
        shown: int,
    ) -> tuple[dict, dict]:
        rid = f"r:{edge_i}"
        hid = f"p:{_pid(host_id)}"
        if side == "upstream":
            source, target = rid, hid
        else:
            source, target = hid, rid
        node = {
            "id": rid,
            "kind": "remainder",
            "host_process_id": _pid(host_id),
            "side": side,
            "hidden_count": leftover,
            "can_expand_all": leftover <= EXPAND_CAP and shown > 0,
            "expandable": leftover > 0,
        }
        edge = {
            "id": f"re:{edge_i}",
            "kind": "remainder",
            "source_id": source,
            "target_id": target,
            "host_process_id": _pid(host_id),
            "side": side,
        }
        return node, edge

    def _functional_remainder_payload(
        self,
        edge_i: int,
        key: FlowKey,
        amount: float | None,
        role: str,
        functional_at: str | None,
        leftover: int,
        shown: int,
    ) -> tuple[dict, dict]:
        rid = f"r:{edge_i}"
        hid = f"p:{_pid(self.center_id)}"
        bucket = "suppliers" if key.side == "upstream" else "consumers"
        if key.side == "upstream":
            source, target = rid, hid
        else:
            source, target = hid, rid
        node = {
            "id": rid,
            "kind": "remainder",
            "bucket": bucket,
            "host_process_id": _pid(self.center_id),
            "side": key.side,
            "hidden_count": leftover,
            "can_expand_all": leftover <= EXPAND_CAP and shown > 0,
            "expandable": leftover > 0,
            "flow": key.as_dict(),
            "product": key.product,
            "amount": _display_amount(amount),
            "unit": key.unit,
        }
        edge = {
            "id": f"rf:{edge_i}",
            "kind": "flow",
            "source_id": source,
            "target_id": target,
            "product": key.product,
            "amount": _display_amount(amount),
            "unit": key.unit,
            "amount_unit": key.unit,
            "role": role,
            "functional_at": functional_at,
            "center_functional": True,
            "flow": key.as_dict(),
            "host_process_id": _pid(self.center_id),
            "side": key.side,
        }
        return node, edge


def process_nodes(payload: dict) -> list[dict]:
    return [n for n in payload["nodes"] if n["kind"] == "process"]


def stub_edges(payload: dict) -> list[dict]:
    return [e for e in payload["edges"] if e.get("kind") == "stub"]


def remainder_nodes(payload: dict) -> list[dict]:
    return [n for n in payload["nodes"] if n.get("kind") == "remainder"]
