"""Tests for GSA (``sensitivity_analysis``) and uncertainty formatting for GSA tables."""

from __future__ import annotations

import numpy as np
import stats_arrays as sa

from activity_browser.bwutils.montecarlo import MonteCarloLCA
from activity_browser.bwutils.sensitivity_analysis import (
    GSA_COLUMNS,
    GSA_INDEX_COLUMN,
    GSA_NAME_COLUMN,
    GSA_TYPE_COLUMN,
    GSA_UNCERTAINTY_DIST_COLUMN,
    GSA_UNCERTAINTY_INFO_COLUMN,
    GlobalSensitivityAnalysis,
    get_CF_dataframe,
    get_lca,
)
from activity_browser.bwutils.uncertainty import (
    uncertainty_field_name,
    uncertainty_parameters_summary,
)
from fixtures.monte_carlo import CALCULATION_SETUP

# SALib delta needs enough MC iterations; keep ≥ 40 for full multi-layer GSA.
ITERATIONS = 40
SEED = 42

ALL_UNCERTAINTY_LAYERS = dict(
    technosphere=True,
    biosphere=True,
    cf=True,
    parameters=True,
)


def _run_mc(cs_name: str, **includes) -> MonteCarloLCA:
    mc = MonteCarloLCA(cs_name)
    mc.calculate(iterations=ITERATIONS, seed=SEED, **includes)
    return mc


def _run_gsa(mc: MonteCarloLCA) -> GlobalSensitivityAnalysis:
    gsa = GlobalSensitivityAnalysis(mc)
    gsa.perform_GSA(0, 0, 0.01, 0.01)
    return gsa


def test_triangular_uncertainty_summary():
    assert uncertainty_field_name(sa.TriangularUncertainty.id, "loc") == "Mode"
    assert (
        uncertainty_parameters_summary(
            {"uncertainty type": sa.TriangularUncertainty.id, "loc": 5.0, "minimum": 0.0, "maximum": 10.0}
        )
        == "Mode: 5.0; Minimum: 0.0; Maximum: 10.0"
    )


def test_get_cf_dataframe_uses_method_uncertainty(mc_project):
    cs = CALCULATION_SETUP
    lca = get_lca(cs["inv"][0], cs["ia"][0])
    dfcf, _ = get_CF_dataframe(lca, cs["ia"][0], only_uncertain_CFs=True)

    assert not dfcf.empty
    assert dfcf.iloc[0][GSA_TYPE_COLUMN] == "characterization factor"
    assert dfcf.iloc[0][GSA_UNCERTAINTY_DIST_COLUMN] == "Uniform"
    assert "Minimum:" in dfcf.iloc[0][GSA_UNCERTAINTY_INFO_COLUMN]


def test_mc_populates_cf_dict(mc_project):
    mc = _run_mc(mc_project, technosphere=False, biosphere=False, cf=True, parameters=False)
    assert len(mc.CF_dict[mc.methods[0]]) == ITERATIONS


def test_gsa_full_run_all_uncertainty_layers(mc_project_with_parameters):
    """End-to-end GSA with technosphere, biosphere, CF, and parameter MC uncertainty."""
    mc = _run_mc(mc_project_with_parameters, **ALL_UNCERTAINTY_LAYERS)
    assert mc.iterations == ITERATIONS

    gsa = _run_gsa(mc)
    assert gsa.df_final is not None and not gsa.df_final.empty
    assert list(gsa.df_final.columns) == list(GSA_COLUMNS)

    types = set(gsa.df_final[GSA_TYPE_COLUMN])
    assert types == {
        "technosphere",
        "biosphere",
        "characterization factor",
        "parameter",
    }
    assert gsa.df_final["delta"].notna().all()
    assert np.isfinite(gsa.df_final["delta"]).all()
    assert gsa.df_final["delta"].is_monotonic_decreasing


def test_gsa_runs_with_cf_uncertainty(mc_project):
    mc = _run_mc(mc_project, technosphere=False, biosphere=False, cf=True, parameters=False)
    gsa = _run_gsa(mc)

    assert gsa.df_final is not None and not gsa.df_final.empty
    assert (gsa.df_final[GSA_TYPE_COLUMN] == "characterization factor").any()
    assert list(gsa.df_final.columns) == list(GSA_COLUMNS)


def test_exchange_gsa_name_format(mc_project):
    mc = _run_mc(mc_project, technosphere=True, biosphere=False, cf=False, parameters=False)
    gsa = _run_gsa(mc)

    tech = gsa.df_final.loc[gsa.df_final[GSA_TYPE_COLUMN] == "technosphere"].iloc[0]
    assert " --> " in tech[GSA_NAME_COLUMN]
    assert tech[GSA_NAME_COLUMN].count("[GLO]") >= 2
    assert "(" not in tech[GSA_NAME_COLUMN]
    assert "(" in tech[GSA_INDEX_COLUMN]
    assert tech[GSA_INDEX_COLUMN] != tech[GSA_NAME_COLUMN]
    assert gsa.metadata.index.name == GSA_INDEX_COLUMN


def test_gsa_runs_with_parameter_uncertainty(mc_project_with_parameters):
    mc = _run_mc(
        mc_project_with_parameters,
        technosphere=False,
        biosphere=False,
        cf=False,
        parameters=True,
    )
    gsa = _run_gsa(mc)

    param = gsa.df_final.loc[gsa.df_final[GSA_TYPE_COLUMN] == "parameter"].iloc[0]
    assert "bio_amount" in param[GSA_NAME_COLUMN]
    assert param[GSA_INDEX_COLUMN] == param[GSA_NAME_COLUMN]
    assert "Minimum: 8.0" in param[GSA_UNCERTAINTY_INFO_COLUMN]
    assert "Maximum: 12.0" in param[GSA_UNCERTAINTY_INFO_COLUMN]
