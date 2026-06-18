"""
Integration tests for ``MonteCarloLCA`` multi-layer wiring (single-layer spread is stats_arrays/bw2calc).
"""

from __future__ import annotations

import numpy as np

from activity_browser.bwutils.montecarlo import MonteCarloLCA

SEED = 42
ITERATIONS = 20


def _run_mc(cs_name: str, **includes) -> MonteCarloLCA:
    mc = MonteCarloLCA(cs_name)
    mc.calculate(iterations=ITERATIONS, seed=SEED, **includes)
    return mc


def _mc_scores(mc: MonteCarloLCA) -> np.ndarray:
    return mc.results[:, 0, 0]


def test_mc_parameter_uncertainty_produces_spread(mc_project_with_parameters):
    mc = _run_mc(
        mc_project_with_parameters,
        technosphere=False,
        biosphere=False,
        cf=False,
        parameters=True,
    )
    assert np.std(_mc_scores(mc)) > 0


def test_mc_all_sources_jointly_produce_spread(mc_project_with_parameters):
    mc = _run_mc(
        mc_project_with_parameters,
        technosphere=True,
        biosphere=True,
        cf=True,
        parameters=True,
    )
    assert np.std(_mc_scores(mc)) > 0


def test_mc_reproducible_with_same_seed(mc_project):
    kwargs = dict(
        technosphere=True,
        biosphere=True,
        cf=True,
        parameters=False,
    )
    first = _mc_scores(_run_mc(mc_project, **kwargs))
    second = _mc_scores(_run_mc(mc_project, **kwargs))
    np.testing.assert_array_equal(first, second)
