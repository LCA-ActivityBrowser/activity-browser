"""Parameter scenarios (project / database / activity) → flow scenarios → SuperstructureMLCA."""

from __future__ import annotations

import pandas as pd
import pytest
from bw2data.parameters import ActivityParameter
from bw2data.tests import bw2test

import bw2data as bd

from activity_browser.bwutils.superstructure.manager import SuperstructureManager
from activity_browser.bwutils.superstructure.mlca import SuperstructureMLCA
from activity_browser.bwutils.superstructure.utils import parameters_to_sdf
from fixtures.bw_helpers import (
    register_parameter_setup,
    write_calculation_setup,
    write_functional_database,
    write_method,
)
from fixtures.database_roundtrip import functional_data, parameter_setup

DB_NAME = "fuel_elec"


@pytest.fixture
@bw2test
def fuel_elec_with_all_parameter_levels():
    """Elec consumes fuel; fuel emits CO₂.

    Exchange formula: ``share * db_mult * proj_mult`` so each parameter level
    can scale the technosphere amount independently.
    """
    bio = bd.config.biosphere
    bd.Database(bio).register()
    bd.Database(bio).write(
        {
            (bio, "co2"): {
                "name": "Carbon dioxide",
                "code": "co2",
                "unit": "kg",
                "type": "emission",
                "categories": ("air",),
                "database": bio,
                "exchanges": [],
            }
        }
    )

    data = functional_data(DB_NAME, parameters=False)
    data[(DB_NAME, "elec_proc")]["exchanges"].append(
        {"input": (DB_NAME, "fuel_prod"), "type": "technosphere", "amount": 0.5}
    )
    data[(DB_NAME, "fuel_proc")]["exchanges"].append(
        {"input": (bio, "co2"), "type": "biosphere", "amount": 1.0}
    )
    write_functional_database(DB_NAME, data, process=True)

    bd.parameters.new_project_parameters(
        [{"name": "proj_mult", "amount": 1.0, "formula": ""}]
    )
    bd.parameters.new_database_parameters(
        [{"name": "db_mult", "amount": 1.0, "formula": ""}],
        DB_NAME,
    )
    setup = parameter_setup(DB_NAME, process_code="elec_proc")
    setup["parameterized_exchanges"][0]["formula"] = "share * db_mult * proj_mult"
    register_parameter_setup(DB_NAME, setup)

    write_method("GWP", [((bio, "co2"), 1.0)])
    write_calculation_setup(
        "cs1",
        {"inv": [{(DB_NAME, "elec_prod"): 1}], "ia": [("GWP",)]},
    )
    return DB_NAME


def test_project_database_activity_parameter_scenarios_convert_and_run_mlca(
    fuel_elec_with_all_parameter_levels,
):
    act_group = str(ActivityParameter.get(ActivityParameter.name == "share").group)
    param_scenarios = pd.DataFrame(
        [
            {
                "Name": "proj_mult",
                "Group": "project",
                "default": 1.0,
                "baseline": 1.0,
                "project_high": 2.0,
                "database_high": 1.0,
                "activity_high": 1.0,
            },
            {
                "Name": "db_mult",
                "Group": DB_NAME,
                "default": 1.0,
                "baseline": 1.0,
                "project_high": 1.0,
                "database_high": 2.0,
                "activity_high": 1.0,
            },
            {
                "Name": "share",
                "Group": act_group,
                "default": 0.5,
                "baseline": 0.5,
                "project_high": 0.5,
                "database_high": 0.5,
                "activity_high": 1.0,
            },
        ]
    )

    flow_df = parameters_to_sdf(param_scenarios)
    # Formula share * db_mult * proj_mult
    assert float(flow_df["baseline"].iloc[0]) == pytest.approx(0.5)
    assert float(flow_df["project_high"].iloc[0]) == pytest.approx(1.0)
    assert float(flow_df["database_high"].iloc[0]) == pytest.approx(1.0)
    assert float(flow_df["activity_high"].iloc[0]) == pytest.approx(1.0)

    # Same post-processing the CS scenario UI applies before calculate.
    flow_df = SuperstructureManager(flow_df).combined_data()
    mlca = SuperstructureMLCA("cs1", flow_df)
    mlca.calculate()
    scores = mlca.lca_scores_to_dataframe()
    baseline = float(scores.iloc[0][("GWP", "baseline")])
    assert baseline > 0
    assert float(scores.iloc[0][("GWP", "project_high")]) == pytest.approx(
        2 * baseline
    )
    assert float(scores.iloc[0][("GWP", "database_high")]) == pytest.approx(
        2 * baseline
    )
    assert float(scores.iloc[0][("GWP", "activity_high")]) == pytest.approx(
        2 * baseline
    )
