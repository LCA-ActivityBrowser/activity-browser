"""
Unit tests for parameter Monte Carlo matrix mapping (``parameter_montecarlo`` module).
"""

from __future__ import annotations

import bw2calc as bc
import bw2data as bd

from activity_browser.bwutils.parameters import (
    MonteCarloParameterManager,
    apply_parameter_exchanges,
    matrix_coords_for_param_row,
)


def test_parameter_rows_map_to_lca_matrices(mc_project_with_parameters):
    cs = bd.calculation_setups[mc_project_with_parameters]
    fu_key = list(cs["inv"][0].keys())[0]
    demands = {"0": {bd.get_activity(fu_key).id: 1.0}}
    methods = cs["ia"][:1]

    bd.parameters.recalculate()
    data_objs = bd.get_multilca_data_objs(
        functional_units=demands,
        method_config={"impact_categories": methods},
    )
    lca = bc.MultiLCA(
        demands=demands,
        method_config={"impact_categories": methods},
        data_objs=data_objs,
        selective_use={
            "technosphere_matrix": {"use_distributions": False},
            "biosphere_matrix": {"use_distributions": False},
            "characterization_matrix": {"use_distributions": False},
        },
        seed_override=42,
    )
    lca.lci()

    param_rows = MonteCarloParameterManager(seed=42).next()
    assert len(param_rows) >= 1

    mapped = sum(
        1 for row in param_rows if matrix_coords_for_param_row(lca, row) is not None
    )
    assert mapped >= 1

    updated = apply_parameter_exchanges(lca, param_rows)
    assert updated >= 1
