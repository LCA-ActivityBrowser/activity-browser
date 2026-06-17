"""Reference-flow and method label formatting."""

import pandas as pd
import pytest
import bw2data as bd

from activity_browser.bwutils.commontasks import get_fu_label, get_method_label, reference_flow_parts
from activity_browser.bwutils.contribution_labels import (
    contribution_column_labels,
    contribution_row_labels,
)
from activity_browser.bwutils.multilca import _load_cs


def _bw_node(activity: dict):
    """Minimal Brightway-like node for ``refresh_node`` / ``is_node_biosphere``."""

    class _Doc:
        def __init__(self, node_type: str):
            self.type = node_type

    class _Node(dict):
        def __init__(self, data):
            super().__init__(data)
            self._document = _Doc(data.get("type", ""))

    return _Node(activity)


def _patch_get_node(monkeypatch, activities: dict):
    def refresh_node(node):
        if isinstance(node, tuple):
            if node not in activities:
                raise bd.errors.UnknownObject
            return _bw_node(activities[node])
        if hasattr(node, "_document"):
            return node
        raise ValueError("Activity must be either a tuple, int or Node instance")

    monkeypatch.setattr("activity_browser.bwutils.commontasks.refresh_node", refresh_node)
    monkeypatch.setattr("activity_browser.bwutils.contribution_labels.refresh_node", refresh_node)


@pytest.fixture
def product_activity(monkeypatch):
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

    monkeypatch.setattr("activity_browser.bwutils.commontasks.bd.get_activity", get_activity)
    return product


def test_get_fu_label_product_with_processor(product_activity):
    assert get_fu_label(product_activity) == "product 0 | main process 0 | GLO | LCIA_overview_test"


@pytest.fixture
def main_process_activity(monkeypatch, product_activity):
    product_key = ("LCIA_overview_test", "prod_0")

    def get_activity(key):
        if key == ("LCIA_overview_test", "main_0"):
            return {
                "name": "main process 0",
                "type": "process",
                "location": "GLO",
                "database": "LCIA_overview_test",
                "exchanges": [{"type": "production", "amount": 1, "input": product_key}],
            }
        if key == product_key:
            return product_activity
        raise KeyError(key)

    monkeypatch.setattr("activity_browser.bwutils.commontasks.bd.get_activity", get_activity)
    return get_activity(("LCIA_overview_test", "main_0"))


def test_get_fu_label_process_via_production_exchange(main_process_activity):
    assert get_fu_label(main_process_activity) == "product 0 | main process 0 | GLO | LCIA_overview_test"


def test_get_method_label():
    assert get_method_label(("IPCC", "GWP100")) == "IPCC, GWP100"
    assert get_method_label("x") == "x"


def test_load_cs_label_dicts(product_activity, monkeypatch):
    monkeypatch.setattr(
        "activity_browser.bwutils.multilca.bd.get_activity", lambda key: product_activity
    )
    key = ("LCIA_overview_test", "prod_0")
    obj = type("Obj", (), {})()
    _load_cs(obj, [{key: 1.0}, {key: 2.0}], [("m", "a")])
    assert obj.fu_labels[0] == obj.fu_labels[1]
    assert obj.fu_labels[0] == get_fu_label(product_activity)
    assert obj.method_labels[0] == "m, a"


def test_contribution_row_labels_biosphere(monkeypatch):
    flow = {
        "name": "Carbon dioxide, fossil",
        "categories": "air",
        "type": "emission",
        "database": "biosphere3",
        "code": "abc",
    }
    key = ("biosphere3", "abc")
    _patch_get_node(monkeypatch, {key: flow})
    df = pd.DataFrame(
        {
            "name": ["Carbon dioxide, fossil"],
            "categories": ["air"],
            "database": ["biosphere3"],
            "code": ["abc"],
            "0": [1.0],
        }
    )
    assert contribution_row_labels(df) == ["Carbon dioxide, fossil | air (biosphere3)"]


def test_contribution_row_labels_process_with_categories_column(product_activity, monkeypatch):
    """Technosphere rows must not use biosphere labelling when categories column exists."""
    key = ("LCIA_overview_test", "prod_0")
    monkeypatch.setattr(
        "activity_browser.bwutils.multilca.bd.get_activity", lambda key: product_activity
    )
    monkeypatch.setattr(
        "activity_browser.bwutils.commontasks.bd.get_activity", lambda _: product_activity
    )
    _patch_get_node(monkeypatch, {key: product_activity})
    df = pd.DataFrame(
        {
            "index": ["short process only"],
            "name": ["main process 0"],
            "product": ["product 0"],
            "location": ["GLO"],
            "database": ["LCIA_overview_test"],
            "code": ["prod_0"],
            "categories": [None],
            "0": [1.0],
        }
    )
    label = contribution_row_labels(df)[0]
    assert label == get_fu_label(product_activity)
    assert label != "short process only"
    assert " | " in label


def test_contribution_row_labels_elementary_flow_custom_database(monkeypatch):
    """Elementary flows are identified by node type, not database name."""
    flow = {
        "name": "custom emission",
        "categories": "air",
        "type": "emission",
        "database": "my_elementary_flows",
        "code": "co2",
    }
    key = ("my_elementary_flows", "co2")

    def get_activity(act_key):
        assert act_key == key
        return flow

    monkeypatch.setattr("activity_browser.bwutils.commontasks.bd.get_activity", get_activity)
    _patch_get_node(monkeypatch, {key: flow})
    df = pd.DataFrame(
        {
            "name": ["custom emission"],
            "categories": ["air"],
            "type": ["emission"],
            "database": ["my_elementary_flows"],
            "code": ["co2"],
            "0": [1.0],
        }
    )
    assert contribution_row_labels(df) == ["custom emission | air (my_elementary_flows)"]


def test_contribution_column_labels(product_activity, monkeypatch):
    monkeypatch.setattr(
        "activity_browser.bwutils.multilca.bd.get_activity", lambda key: product_activity
    )
    key = ("LCIA_overview_test", "prod_0")
    mlca = type("MLCA", (), {})()
    _load_cs(mlca, [{key: 1.0}], [("m", "a")])

    class Switches:
        indexes = type("I", (), {"func": 0, "method": 1})()
        mode = 0

        def currentIndex(self):
            return self.mode

    switches = Switches()
    tab = type("Tab", (), {"switches": switches, "parent": type("P", (), {"mlca": mlca})()})()
    assert contribution_column_labels(tab, [0]) == [mlca.fu_labels[0]]
    switches.mode = switches.indexes.method
    assert contribution_column_labels(tab, [0]) == [mlca.method_labels[0]]


def test_setup_column_labels_from_mlca_dicts(product_activity, monkeypatch):
    monkeypatch.setattr(
        "activity_browser.bwutils.multilca.bd.get_activity", lambda key: product_activity
    )
    key = ("LCIA_overview_test", "prod_0")
    mlca = type("MLCA", (), {})()
    _load_cs(mlca, [{key: 1.0}], [("m", "a"), ("long", "name")])

    class Switches:
        indexes = type("I", (), {"func": 0, "method": 1, "scenario": 2})()
        mode = 1

        def currentIndex(self):
            return self.mode

    tab = type("Tab", (), {"switches": Switches(), "parent": type("P", (), {"mlca": mlca})()})()
    assert contribution_column_labels(tab, [0, 1]) == ["m, a", "long, name"]


def test_join_df_with_metadata_reference_flow_columns(product_activity, monkeypatch):
    from activity_browser.bwutils.multilca import Contributions

    key = ("LCIA_overview_test", "prod_0")

    def get_activity(k):
        if k == ("LCIA_overview_test", "main_0"):
            return {
                "name": "main process 0",
                "type": "process",
                "location": "GLO",
                "database": "LCIA_overview_test",
            }
        return product_activity

    monkeypatch.setattr("activity_browser.bwutils.commontasks.bd.get_activity", get_activity)
    monkeypatch.setattr("activity_browser.bwutils.multilca.bd.get_activity", get_activity)

    meta_df = pd.DataFrame(
        {
            "name": [None],
            "product": [None],
            "location": ["GLO"],
            "database": ["LCIA_overview_test"],
        },
        index=pd.MultiIndex.from_tuples([key], names=["database", "code"]),
    )

    class _FakeMetadata:
        @property
        def keys(self):
            return {key}

        def get_metadata(self, keys, columns=None):
            frame = meta_df.loc[keys]
            if columns is not None:
                return frame[list(columns)]
            return frame

    monkeypatch.setattr("activity_browser.bwutils.multilca.metadata", _FakeMetadata())

    mlca = type("MLCA", (), {"fu_labels": {}, "method_labels": {}, "methods": []})()
    df = pd.DataFrame({"impact": [1.0]}, index=[key])
    joined = Contributions.join_df_with_metadata(df, x_fields=None, mlca=mlca)

    label = "product 0 | main process 0 | GLO | LCIA_overview_test"
    assert joined.loc[label, "product"] == "product 0"
    assert joined.loc[label, "name"] == "main process 0"


def test_join_df_with_metadata_ef_fields(monkeypatch):
    from activity_browser.bwutils.multilca import Contributions

    key = ("biosphere3", "co2")
    fields = ["name", "categories", "database"]
    meta_df = pd.DataFrame(
        {
            "name": ["Carbon dioxide, fossil"],
            "categories": ["air"],
            "database": ["biosphere3"],
        },
        index=pd.MultiIndex.from_tuples([key], names=["database", "code"]),
    )

    class _FakeMetadata:
        @property
        def keys(self):
            return {key}

        def get_metadata(self, keys, columns=None):
            frame = meta_df.loc[keys]
            if columns is not None:
                return frame[list(columns)]
            return frame

    monkeypatch.setattr("activity_browser.bwutils.multilca.metadata", _FakeMetadata())

    mlca = type("MLCA", (), {"fu_labels": {}, "method_labels": {}, "methods": []})()
    df = pd.DataFrame({"0": [1.0]}, index=[key])
    joined = Contributions.join_df_with_metadata(df, x_fields=fields, mlca=mlca)
    assert joined.index[0] == "Carbon dioxide, fossil | air | biosphere3"
    joined.reset_index(drop=False)  # must not raise "database already exists"


def test_multi_part_method_columns_stay_flat_for_metadata_join():
    """Contribution compare columns use setup indices, not method tuples."""
    df = pd.DataFrame(
        {0: [10.0, 5.0], 1: [8.0, 3.0]},
        index=[("Score", ""), ("biosphere3", "CO2")],
    )
    assert not isinstance(df.columns, pd.MultiIndex)

    df.index = pd.MultiIndex.from_tuples(
        [("Score", ""), ("biosphere3", "CO2")], names=["database", "code"]
    )
    meta = pd.DataFrame(
        {"name": ["Score", "Carbon dioxide"]},
        index=df.index,
    )

    joined = meta.join(df, how="outer")
    assert not isinstance(joined.columns, pd.MultiIndex)
    assert joined[0].loc[("Score", "")] == 10.0


def test_top_ef_contributions_compare_impact_categories(lcia_overview_project):
    """Switching Contributions to compare-by-IC must build the EF table."""
    from activity_browser.bwutils.multilca import Contributions, MLCA

    mlca = MLCA("lcia_3x3")
    mlca.calculate()
    contributions = Contributions(mlca)
    df = contributions.top_elementary_flow_contributions(functional_unit="0", limit=5)
    assert len(df) > 0
    assert len(mlca.methods) == len(df.select_dtypes(include="number").columns)
