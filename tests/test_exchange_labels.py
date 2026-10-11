"""Tests for shared exchange label helpers."""

from activity_browser.bwutils.commontasks import (
    exchange_consumer_parts,
    exchange_part_label,
    exchange_label,
    exchange_product_name,
)


def test_exchange_labels(basic_project_readonly):
    """Product, consumer parts, full/short labels, and endpoint label."""
    process = basic_project_readonly.get("process")
    elementary = basic_project_readonly.get("elementary")
    db_name = basic_project_readonly.name

    product = exchange_product_name(elementary.key)
    assert product == elementary["name"]

    proc, location, database = exchange_consumer_parts(process.key)
    assert proc == process["name"]
    assert database == db_name

    full = exchange_label(elementary.key, process.key, include_database=True)
    assert "-->" in full
    assert process["name"] in full
    assert elementary["name"] in full
    assert db_name in full

    short = exchange_label(elementary.key, process.key, include_database=False)
    assert db_name not in short

    endpoint = exchange_part_label(process.key, include_database=True)
    assert process["name"] in endpoint
    assert db_name in endpoint


def test_setup_fu_labels_exclude_amount(basic_project_readonly):
    """FU labels ignore amount; shares module-scoped read-only project."""
    from activity_browser.bwutils.multilca import _load_cs

    key = ("basic", "product_1")
    obj = type("Obj", (), {})()
    _load_cs(obj, [{key: 1.0}, {key: 2.0}], [])
    assert len(obj.fu_labels) == 2
    assert obj.fu_labels[0] == obj.fu_labels[1]
    assert "1.0" not in obj.fu_labels[0]
