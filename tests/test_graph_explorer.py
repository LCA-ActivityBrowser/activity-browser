"""Graph explorer expand / collapse / stub flows (no Qt)."""

from graph_explorer_test_data import TestInventory

from activity_browser.bwutils.graph_explorer.explorer import (
    EXPAND_CAP,
    Counterpart,
    FlowKey,
    GraphExplorer,
    process_nodes,
    remainder_nodes,
    stub_edges,
)
from activity_browser.bwutils.graph_explorer.inventory import (
    _physical_endpoints,
    _physical_side,
)

UP = FlowKey("upstream", "electricity", "kilowatt hour")
DOWN = FlowKey("downstream", "electricity", "kilowatt hour")


def _inv_center_only():
    labels = {
        1: ("trichloroethane", "GLO"),
        2: ("electricity market", "World"),
        3: ("consumer", "GLO"),
    }
    groups = {
        1: [
            (UP, [Counterpart(2, 0.5)]),
            (DOWN, [Counterpart(3, 1.0, from_exchange=False)]),
        ],
    }
    return TestInventory(labels, groups)


def _inv_twenty_five_down():
    labels = {1: ("market group", "World")}
    downs = [Counterpart(10 + i, 100 - i, from_exchange=False) for i in range(25)]
    for c in downs:
        labels[c.process_id] = (f"consumer {c.process_id}", "GLO")
    groups = {1: [(DOWN, downs)]}
    return TestInventory(labels, groups)


def test_first_paint_caps_direct_downstream():
    ge = GraphExplorer(1, _inv_twenty_five_down())
    payload = ge.payload()
    assert len(process_nodes(payload)) == 1
    assert stub_edges(payload) == []
    rems = remainder_nodes(payload)
    assert len(rems) == 1
    assert rems[0]["bucket"] == "consumers"
    assert rems[0]["hidden_count"] == 25
    assert rems[0]["side"] == "downstream"
    flows = [e for e in payload["edges"] if e["kind"] == "flow"]
    assert any(e.get("center_functional") for e in flows)
    center = next(n for n in process_nodes(payload) if n["is_center"])
    assert center["expand_downstream"] is True
    assert center["collapse_downstream"] is False


def test_first_paint_sorts_mixed_upstream_products():
    labels = {1: ("root", "GLO"), 2: ("chlorine", "RER"), 3: ("vinyl", "GLO")}
    chlorine = FlowKey("upstream", "chlorine, liquid", "kilogram")
    vinyl = FlowKey("upstream", "vinyl chloride", "kilogram")
    groups = {
        1: [
            (chlorine, [Counterpart(2, 0.4)]),
            (vinyl, [Counterpart(3, 0.6)]),
        ],
    }
    ge = GraphExplorer(1, TestInventory(labels, groups))
    ids = {n["process_id"] for n in process_nodes(ge.payload())}
    assert ids == {"1", "2", "3"}


def test_listed_remainder_excludes_consumers():
    waste = FlowKey("downstream", "wastewater", "cubic meter")
    labels = {1: ("factory", "GLO"), 2: ("supplier", "GLO"), 3: ("consumer", "GLO")}
    wastes = []
    for i in range(4):
        pid = 20 + i
        labels[pid] = (f"ww {i}", "GLO")
        wastes.append(Counterpart(pid, 1.0, role="waste"))
    groups = {
        1: [
            (UP, [Counterpart(2, 0.5)]),
            (waste, wastes),
            (DOWN, [Counterpart(3, 1.0, from_exchange=False)]),
        ],
    }
    ge = GraphExplorer(1, TestInventory(labels, groups))
    payload = ge.payload()
    ids = {n["process_id"] for n in process_nodes(payload)}
    assert "3" not in ids
    assert {"20", "21", "22", "23"} <= ids
    rems = remainder_nodes(payload)
    assert len(rems) == 1
    assert rems[0]["bucket"] == "consumers"
    assert rems[0]["hidden_count"] == 1
    assert stub_edges(payload) == []
    center = next(n for n in process_nodes(payload) if n["is_center"])
    assert center["expand_downstream"] is True
    ge.expand_side(1, "downstream")
    ids = {n["process_id"] for n in process_nodes(ge.payload())}
    assert "3" in ids
    assert stub_edges(ge.payload()) == []
    assert remainder_nodes(ge.payload()) == []


def test_expand_listed_side_pages_remainder():
    labels = {1: ("root", "GLO")}
    ups = [Counterpart(10 + i, 100 - i) for i in range(25)]
    for c in ups:
        labels[c.process_id] = (f"supplier {c.process_id}", "GLO")
    ge = GraphExplorer(1, TestInventory(labels, {1: [(UP, ups)]}))
    assert len(process_nodes(ge.payload())) == 1 + EXPAND_CAP
    ge.expand_side(1, "upstream")
    assert len(process_nodes(ge.payload())) == 1 + EXPAND_CAP
    ge.expand_listed_side(1, "upstream")
    assert len(process_nodes(ge.payload())) == 21


def test_first_paint_shows_listed_inputs_not_consumers():
    ge = GraphExplorer(1, _inv_center_only())
    payload = ge.payload()
    ids = {n["process_id"] for n in process_nodes(payload)}
    assert ids == {"1", "2"}
    flows = [e for e in payload["edges"] if e["kind"] == "flow"]
    assert any(e["source_id"] == "p:2" and e["target_id"] == "p:1" for e in flows)
    assert not any(e["target_id"] == "p:3" for e in flows)
    assert stub_edges(payload) == []
    rems = remainder_nodes(payload)
    assert len(rems) == 1
    assert rems[0]["bucket"] == "consumers"
    assert rems[0]["product"] == "electricity"


def test_first_paint_caps_direct_upstream():
    labels = {1: ("root", "GLO")}
    ups = [Counterpart(10 + i, 100 - i) for i in range(25)]
    for c in ups:
        labels[c.process_id] = (f"supplier {c.process_id}", "GLO")
    groups = {1: [(UP, ups)]}
    ge = GraphExplorer(1, TestInventory(labels, groups))
    payload = ge.payload()
    procs = process_nodes(payload)
    assert len(procs) == 1 + EXPAND_CAP
    stubs = stub_edges(payload)
    assert len(stubs) == 1
    assert stubs[0]["side"] == "upstream"
    assert stubs[0]["hidden_count"] == 15
    leftover_hosts = {s["host_process_id"] for s in stubs}
    assert leftover_hosts == {"1"}
    rems = remainder_nodes(payload)
    assert len(rems) == 1
    assert rems[0]["hidden_count"] == 15
    assert rems[0]["side"] == "upstream"


def test_remainder_aggregates_mixed_upstream_products():
    labels = {1: ("root", "GLO")}
    groups = []
    pid = 10
    for i, product in enumerate(("vinyl A", "vinyl B", "chlorine")):
        key = FlowKey("upstream", product, "kilogram")
        big, small = pid, pid + 1
        labels[big] = (f"market {product}", "GLO")
        labels[small] = (f"other {product}", "GLO")
        groups.append((key, [Counterpart(big, 20 - i), Counterpart(small, 0.1)]))
        pid += 2
    for j in range(8):
        key = FlowKey("upstream", f"other {j}", "kilogram")
        labels[pid] = (f"single {j}", "GLO")
        groups.append((key, [Counterpart(pid, 10 - j)]))
        pid += 1
    ge = GraphExplorer(1, TestInventory(labels, {1: groups}))
    payload = ge.payload()
    assert len(process_nodes(payload)) == 1 + EXPAND_CAP
    rems = remainder_nodes(payload)
    assert len(rems) == 1
    assert rems[0]["side"] == "upstream"
    assert rems[0]["hidden_count"] == 4


def test_first_paint_pages_consumers_with_triangle_not_remainder():
    ge = GraphExplorer(1, _inv_twenty_five_down())
    center = next(n for n in process_nodes(ge.payload()) if n["is_center"])
    assert center["expand_downstream"] is True
    rems = remainder_nodes(ge.payload())
    assert len(rems) == 1
    assert rems[0]["bucket"] == "consumers"
    assert rems[0]["hidden_count"] == 25
    ge.expand_side(1, "downstream")
    center = next(n for n in process_nodes(ge.payload()) if n["is_center"])
    assert center["expand_downstream"] is True
    assert center["collapse_downstream"] is True
    assert len(process_nodes(ge.payload())) == 1 + EXPAND_CAP
    rems = remainder_nodes(ge.payload())
    assert len(rems) == 1
    assert rems[0]["hidden_count"] == 15
    assert stub_edges(ge.payload()) == []
    ge.expand_side(1, "downstream")
    assert len(process_nodes(ge.payload())) == 21
    assert remainder_nodes(ge.payload())[0]["hidden_count"] == 5


def test_center_functional_flow_without_consumers():
    labels = {1: ("power plant", "GLO")}
    groups = {1: [(DOWN, [])]}
    ge = GraphExplorer(1, TestInventory(labels, groups))
    stubs = stub_edges(ge.payload())
    assert len(stubs) == 1
    assert stubs[0]["is_center_host"]
    assert stubs[0]["functional_at"] == "source"
    assert stubs[0]["expandable"] is False


def test_center_functional_flow_not_replaced_by_unshown_consumers():
    ge = GraphExplorer(1, _inv_center_only())
    flows = [e for e in ge.payload()["edges"] if e["kind"] == "flow"]
    assert not any(e["target_id"] == "p:3" for e in flows)
    assert stub_edges(ge.payload()) == []
    rems = remainder_nodes(ge.payload())
    assert len(rems) == 1
    assert rems[0]["bucket"] == "consumers"
    assert any(e.get("center_functional") for e in flows)


def test_first_paint_includes_center_flow_amounts():
    ge = GraphExplorer(1, _inv_center_only())
    flows = [e for e in ge.payload()["edges"] if e["kind"] == "flow"]
    by_target = {e["target_id"]: e for e in flows}
    assert by_target["p:1"]["amount"] == 0.5
    func = next(e for e in flows if e.get("center_functional"))
    assert func["amount"] == 1.0


def test_product_flow_is_functional_at_producer():
    ge = GraphExplorer(1, _inv_center_only())
    func = next(e for e in ge.payload()["edges"] if e["kind"] == "flow" and e.get("center_functional"))
    assert func["role"] == "product"
    assert func["functional_at"] == "source"
    ge.expand_side(1, "downstream")
    flows = [e for e in ge.payload()["edges"] if e["kind"] == "flow"]
    down = next(e for e in flows if e["target_id"] == "p:3")
    assert down["role"] == "product"
    assert down["functional_at"] == "source"
    up = next(e for e in flows if e["source_id"] == "p:2")
    assert up["role"] == "product"
    assert up["functional_at"] == "source"


def test_expanded_neighbour_does_not_show_its_incoming_stubs():
    labels = {1: ("root", None), 2: ("mid", None), 3: ("leaf", None)}
    mid_up = FlowKey("upstream", "a", "kg")
    leaf_up = FlowKey("upstream", "b", "kg")
    groups = {
        1: [(mid_up, [Counterpart(2, 1)])],
        2: [(leaf_up, [Counterpart(3, 1)])],
        3: [],
    }
    ge = GraphExplorer(1, TestInventory(labels, groups))
    payload = ge.payload()
    assert {n["process_id"] for n in process_nodes(payload)} == {"1", "2"}
    assert stub_edges(payload) == []
    ge.expand_side(2, "upstream")
    payload = ge.payload()
    ids = {n["process_id"] for n in process_nodes(payload)}
    assert ids == {"1", "2", "3"}
    assert stub_edges(payload) == []


def test_waste_input_is_functional_at_target_and_dashed():
    waste = FlowKey("upstream", "hazardous waste", "kilogram")
    labels = {1: ("incineration", "GLO"), 2: ("generator", "GLO")}
    groups = {
        1: [(waste, [Counterpart(2, -1.0, role="waste")])],
    }
    ge = GraphExplorer(1, TestInventory(labels, groups))
    payload = ge.payload()
    ids = {n["process_id"] for n in process_nodes(payload)}
    assert ids == {"1", "2"}
    flows = [e for e in payload["edges"] if e["kind"] == "flow"]
    assert len(flows) == 1
    assert flows[0]["role"] == "waste"
    assert flows[0]["functional_at"] == "target"
    assert flows[0]["source_id"] == "p:2"
    assert flows[0]["target_id"] == "p:1"
    assert flows[0]["amount"] == 1.0


def test_waste_output_is_downstream_on_first_paint():
    waste = FlowKey("downstream", "hazardous waste", "kilogram")
    labels = {1: ("factory", "GLO"), 2: ("incineration", "GLO")}
    groups = {
        1: [(waste, [Counterpart(2, 1.0, role="waste", functional_at="target")])],
    }
    ge = GraphExplorer(1, TestInventory(labels, groups))
    payload = ge.payload()
    ids = {n["process_id"] for n in process_nodes(payload)}
    assert ids == {"1", "2"}
    flows = [e for e in payload["edges"] if e["kind"] == "flow"]
    assert len(flows) == 1
    assert flows[0]["role"] == "waste"
    assert flows[0]["source_id"] == "p:1"
    assert flows[0]["target_id"] == "p:2"
    assert flows[0]["amount"] == 1.0


def test_waste_into_treatment_is_upstream():
    assert _physical_side(1, 2, -1.0, role="waste", host_treats_waste=True) == "upstream"
    assert _physical_endpoints(1, 2, -1.0, role="waste", host_treats_waste=True) == (2, 1)


def test_waste_from_generator_is_downstream():
    assert _physical_side(1, 2, 1.0, role="waste", host_treats_waste=False) == "downstream"
    assert _physical_endpoints(1, 2, 1.0, role="waste", host_treats_waste=False) == (1, 2)
    assert _physical_side(1, 2, 1.0, role="product", other_treats_waste=True) == "downstream"
    assert _physical_endpoints(1, 2, 1.0, role="product", other_treats_waste=True) == (1, 2)


def test_waste_market_mix_is_downstream():
    assert _physical_side(
        1, 2, 1.0, role="waste",
        host_treats_waste=True, other_treats_waste=True, host_is_market=True,
    ) == "downstream"
    assert _physical_endpoints(
        1, 2, 1.0, role="waste",
        host_treats_waste=True, other_treats_waste=True, host_is_market=True,
    ) == (1, 2)


def test_waste_treatment_market_input_stays_upstream():
    assert _physical_side(
        1, 2, 1.0, role="waste",
        host_treats_waste=True, other_treats_waste=True, host_is_market=False,
    ) == "upstream"
    assert _physical_endpoints(
        1, 2, 1.0, role="waste",
        host_treats_waste=True, other_treats_waste=True, host_is_market=False,
    ) == (2, 1)


def test_layout_ranks_place_suppliers_left_and_consumers_right():
    ge = GraphExplorer(1, _inv_center_only())
    ge.expand_side(1, "downstream")
    ranks = {n["process_id"]: n["rank"] for n in process_nodes(ge.payload())}
    assert ranks["1"] == 0
    assert ranks["2"] < 0
    assert ranks["3"] > 0


def test_refresh_listed_exchanges_shows_new_input():
    ge = GraphExplorer(1, _inv_center_only())
    assert {n["process_id"] for n in process_nodes(ge.payload())} == {"1", "2"}
    extra = FlowKey("upstream", "heat", "megajoule")
    ge.inventory._groups[1].append((extra, [Counterpart(9, 0.2)]))
    ge.inventory._labels[9] = ("heat plant", "GLO")
    ge.refresh_listed_exchanges()
    ids = {n["process_id"] for n in process_nodes(ge.payload())}
    assert ids == {"1", "2", "9"}
    flows = [e for e in ge.payload()["edges"] if e["kind"] == "flow"]
    assert any(e["source_id"] == "p:9" and e["target_id"] == "p:1" for e in flows)


def test_refresh_listed_exchanges_removes_deleted_input():
    ge = GraphExplorer(1, _inv_center_only())
    assert {n["process_id"] for n in process_nodes(ge.payload())} == {"1", "2"}
    ge.inventory._groups[1] = [
        (DOWN, [Counterpart(3, 1.0, from_exchange=False)]),
    ]
    ge.refresh_listed_exchanges()
    ids = {n["process_id"] for n in process_nodes(ge.payload())}
    assert ids == {"1"}
    flows = [e for e in ge.payload()["edges"] if e["kind"] == "flow"]
    assert not any(e["source_id"] == "p:2" or e["target_id"] == "p:2" for e in flows)


def test_refresh_listed_exchanges_does_not_dump_remainder():
    labels = {1: ("root", "GLO")}
    ups = [Counterpart(10 + i, 100 - i) for i in range(25)]
    for c in ups:
        labels[c.process_id] = (f"supplier {c.process_id}", "GLO")
    groups = {1: [(UP, list(ups))]}
    ge = GraphExplorer(1, TestInventory(labels, groups))
    assert len(process_nodes(ge.payload())) == 1 + EXPAND_CAP
    extra = FlowKey("upstream", "new input", "kilogram")
    ge.inventory._groups[1].append((extra, [Counterpart(99, 1.0)]))
    ge.inventory._labels[99] = ("dropped", "GLO")
    ge.refresh_listed_exchanges()
    ids = {n["process_id"] for n in process_nodes(ge.payload())}
    assert "99" in ids
    assert len(ids) == 1 + EXPAND_CAP + 1


def test_first_paint_includes_opened_process():
    ge = GraphExplorer(1, _inv_center_only())
    ids = {n["process_id"] for n in process_nodes(ge.payload())}
    assert "1" in ids


def test_expand_flow_caps_at_ten_and_connects():
    ge = GraphExplorer(1, _inv_twenty_five_down())
    payload = ge.payload()
    assert len(process_nodes(payload)) == 1
    ge.expand_flow(1, DOWN)
    payload = ge.payload()
    procs = process_nodes(payload)
    assert len(procs) == 1 + EXPAND_CAP
    assert stub_edges(payload) == []
    rems = remainder_nodes(payload)
    assert len(rems) == 1
    assert rems[0]["bucket"] == "consumers"
    assert rems[0]["hidden_count"] == 15
    flows = [e for e in payload["edges"] if e["kind"] == "flow"]
    assert any(e.get("center_functional") for e in flows)
    ge.expand_flow(1, DOWN)
    payload = ge.payload()
    assert len(process_nodes(payload)) == 21


def test_no_remainder_when_flow_fully_shown():
    ge = GraphExplorer(1, _inv_center_only())
    ge.expand_side(1, "downstream")
    assert remainder_nodes(ge.payload()) == []


def test_expand_all_refused_when_stub_above_cap():
    ge = GraphExplorer(1, _inv_twenty_five_down())
    ge.expand_flow(1, DOWN, all_remaining=True)
    assert len(process_nodes(ge.payload())) == 1


def test_expand_ten_more_then_expand_all():
    ge = GraphExplorer(1, _inv_twenty_five_down())
    ge.expand_flow(1, DOWN)
    ge.expand_flow(1, DOWN)
    payload = ge.payload()
    assert len(process_nodes(payload)) == 21
    assert stub_edges(payload) == []
    assert remainder_nodes(payload)[0]["hidden_count"] == 5
    ge.expand_flow(1, DOWN, all_remaining=True)
    assert len(process_nodes(ge.payload())) == 26
    assert stub_edges(ge.payload()) == []
    assert remainder_nodes(ge.payload()) == []


def test_largest_abs_amount_first():
    ge = GraphExplorer(1, _inv_twenty_five_down())
    ge.expand_side(1, "downstream")
    ids = {int(n["process_id"]) for n in process_nodes(ge.payload()) if not n["is_center"]}
    assert ids == set(range(10, 20))


def test_pair_flow_drawn_when_both_visible():
    ge = GraphExplorer(1, _inv_center_only())
    payload = ge.payload()
    flows = [e for e in payload["edges"] if e["kind"] == "flow"]
    assert any(e["source_id"] == "p:2" and e["target_id"] == "p:1" for e in flows)


def _inv_inner_exchange():
    heat = FlowKey("downstream", "heat", "megajoule")
    labels = {1: ("root", "GLO"), 2: ("supplier", "GLO"), 3: ("consumer", "GLO")}
    groups = {
        1: [
            (UP, [Counterpart(2, 0.5)]),
            (DOWN, [Counterpart(3, 1.0)]),
        ],
        2: [(heat, [Counterpart(3, 2.0)])],
    }
    return TestInventory(labels, groups)


def test_direct_only_hides_inner_exchanges():
    ge = GraphExplorer(1, _inv_inner_exchange())
    assert ge.direct_only is True
    flows = [e for e in ge.payload()["edges"] if e["kind"] == "flow"]
    assert any(e["source_id"] == "p:2" and e["target_id"] == "p:1" for e in flows)
    assert any(e["source_id"] == "p:1" and e["target_id"] == "p:3" for e in flows)
    assert not any(e["source_id"] == "p:2" and e["target_id"] == "p:3" for e in flows)


def test_all_inner_exchanges_when_direct_only_off():
    ge = GraphExplorer(1, _inv_inner_exchange())
    ge.direct_only = False
    flows = [e for e in ge.payload()["edges"] if e["kind"] == "flow"]
    assert any(e["source_id"] == "p:2" and e["target_id"] == "p:3" for e in flows)


def test_expand_downstream_side_uses_cap():
    ge = GraphExplorer(1, _inv_twenty_five_down())
    assert len(process_nodes(ge.payload())) == 1
    ge.expand_side(1, "downstream")
    assert len(process_nodes(ge.payload())) == 11
    assert stub_edges(ge.payload()) == []
    ge.expand_side(1, "downstream")
    assert len(process_nodes(ge.payload())) == 21
    assert stub_edges(ge.payload()) == []


def test_collapse_downstream_hides_exclusive_processes():
    ge = GraphExplorer(1, _inv_twenty_five_down())
    ge.collapse_side(1, "downstream")
    procs = process_nodes(ge.payload())
    assert len(procs) == 1
    assert procs[0]["is_center"]
    ge.expand_side(1, "downstream")
    ids = {int(n["process_id"]) for n in process_nodes(ge.payload()) if not n["is_center"]}
    assert ids == set(range(10, 20))


def test_collapse_does_not_remove_center():
    ge = GraphExplorer(1, _inv_center_only())
    ge.collapse_side(1, "upstream")
    assert any(n["is_center"] for n in process_nodes(ge.payload()))


def test_collapse_center_upstream_can_expand_again():
    ge = GraphExplorer(1, _inv_center_only())
    assert {n["process_id"] for n in process_nodes(ge.payload())} == {"1", "2"}
    center = next(n for n in process_nodes(ge.payload()) if n["is_center"])
    assert center["collapse_upstream"] is True
    assert center["expand_upstream"] is False
    ge.collapse_side(1, "upstream")
    ids = {n["process_id"] for n in process_nodes(ge.payload())}
    assert ids == {"1"}
    center = next(n for n in process_nodes(ge.payload()) if n["is_center"])
    assert center["expand_upstream"] is True
    assert center["collapse_upstream"] is False
    ge.expand_side(1, "upstream")
    ids = {n["process_id"] for n in process_nodes(ge.payload())}
    assert "2" in ids
    center = next(n for n in process_nodes(ge.payload()) if n["is_center"])
    assert center["collapse_upstream"] is True
    assert center["expand_upstream"] is False


def test_remove_process_and_exclusive():
    labels = {1: ("root", None), 2: ("mid", None), 3: ("leaf", None)}
    mid_up = FlowKey("upstream", "a", "kg")
    leaf_up = FlowKey("upstream", "b", "kg")
    groups = {
        1: [(mid_up, [Counterpart(2, 1)])],
        2: [(leaf_up, [Counterpart(3, 1)])],
        3: [],
    }
    ge = GraphExplorer(1, TestInventory(labels, groups))
    assert {n["process_id"] for n in process_nodes(ge.payload())} == {"1", "2"}
    ge.expand_flow(2, leaf_up)
    assert len(process_nodes(ge.payload())) == 3
    ge.remove_process(2)
    ids = {n["process_id"] for n in process_nodes(ge.payload())}
    assert ids == {"1"}


def test_cannot_remove_center():
    ge = GraphExplorer(1, _inv_center_only())
    ge.remove_process(1)
    assert process_nodes(ge.payload())[0]["process_id"] == "1"


def test_select_process():
    ge = GraphExplorer(1, _inv_center_only())
    ge.select(2)
    selected = [n for n in process_nodes(ge.payload()) if n["selected"]]
    assert len(selected) == 1
    assert selected[0]["process_id"] == "2"


def test_multifunctional_flag_when_two_functional_flows():
    a = FlowKey("downstream", "product a", "kilogram")
    b = FlowKey("downstream", "product b", "kilogram")
    labels = {1: ("chem plant", "GLO")}
    groups = {1: [(a, []), (b, [])]}
    ge = GraphExplorer(1, TestInventory(labels, groups))
    center = next(n for n in process_nodes(ge.payload()) if n["is_center"])
    assert center["multifunctional"] is True


def test_single_product_is_not_multifunctional():
    ge = GraphExplorer(1, _inv_center_only())
    center = next(n for n in process_nodes(ge.payload()) if n["is_center"])
    assert center["multifunctional"] is False


def test_card_prefers_metadata_lookup_for_labels():
    from activity_browser.bwutils.graph_explorer.inventory import BrightwayInventory

    inv = BrightwayInventory(
        metadata_lookup=lambda pid: {
            "name": "from-mds",
            "location": "CH",
            "database": "db",
            "product": "heat",
            "type": "process",
        }
        if pid == 7
        else None
    )

    def boom(_pid):
        raise AssertionError("labels should not load a Brightway node")

    inv._node = boom
    card = inv.card(7)
    assert card["name"] == "from-mds"
    assert card["location"] == "CH"
    assert card["product"] == "heat"
    assert card["multifunctional"] is False


def _inv_chp_substitution():
    elec = FlowKey("downstream", "electricity", "kilowatt hour")
    coproduct = FlowKey("downstream", "CHP heat", "megajoule")
    avoided = FlowKey("downstream", "Heat production", "kilogram")
    labels = {
        1: ("CHP - substitution", "GLO"),
        2: ("Heat production", "GLO"),
    }
    groups = {
        1: [
            (elec, []),
            (coproduct, []),
            (avoided, [Counterpart(2, 1.0, role="substitution")]),
        ],
        2: [
            (FlowKey("downstream", "Heat production", "kilogram"), [
                Counterpart(1, 1.0, from_exchange=False),
            ]),
        ],
    }
    return TestInventory(labels, groups)


def test_substitution_listed_on_substituting_process_is_downstream():
    ge = GraphExplorer(1, _inv_chp_substitution())
    ids = {n["process_id"] for n in process_nodes(ge.payload())}
    assert ids == {"1", "2"}
    flows = [e for e in ge.payload()["edges"] if e["kind"] == "flow"]
    sub = next(e for e in flows if e["role"] == "substitution")
    assert sub["source_id"] == "p:1"
    assert sub["target_id"] == "p:2"
    assert sub["amount"] == 1.0
    assert sub["unit"] == "kilogram"
    assert sub["product"] == "Heat production"
    assert sub.get("center_functional") is not True
    assert not sub.get("functional_at")
    stubs = stub_edges(ge.payload())
    assert any(s["unit"] == "megajoule" and s.get("amount") == 0 for s in stubs)


def test_substitution_pair_from_avoided_process_after_consumer_expand():
    ge = GraphExplorer(2, _inv_chp_substitution())
    assert {n["process_id"] for n in process_nodes(ge.payload())} == {"2"}
    ge.expand_side(2, "downstream")
    ids = {n["process_id"] for n in process_nodes(ge.payload())}
    assert ids == {"1", "2"}
    flows = [e for e in ge.payload()["edges"] if e["kind"] == "flow"]
    sub = next(e for e in flows if e["role"] == "substitution")
    assert sub["source_id"] == "p:1"
    assert sub["target_id"] == "p:2"
    assert not any(e.get("center_functional") for e in ge.payload()["edges"])
    assert not any(
        e["kind"] == "stub" and e.get("product") == "Heat production"
        for e in ge.payload()["edges"]
    )


def test_negative_substitution_points_at_the_listing_process():
    avoided = FlowKey("upstream", "waste treatment", "kilogram")
    labels = {1: ("avoider", "GLO"), 2: ("treatment", "GLO")}
    groups = {
        1: [(avoided, [Counterpart(2, -1.0, role="substitution")])],
    }
    ge = GraphExplorer(1, TestInventory(labels, groups))
    flows = [e for e in ge.payload()["edges"] if e["kind"] == "flow"]
    sub = next(e for e in flows if e["role"] == "substitution")
    assert sub["source_id"] == "p:2"
    assert sub["target_id"] == "p:1"
    assert sub["amount"] == 1.0
