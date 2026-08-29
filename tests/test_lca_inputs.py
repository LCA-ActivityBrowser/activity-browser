"""Tree/Sankey LCA demand mapping and scenario selection."""

from __future__ import annotations

import warnings

import bw2data as bd
import pytest
from bw2data.tests import bw2test

from activity_browser.bwutils.lca_inputs import lca_for_tree_selection
from activity_browser.bwutils.superstructure.manager import SuperstructureManager
from activity_browser.bwutils.superstructure.mlca import SuperstructureMLCA
from fixtures.bw_helpers import (
    write_calculation_setup,
    write_functional_database,
    write_method,
)
from fixtures.lcia_overview import (
    CALCULATION_SETUPS,
    DATABASE,
    DATABASE_NAME,
    METHODS,
    build_scenario_dataframe,
)


def _tree_demand(func_unit: dict) -> dict:
    """Match ContributionTreeTab._selection_inputs: datapackage ids."""
    return {bd.get_activity(k).id: v for k, v in func_unit.items()}


@pytest.fixture(scope="module")
@bw2test
def tree_scenario_mlca():
    """One project + one SuperstructureMLCA.calculate for the whole module.

    Previously each test rebuilt ``lcia_overview_project`` and recalculated MLCA
    (~7s each × 4 on Ubuntu CI).
    """
    write_functional_database(DATABASE_NAME, DATABASE, process=True)
    # lcia_1x1 only needs method_0; keep writes minimal.
    write_method("lcia_method_0", METHODS["lcia_method_0"], process=True)
    write_calculation_setup("lcia_1x1", CALCULATION_SETUPS["lcia_1x1"])

    df = SuperstructureManager(build_scenario_dataframe()).combined_data()
    mlca = SuperstructureMLCA("lcia_1x1", df)
    mlca.calculate()
    yield mlca


def test_tree_lca_scenarios_match_mlca_scores(tree_scenario_mlca):
    mlca = tree_scenario_mlca
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


def test_tree_lca_without_scenarios_ignores_scenario_idx(tree_scenario_mlca):
    """Regression: Tree used to always rebuild a non-scenario LCA after sankey update."""
    mlca = tree_scenario_mlca
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


def test_tree_lca_switching_scenarios_updates_score(tree_scenario_mlca):
    mlca = tree_scenario_mlca
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


def test_tree_lca_scenario_switch_does_not_warn_pardiso_noop(tree_scenario_mlca):
    """``decompose_technosphere`` is a PARDISO no-op; do not call it on switch."""
    mlca = tree_scenario_mlca
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
