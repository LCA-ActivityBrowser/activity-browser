"""Build scenario overlays from dataframes (fallback when ``SuperstructureMLCA`` is unavailable)."""

# TODO: this should eventually be replaced by a "datapackage" based solution where bw datapackages are being used (For Montecarlo LCA incrementally for scenario data, uncertainty data and parameter uncertainty data)

from __future__ import annotations

from typing import Optional

import bw2calc as bc
import pandas as pd

from activity_browser.bwutils.superstructure.scenario_overlay import (
    ScenarioOverlay,
    matrix_indices_for_multilca,
    uncertainty_flags_for_indices,
)
from activity_browser.bwutils.superstructure.dataframe import (
    arrays_from_indexed_superstructure,
    filter_databases_indexed_superstructure,
    scenario_names_from_df,
)


def build_overlay_from_df(
    lca: bc.MultiLCA,
    scenario_df: pd.DataFrame,
    databases: set[str],
    scenario: Optional[str | int] = None,
) -> Optional[ScenarioOverlay]:
    """Build overlay from a scenario dataframe (tests / fallback without ``SuperstructureMLCA``)."""
    df = filter_databases_indexed_superstructure(scenario_df, databases)
    names = scenario_names_from_df(df)
    if not names or df.empty:
        return None

    if scenario is None:
        scenario = names[0]
    elif isinstance(scenario, int):
        scenario = names[scenario]

    indices, _ = arrays_from_indexed_superstructure(df)
    amounts = df[scenario].to_numpy(dtype=float)
    return ScenarioOverlay(
        name=scenario,
        indices=indices,
        matrix_indices=matrix_indices_for_multilca(lca, indices),
        amounts=amounts,
        uncertain=uncertainty_flags_for_indices(indices),
    )
