"""Tests for shared exchange label helpers."""

from activity_browser.bwutils.commontasks import (
    exchange_consumer_parts,
    exchange_part_label,
    exchange_label,
    exchange_product_name,
)


def test_exchange_label_technosphere(basic_database):
    process = basic_database.get("process")
    elementary = basic_database.get("elementary")

    product = exchange_product_name(elementary.key)
    assert product == elementary["name"]

    proc, location, database = exchange_consumer_parts(process.key)
    assert proc == process["name"]
    assert database == basic_database.name

    full = exchange_label(elementary.key, process.key, include_database=True)
    assert "-->" in full
    assert process["name"] in full
    assert elementary["name"] in full
    assert basic_database.name in full

    short = exchange_label(elementary.key, process.key, include_database=False)
    assert basic_database.name not in short


def test_exchange_endpoint_label(basic_database):
    process = basic_database.get("process")
    label = exchange_part_label(process.key, include_database=True)
    assert process["name"] in label
    assert basic_database.name in label
