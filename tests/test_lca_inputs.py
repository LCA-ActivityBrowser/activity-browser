"""Tree/Sankey LCA demand mapping and scenario selection."""

from __future__ import annotations

import warnings

import bw2data as bd
import pytest

from activity_browser.bwutils.lca_inputs import lca_for_tree_selection
from activity_browser.bwutils.superstructure.manager import SuperstructureManager
from activity_browser.bwutils.superstructure.mlca import SuperstructureMLCA
from fixtures.lcia_overview import build_scenario_dataframe


def _tree_demand(func_unit: dict) -> dict:
    """Match ContributionTreeTab._selection_inputs: datapackage ids."""
    return {bd.get_activity(k).id: v for k, v in func_unit.items()}


def _scenario_mlca() -> SuperstructureMLCA:
    df = SuperstructureManager(build_scenario_dataframe()).combined_data()
    mlca = SuperstructureMLCA("lcia_1x1", df)
    mlca.calculate()
    return mlca


def test_tree_lca_scenarios_match_mlca_scores(lcia_overview_project):
    mlca = _scenario_mlca()
    demand = _tree_demand(mlca.func_units[0])
    method = mlca.methods[0]
    names = list(mlca.scenario_names)

    for scenario_name in ("baseline", "high_demand", "low_demand"):
        idx = names.index(scenario_name)
        lca, _ = lca_for_tree_selection(
            has_scenarios=True,
            mlca=mlca,
            demand=demand,
            method=method,
            scenario_idx=idx,
            method_idx=0,
        )
        assert lca is mlca.lca
        assert lca.score == pytest.approx(mlca.lca_scores[0, 0, idx])


def test_tree_lca_without_scenarios_ignores_scenario_idx(lcia_overview_project):
    """Regression: Tree used to always rebuild a non-scenario LCA after sankey update."""
    mlca = _scenario_mlca()
    demand = _tree_demand(mlca.func_units[0])
    method = mlca.methods[0]
    names = list(mlca.scenario_names)
    high_idx = names.index("high_demand")
    baseline_idx = names.index("baseline")

    lca, _ = lca_for_tree_selection(
        has_scenarios=False,
        mlca=mlca,
        demand=demand,
        method=method,
        scenario_idx=high_idx,
        method_idx=0,
    )
    assert lca is not mlca.lca
    assert lca.score == pytest.approx(mlca.lca_scores[0, 0, baseline_idx])
    assert lca.score != pytest.approx(mlca.lca_scores[0, 0, high_idx])


def test_tree_lca_switching_scenarios_updates_score(lcia_overview_project):
    mlca = _scenario_mlca()
    demand = _tree_demand(mlca.func_units[0])
    method = mlca.methods[0]
    names = list(mlca.scenario_names)
    high_idx = names.index("high_demand")
    low_idx = names.index("low_demand")

    high, _ = lca_for_tree_selection(
        has_scenarios=True,
        mlca=mlca,
        demand=demand,
        method=method,
        scenario_idx=high_idx,
        method_idx=0,
    )
    high_score = high.score
    low, _ = lca_for_tree_selection(
        has_scenarios=True,
        mlca=mlca,
        demand=demand,
        method=method,
        scenario_idx=low_idx,
        method_idx=0,
    )
    assert low is high
    assert low.score == pytest.approx(mlca.lca_scores[0, 0, low_idx])
    assert low.score != pytest.approx(high_score)


def test_tree_lca_scenario_switch_does_not_warn_pardiso_noop(lcia_overview_project):
    """``decompose_technosphere`` is a PARDISO no-op; do not call it on switch."""
    mlca = _scenario_mlca()
    demand = _tree_demand(mlca.func_units[0])
    method = mlca.methods[0]
    idx = list(mlca.scenario_names).index("high_demand")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        lca_for_tree_selection(
            has_scenarios=True,
            mlca=mlca,
            demand=demand,
            method=method,
            scenario_idx=idx,
            method_idx=0,
        )
    assert not any("PARDISO installed; this is a no-op" in str(w.message) for w in caught)
