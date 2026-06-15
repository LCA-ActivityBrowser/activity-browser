"""Tests for LCIA overview normalization and data builder."""

from __future__ import annotations

import numpy as np
import pytest

from activity_browser.ui.widgets.plot import ABPlot
from activity_browser.bwutils.lcia_overview import (
    LCIACompareMode,
    available_compare_modes,
    build_lcia_overview,
    compare_mode_supports_flip,
    normalize_column,
    normalize_lcia_matrix,
)


def test_normalize_column_uses_max_abs_impact():
    col = np.array([-3.0, 5.0, 10.0])
    out = normalize_column(col, relative=True)
    np.testing.assert_allclose(out, [-30.0, 50.0, 100.0])


def test_normalize_column_mixed_sign_largest_negative_sets_scale():
    col = np.array([-11.0, 5.0, 10.0])
    out = normalize_column(col, relative=True)
    np.testing.assert_allclose(out, [-100.0, 5 / 11 * 100, 10 / 11 * 100])


def test_normalize_column_absolute_unchanged():
    col = np.array([1.5, -2.0])
    out = normalize_column(col, relative=False)
    np.testing.assert_allclose(out, col)


def test_lca_scores_normalized_zero_column():
    from types import SimpleNamespace

    from activity_browser.bwutils.multilca import MLCA

    scores = SimpleNamespace(lca_scores=np.array([[0.0, 10.0], [0.0, 5.0]]))
    normalized = MLCA.lca_scores_normalized.fget(scores)
    np.testing.assert_allclose(normalized[:, 0], [0.0, 0.0])
    np.testing.assert_allclose(normalized[:, 1], [1.0, 0.5])


def test_normalize_lcia_matrix_per_column():
    scores = np.array([[10.0, -4.0], [5.0, -8.0]])
    out = normalize_lcia_matrix(scores, relative=True)
    np.testing.assert_allclose(out[:, 0], [100.0, 50.0])
    np.testing.assert_allclose(out[:, 1], [-50.0, -100.0])


class _FakeMLCA:
    def __init__(self, scores, func_units, methods, scenario_names=None):
        self.lca_scores = scores
        self.func_units = func_units
        self.methods = methods
        self.scenario_names = scenario_names or []
        fu_label_list = [
            f"product {i} | process {i} | GLO | db"
            for i in range(len(func_units))
        ]
        method_label_list = [
            ", ".join(str(p) for p in m if p) for m in methods
        ]
        self.fu_labels = {i: label for i, label in enumerate(fu_label_list)}
        self.method_labels = {i: label for i, label in enumerate(method_label_list)}
        self.setup = type(
            "Setup",
            (),
            {
                "fu_labels": fu_label_list,
                "method_labels": method_label_list,
            },
        )()


class _FakeContributions:
    pass


@pytest.fixture
def stub_method_units(monkeypatch):
    monkeypatch.setattr(
        "activity_browser.bwutils.lcia_overview.unit_of_method",
        lambda method: "kg",
    )


def test_build_flows_x_methods_default_orientation(stub_method_units):
    scores = np.array([[10.0, 20.0], [5.0, 15.0]])
    mlca = _FakeMLCA(
        scores,
        func_units=[{("db", "a"): 1}, {("db", "b"): 1}],
        methods=[("m0",), ("m1",)],
    )
    data = build_lcia_overview(
        mlca,
        _FakeContributions(),
        compare=LCIACompareMode.FLOWS_X_METHODS,
        relative=True,
        flip_groups=False,
    )
    assert data.values.shape == (2, 2)
    assert data.group_labels == ["m0", "m1"]
    assert data.series_labels[0].startswith("product ")


def test_build_flows_x_methods_flip_is_transpose_of_column_normalization(stub_method_units):
    scores = np.array([[10.0, 20.0], [5.0, 15.0]])
    mlca = _FakeMLCA(
        scores,
        func_units=[{("db", "a"): 1}, {("db", "b"): 1}],
        methods=[("m0",), ("m1",)],
    )
    normal = build_lcia_overview(
        mlca,
        _FakeContributions(),
        compare=LCIACompareMode.FLOWS_X_METHODS,
        relative=True,
        flip_groups=False,
    )
    flipped = build_lcia_overview(
        mlca,
        _FakeContributions(),
        compare=LCIACompareMode.FLOWS_X_METHODS,
        relative=True,
        flip_groups=True,
    )
    np.testing.assert_allclose(flipped.values, normal.values.T)
    np.testing.assert_allclose(flipped.absolute_values, normal.absolute_values.T)
    assert flipped.group_labels[0].startswith("product ")
    assert flipped.series_labels == ["m0", "m1"]


@pytest.mark.parametrize(
    "n,expected",
    [
        (0, (0, 0)),
        (1, (1, 1)),
        (2, (1, 2)),
        (3, (2, 2)),
        (4, (2, 2)),
        (5, (2, 3)),
        (6, (2, 3)),
        (8, (3, 3)),
        (9, (3, 3)),
        (10, (3, 4)),
    ],
)
def test_near_square_subplot_grid(n, expected):
    assert ABPlot.near_square_subplot_grid(n) == expected


def test_build_flows_x_scenarios_x_methods_panels(stub_method_units):
    scores = np.array(
        [
            [[1.0, 2.0], [3.0, 4.0]],
            [[5.0, 6.0], [7.0, 8.0]],
        ]
    )
    mlca = _FakeMLCA(
        scores,
        func_units=[{("db", "a"): 1}, {("db", "b"): 1}],
        methods=[("m0",), ("m1",)],
        scenario_names=["s1", "s2"],
    )
    data = build_lcia_overview(
        mlca,
        _FakeContributions(),
        compare=LCIACompareMode.FLOWS_X_SCENARIOS_X_METHODS,
        relative=False,
    )
    assert len(data.panels) == 2
    assert "impact category" in data.table_df.columns


def test_available_compare_modes_order():
    mlca = _FakeMLCA(
        np.zeros((2, 3, 2)),
        func_units=[{}, {}],
        methods=[("a",), ("b",), ("c",)],
        scenario_names=["s1", "s2"],
    )
    modes = available_compare_modes(mlca, has_scenarios=True)
    assert modes[0] == LCIACompareMode.REFERENCE_FLOWS
    assert LCIACompareMode.FLOWS_X_METHODS in modes
    assert LCIACompareMode.FLOWS_X_SCENARIOS in modes
    assert LCIACompareMode.FLOWS_X_SCENARIOS_X_METHODS in modes


def test_compare_mode_supports_flip():
    assert compare_mode_supports_flip(LCIACompareMode.FLOWS_X_METHODS)
    assert not compare_mode_supports_flip(LCIACompareMode.REFERENCE_FLOWS)


@pytest.mark.skip(reason="Fails on CI with non-editable install; covered by test_reference_flow_labels.py")
def test_reference_flow_label_uses_processor_name(lcia_overview_project):
    import bw2data as bd

    from activity_browser.bwutils.commontasks import get_fu_label
    from tests.fixtures.lcia_overview import DATABASE_NAME

    act = bd.get_activity((DATABASE_NAME, "prod_0"))
    label = get_fu_label(act, 1.0)
    assert label == f"product 0 | main process 0 | GLO | {DATABASE_NAME} | 1.0"


def test_lcia_1x1_calculation(lcia_overview_project):
    from activity_browser.bwutils.multilca import MLCA

    mlca = MLCA("lcia_1x1")
    mlca.calculate()
    assert mlca.lca_scores.shape == (1, 1)
    assert mlca.lca_scores[0, 0] > 0


def test_lcia_3x3_all_negative_column_normalization(lcia_overview_project):
    from activity_browser.bwutils.multilca import MLCA

    mlca = MLCA("lcia_3x3_neg")
    mlca.calculate()
    col = mlca.lca_scores[:, 1]
    assert np.all(col < 0)
    normalized = normalize_column(col, relative=True)
    assert np.isclose(normalized.min(), -100.0)


def test_lcia_overview_plot_smoke(lcia_overview_project):
    import matplotlib

    matplotlib.use("Agg")
    from qtpy import QtWidgets

    from activity_browser.app.pages.lca_results.plots import LCIAResultsOverviewPlot
    from activity_browser.bwutils.multilca import MLCA, ca

    if QtWidgets.QApplication.instance() is None:
        QtWidgets.QApplication([])

    mlca = MLCA("lcia_3x3")
    mlca.calculate()
    data = build_lcia_overview(
        mlca,
        ca,
        compare=LCIACompareMode.FLOWS_X_METHODS,
        relative=True,
    )
    plot = LCIAResultsOverviewPlot()
    plot.plot(data)
    assert len(plot.ax.patches) > 0


def test_lcia_compare_label_helpers_round_trip():
    from activity_browser.bwutils.lcia_overview import (
        LCIA_COMPARE_LABELS,
        lcia_compare_label,
        lcia_compare_mode_from_label,
    )

    for mode in LCIACompareMode:
        label = lcia_compare_label(mode)
        assert label == LCIA_COMPARE_LABELS[mode]
        assert lcia_compare_mode_from_label(label) == mode
