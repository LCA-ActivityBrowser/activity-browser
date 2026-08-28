"""
Primary-seam tests: Monte Carlo + scenario amounts on ``MonteCarloLCA.calculate``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from activity_browser.bwutils.montecarlo import MonteCarloLCA
from activity_browser.bwutils.superstructure.manager import SuperstructureManager
from activity_browser.bwutils.superstructure.utils import SUPERSTRUCTURE
from fixtures.monte_carlo import (
    BASELINE_SCORE,
    DATABASE_NAME,
)

SEED = 42
ITERATIONS = 20


def _scenario_row(**fields) -> pd.DataFrame:
    row = {c: np.nan for c in SUPERSTRUCTURE}
    row.update(fields)
    return SuperstructureManager(pd.DataFrame([row])).combined_data(skip_checks=True)


def _scenario_df_biosphere_on_main(amounts: dict[str, float]) -> pd.DataFrame:
    if all(isinstance(v, float) and np.isnan(v) for v in amounts.values()):
        idx = pd.MultiIndex.from_tuples(
            [((DATABASE_NAME, "elementary"), (DATABASE_NAME, "main"), "biosphere")],
            names=["input", "output", "flow"],
        )
        return pd.DataFrame(amounts, index=idx)

    return _scenario_row(
        **{
            "from database": DATABASE_NAME,
            "from key": (DATABASE_NAME, "elementary"),
            "to database": DATABASE_NAME,
            "to key": (DATABASE_NAME, "main"),
            "flow type": "biosphere",
            **amounts,
        }
    )


def _scenario_df_technosphere_on_main(amounts: dict[str, float]) -> pd.DataFrame:
    return _scenario_row(
        **{
            "from database": DATABASE_NAME,
            "from key": (DATABASE_NAME, "supplier_product"),
            "to database": DATABASE_NAME,
            "to key": (DATABASE_NAME, "main"),
            "flow type": "technosphere",
            **amounts,
        }
    )


def _run(cs_name: str, scenario_df=None, scenario=None, **includes) -> MonteCarloLCA:
    mc = MonteCarloLCA(cs_name)
    mc.calculate(
        iterations=ITERATIONS,
        seed=SEED,
        scenario_df=scenario_df,
        scenario=scenario,
        **includes,
    )
    return mc


def _scores(mc: MonteCarloLCA) -> np.ndarray:
    return mc.results[:, 0, 0]


def test_mc_scenario_amounts_apply_when_uncertainty_off(mc_project):
    """Deterministic MC follows the selected scenario amount (main bio 10 → 20)."""
    sdf = _scenario_df_biosphere_on_main({"S1": 10.0, "S2": 20.0})
    s1 = _scores(
        _run(
            mc_project,
            scenario_df=sdf,
            scenario="S1",
            technosphere=False,
            biosphere=False,
            cf=False,
            parameters=False,
        )
    )
    s2 = _scores(
        _run(
            mc_project,
            scenario_df=sdf,
            scenario="S2",
            technosphere=False,
            biosphere=False,
            cf=False,
            parameters=False,
        )
    )
    np.testing.assert_allclose(s1, BASELINE_SCORE)
    np.testing.assert_allclose(s2, 21.0)


def test_mc_scenario_by_index(mc_project):
    sdf = _scenario_df_biosphere_on_main({"S1": 10.0, "S2": 20.0})
    scores = _scores(
        _run(
            mc_project,
            scenario_df=sdf,
            scenario=1,
            technosphere=False,
            biosphere=False,
            cf=False,
            parameters=False,
        )
    )
    np.testing.assert_allclose(scores, 21.0)


def test_mc_scenario_technosphere_amount_applies(mc_project):
    sdf = _scenario_df_technosphere_on_main({"S1": 2.0})
    scores = _scores(
        _run(
            mc_project,
            scenario_df=sdf,
            scenario="S1",
            technosphere=False,
            biosphere=False,
            cf=False,
            parameters=False,
        )
    )
    np.testing.assert_allclose(scores, 12.0)


def test_mc_scenario_nan_keeps_database_amount(mc_project):
    sdf = _scenario_df_biosphere_on_main({"S1": float("nan")})
    scores = _scores(
        _run(
            mc_project,
            scenario_df=sdf,
            scenario="S1",
            technosphere=False,
            biosphere=False,
            cf=False,
            parameters=False,
        )
    )
    np.testing.assert_allclose(scores, BASELINE_SCORE)


def test_mc_scenario_uncertain_flow_keeps_database_uncertainty(mc_project):
    sdf = _scenario_row(
        **{
            "from database": DATABASE_NAME,
            "from key": (DATABASE_NAME, "elementary"),
            "to database": DATABASE_NAME,
            "to key": (DATABASE_NAME, "supplier"),
            "flow type": "biosphere",
            "S2": 100.0,
        }
    )
    fixed = _scores(
        _run(
            mc_project,
            scenario_df=sdf,
            scenario="S2",
            technosphere=False,
            biosphere=False,
            cf=False,
            parameters=False,
        )
    )
    stochastic = _scores(
        _run(
            mc_project,
            scenario_df=sdf,
            scenario="S2",
            technosphere=False,
            biosphere=True,
            cf=False,
            parameters=False,
        )
    )
    np.testing.assert_allclose(fixed, 110.0)
    assert stochastic.max() < 20.0
    assert np.std(stochastic) > 0


def test_mc_parameters_win_over_scenario_amount(mc_project_with_parameters):
    sdf = _scenario_df_biosphere_on_main({"S2": 100.0})
    scores = _scores(
        _run(
            mc_project_with_parameters,
            scenario_df=sdf,
            scenario="S2",
            technosphere=False,
            biosphere=False,
            cf=False,
            parameters=True,
        )
    )
    assert scores.min() >= 8.5
    assert scores.max() <= 13.5


def test_mc_last_run_summary(mc_project):
    sdf = _scenario_df_biosphere_on_main({"S2": 20.0})
    mc = _run(
        mc_project,
        scenario_df=sdf,
        scenario="S2",
        technosphere=True,
        biosphere=False,
        cf=False,
        parameters=False,
    )
    assert mc.last_run_summary == {
        "scenario": "S2",
        "iterations": ITERATIONS,
        "seed": SEED,
        "includes": {
            "technosphere": True,
            "biosphere": False,
            "cf": False,
            "parameters": False,
        },
    }
