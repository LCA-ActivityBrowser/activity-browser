"""Reference-flow label formatting (product nodes with processor activities)."""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from activity_browser.app.pages.lca_results.plots import (
    contribution_column_labels,
    contribution_row_labels,
)
from activity_browser.bwutils.commontasks import (
    format_reference_flow_label,
    reference_flow_parts,
)


@pytest.fixture
def product_activity(monkeypatch):
    """Product node like ``LCIA_overview_test`` (processor = main process)."""
    processor = {
        "name": "main process 0",
        "type": "process",
        "location": "GLO",
        "database": "LCIA_overview_test",
    }
    product = {
        "name": "product 0",
        "reference product": "product 0",
        "type": "product",
        "location": "GLO",
        "database": "LCIA_overview_test",
        "processor": ("LCIA_overview_test", "main_0"),
    }

    def get_activity(key):
        if key == ("LCIA_overview_test", "main_0"):
            return processor
        raise KeyError(key)

    monkeypatch.setattr(
        "activity_browser.bwutils.commontasks.bd.get_activity", get_activity
    )
    return product


def test_reference_flow_parts_product_with_processor(product_activity):
    product, process_name, location, database = reference_flow_parts(product_activity)
    assert product == "product 0"
    assert process_name == "main process 0"
    assert location == "GLO"
    assert database == "LCIA_overview_test"


def test_format_reference_flow_label_product_with_processor(product_activity):
    label = format_reference_flow_label(product_activity)
    assert label == "product 0 | main process 0 | GLO | LCIA_overview_test"
    assert "None" not in label


@pytest.fixture
def main_process_activity(monkeypatch, product_activity):
    """Process node linked to a product via its production exchange."""
    product_key = ("LCIA_overview_test", "prod_0")

    def get_activity(key):
        if key == ("LCIA_overview_test", "main_0"):
            return {
                "name": "main process 0",
                "type": "process",
                "location": "GLO",
                "database": "LCIA_overview_test",
                "exchanges": [
                    {"type": "production", "amount": 1, "input": product_key},
                ],
            }
        if key == product_key:
            return product_activity
        raise KeyError(key)

    monkeypatch.setattr(
        "activity_browser.bwutils.commontasks.bd.get_activity", get_activity
    )
    return get_activity(("LCIA_overview_test", "main_0"))


def test_reference_flow_parts_process_via_production_exchange(main_process_activity):
    product, process_name, location, database = reference_flow_parts(
        main_process_activity
    )
    assert product == "product 0"
    assert process_name == "main process 0"
    assert location == "GLO"
    assert database == "LCIA_overview_test"


def test_format_reference_flow_label_process_via_production_exchange(
    main_process_activity,
):
    label = format_reference_flow_label(main_process_activity)
    assert label == "product 0 | main process 0 | GLO | LCIA_overview_test"
    assert "None" not in label


def test_contribution_row_labels_from_metadata_keys(
    product_activity, main_process_activity, monkeypatch
):
    def get_activity(key):
        if key == ("LCIA_overview_test", "main_0"):
            return main_process_activity
        if key == ("LCIA_overview_test", "prod_0"):
            return product_activity
        raise KeyError(key)

    monkeypatch.setattr(
        "activity_browser.app.pages.lca_results.plots.bd.get_activity", get_activity
    )
    monkeypatch.setattr(
        "activity_browser.bwutils.commontasks.bd.get_activity", get_activity
    )
    df = pd.DataFrame(
        {
            "index": ["None | product 0 | GLO"],
            "database": ["LCIA_overview_test"],
            "code": ["main_0"],
            "prod_0": [1.0],
        }
    )
    labels = contribution_row_labels(df)
    assert labels == ["product 0 | main process 0 | GLO | LCIA_overview_test"]


def test_contribution_column_labels_reference_flows(
    product_activity, monkeypatch
):
    processor = {
        "name": "main process 0",
        "type": "process",
        "location": "GLO",
        "database": "LCIA_overview_test",
    }

    def get_activity(key):
        if key == ("LCIA_overview_test", "prod_0"):
            return product_activity
        if key == ("LCIA_overview_test", "main_0"):
            return processor
        raise KeyError(key)

    monkeypatch.setattr(
        "activity_browser.app.pages.lca_results.plots.bd.get_activity", get_activity
    )
    monkeypatch.setattr(
        "activity_browser.bwutils.commontasks.bd.get_activity", get_activity
    )

    class Switches:
        indexes = type("I", (), {"func": 0, "method": 1})()

        def currentIndex(self):
            return self.indexes.func

    class Parent:
        mlca = type(
            "MLCA",
            (),
            {"fu_activity_keys": [("LCIA_overview_test", "prod_0")]},
        )()

    tab = type("Tab", (), {"switches": Switches(), "parent": Parent()})()
    labels = contribution_column_labels(tab, ["stale column label"])
    assert labels == ["product 0 | main process 0 | GLO | LCIA_overview_test"]
