"""Scenario starter template helpers (no Qt)."""
from pathlib import Path

import pandas as pd
from bw2data.tests import bw2test

from activity_browser.bwutils.superstructure import scenario_templates as scen_tpl


def test_scenario_template_paths_exist():
    for kind in ("parameter", "flow"):
        for fmt in ("xlsx", "csv"):
            path = scen_tpl.scenario_template_path(kind, fmt)
            assert path.is_file(), path


def test_copy_scenario_template(tmp_path: Path):
    dest = tmp_path / "my-flow.xlsx"
    out = scen_tpl.copy_scenario_template("flow", "xlsx", dest)
    assert out.is_file()
    assert out.suffix == ".xlsx"


@bw2test
def test_parameter_template_dataframe_has_example_columns():
    df = scen_tpl.parameter_template_dataframe()
    assert list(df.columns)[:3] == ["Name", "Group", "default"]
    assert list(df.columns)[3:] == list(scen_tpl.EXAMPLE_SCENARIO_COLS)
