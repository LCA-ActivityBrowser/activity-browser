"""In-memory inventory for Graph explorer tests."""

from __future__ import annotations

from activity_browser.bwutils.graph_explorer.explorer import (
    Counterpart,
    FlowKey,
    PairFlow,
)


class TestInventory:
    __test__ = False

    def __init__(
        self,
        labels: dict[int, tuple[str, str | None]],
        groups: dict[int, list[tuple[FlowKey, list[Counterpart]]]],
    ):
        self._labels = labels
        self._groups = groups

    def label(self, process_id: int) -> tuple[str, str | None]:
        return self._labels[process_id]

    def card(self, process_id: int) -> dict:
        name, location = self._labels[process_id]
        return {
            "name": name,
            "location": location or "",
            "database": "",
            "product": "",
            "multifunctional": len(self.functional_flows(process_id)) > 1,
        }

    def flow_heads(self, process_id: int) -> list[tuple[FlowKey, int]]:
        return [(key, len(cs)) for key, cs in self._groups.get(process_id, [])]

    def counterparts_ranked(self, process_id: int, key: FlowKey) -> list[Counterpart]:
        for k, cs in self._groups.get(process_id, []):
            if k == key:
                return sorted(cs, key=lambda c: (-c.abs_amount, c.process_id))
        return []

    def host_flow_amount(self, process_id: int, key: FlowKey) -> float | None:
        for k, cs in self._groups.get(process_id, []):
            if k == key and cs:
                return cs[0].amount
        return None

    def host_flow_style(self, process_id: int, key: FlowKey) -> tuple[str, str | None]:
        for k, cs in self._groups.get(process_id, []):
            if k == key and cs:
                role = cs[0].role
                if role == "waste" and key.side == "upstream":
                    return role, "target"
                if role == "product" and key.side == "downstream":
                    return role, "source"
                return role, cs[0].functional_at
        if key.side == "downstream":
            return "product", "source"
        return "product", None

    def functional_flows(self, process_id: int) -> list[tuple[FlowKey, float, str, str]]:
        out: list[tuple[FlowKey, float, str, str]] = []
        for key, cs in self._groups.get(process_id, []):
            role, functional_at = self.host_flow_style(process_id, key)
            if role == "waste" and key.side != "upstream":
                continue
            if role == "product" and key.side != "downstream":
                continue
            if not functional_at:
                continue
            amount = cs[0].amount if cs else 0.0
            out.append((key, amount, role, functional_at))
        return out

    def pair_flows(self, process_ids: set[int]) -> list[PairFlow]:
        out: list[PairFlow] = []
        for host, groups in self._groups.items():
            if host not in process_ids:
                continue
            for key, cs in groups:
                for c in cs:
                    if c.process_id not in process_ids:
                        continue
                    if (
                        not c.from_exchange
                        and c.role != "substitution"
                        and any(
                            oc.role == "substitution" and oc.process_id == host
                            for _ok, ocs in self._groups.get(c.process_id, [])
                            for oc in ocs
                        )
                    ):
                        continue
                    if key.side == "upstream":
                        source, target = c.process_id, host
                    else:
                        source, target = host, c.process_id
                    functional_at = c.functional_at
                    if c.role == "substitution":
                        functional_at = None
                    elif functional_at is None:
                        functional_at = "target" if c.role == "waste" else "source"
                    out.append(PairFlow(
                        source, target, key.product, c.amount, key.unit,
                        role=c.role, functional_at=functional_at,
                    ))
        return out

    def invalidate(self, process_id: int | None = None) -> None:
        return
