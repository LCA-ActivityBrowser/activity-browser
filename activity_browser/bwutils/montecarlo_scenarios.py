"""Scenario amount overlay for Monte Carlo LCA (before uncertainty and parameter sampling)."""

from __future__ import annotations

from typing import Optional, Tuple

import bw2calc as bc
import bw2data as bd
import numpy as np
import pandas as pd
from bw2data.backends import ExchangeDataset
from stats_arrays import distributions as sa

from activity_browser.bwutils.superstructure.dataframe import (
    arrays_from_indexed_superstructure,
    filter_databases_indexed_superstructure,
    scenario_names_from_df,
)
from activity_browser.bwutils.uncertainty import uncertainty_type_id
from activity_browser.bwutils.utils import Index
from activity_browser.bwutils.parameters.parameter_montecarlo import (
    matrix_coords_for_exchange,
    write_matrix_amount,
)

# Exchange uncertainty types that keep database sampling when the MC layer is on.
_UNCERTAINTY_TYPES = frozenset(
    {
        sa.LognormalUncertainty.id,
        sa.NormalUncertainty.id,
        sa.TriangularUncertainty.id,
        sa.UniformUncertainty.id,
    }
)


def prepare_scenario_arrays(
    scenario_df: pd.DataFrame,
    databases: set[str],
    scenario: Optional[str | int] = None,
) -> Tuple[Optional[str], np.ndarray, np.ndarray]:
    """Resolve scenario column and return ``(name, index_array, amount_array)``."""
    df = filter_databases_indexed_superstructure(scenario_df, databases)
    names = scenario_names_from_df(df)
    if not names or df.empty:
        return None, np.array([], dtype=object), np.array([], dtype=float)

    if scenario is None:
        scenario = names[0]
    elif isinstance(scenario, int):
        scenario = names[scenario]

    indices, _ = arrays_from_indexed_superstructure(df)
    amounts = df[scenario].to_numpy(dtype=float)
    return scenario, indices, amounts


def apply_scenario_amounts(
    lca: bc.MultiLCA,
    indices: np.ndarray,
    amounts: np.ndarray,
    *,
    include_technosphere: bool,
    include_biosphere: bool,
) -> None:
    """Write scenario amounts when the MC layer is off or the exchange is deterministic."""
    for index, amount in zip(indices, amounts):
        if np.isnan(amount):
            continue
        is_bio = index.flow_type in bd.labels.biosphere_edge_types
        layer_on = include_biosphere if is_bio else include_technosphere
        if layer_on and _exchange_uncertainty_type(index) in _UNCERTAINTY_TYPES:
            continue

        coords = matrix_coords_for_exchange(
            lca,
            flow_type=index.flow_type,
            input_database=index.input.database,
            input_code=index.input.code,
            output_database=index.output.database,
            output_code=index.output.code,
            input_id=index.input_id,
            output_id=index.output_id,
        )
        if coords is None:
            continue
        matrix_name, row, col = coords
        value = -amount if index.flip else amount
        write_matrix_amount(lca, matrix_name, row, col, value)


def _exchange_uncertainty_type(index: Index) -> int:
    try:
        exc = ExchangeDataset.get(
            ExchangeDataset.input_code == index.input.code,
            ExchangeDataset.input_database == index.input.database,
            ExchangeDataset.output_code == index.output.code,
            ExchangeDataset.output_database == index.output.database,
        )
        return uncertainty_type_id(exc.data or {})
    except ExchangeDataset.DoesNotExist:
        return 0
