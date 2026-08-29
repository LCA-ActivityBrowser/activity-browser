"""Precomputed scenario matrix overlay (shared by SuperstructureMLCA and Monte Carlo)."""

# TODO: this should eventually be replaced by a "datapackage" based solution where bw datapackages are being used (For Montecarlo LCA incrementally for scenario data, uncertainty data and parameter uncertainty data)

from __future__ import annotations

from dataclasses import dataclass

import bw2calc as bc
import bw2data as bd
import numpy as np
from bw2data.backends import ExchangeDataset
from stats_arrays import distributions as sa

from activity_browser.bwutils.uncertainty import uncertainty_type_id
from activity_browser.bwutils.utils import Index
from activity_browser.bwutils.parameters.parameter_montecarlo import (
    matrix_coords_for_exchange,
)

_DETERMINISTIC_UNCERTAINTY_TYPES = frozenset(
    {
        sa.UndefinedUncertainty.id,
        sa.NoUncertainty.id,
    }
)

_MATRIX_NAMES = {
    "biosphere": "biosphere_matrix",
    "technosphere": "technosphere_matrix",
    "production": "technosphere_matrix",
    "substitution": "technosphere_matrix",
}


@dataclass(frozen=True)
class ScenarioOverlay:
    """Precomputed scenario amounts and matrix coordinates for MC overlay."""

    name: str
    indices: np.ndarray
    matrix_indices: np.ndarray
    amounts: np.ndarray
    uncertain: np.ndarray


def uncertainty_flags_for_indices(indices: np.ndarray) -> np.ndarray:
    """Return a bool array: True where the exchange has MC-relevant uncertainty.

    Any ``stats_arrays`` distribution (type id >= 2) is resampled when the
    technosphere/biosphere MC layer is on; only undefined/no-uncertainty are
    treated as deterministic for scenario pinning.
    """
    flags = np.zeros(len(indices), dtype=bool)
    for i, index in enumerate(indices):
        flags[i] = (
            exchange_uncertainty_type(index) not in _DETERMINISTIC_UNCERTAINTY_TYPES
        )
    return flags


def matrix_indices_for_multilca(
    lca: bc.MultiLCA, indices: np.ndarray
) -> np.ndarray:
    """Resolve ``(row, col, flip)`` on a ``MultiLCA`` (once per calculate)."""
    result = np.zeros(
        len(indices),
        dtype=[("row", np.uint32), ("col", np.uint32), ("flip", np.bool_)],
    )
    for i, index in enumerate(indices):
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
        _, row, col = coords
        result[i] = (row, col, index.flip)
    return result


def apply_scenario_overlay(
    lca: bc.MultiLCA,
    overlay: ScenarioOverlay,
    *,
    include_technosphere: bool,
    include_biosphere: bool,
    repin_only: bool = False,
) -> None:
    """Write scenario amounts into LCA matrices.

    Initial pass (``repin_only=False``): pin every scenario cell that should
    hold a fixed amount (layer off, or layer on but exchange deterministic).

    Re-pin pass (``repin_only=True``): only layers being MC-resampled; used after
    ``next()`` restored DB draws on uncertain cells while leaving pinned cells to
    be overwritten from the datapackage.
    """
    flow_types = np.array([idx.flow_type for idx in overlay.indices])
    for kind in np.unique(flow_types):
        mask = flow_types == kind
        idx = overlay.matrix_indices[mask]
        sample = overlay.amounts[mask].copy()
        uncertain = overlay.uncertain[mask]

        valid = ~np.isnan(sample)
        idx = idx[valid]
        sample = sample[valid]
        uncertain = uncertain[valid]
        if sample.size == 0:
            continue

        is_bio = kind in bd.labels.biosphere_edge_types
        layer_on = include_biosphere if is_bio else include_technosphere
        if repin_only:
            if not layer_on:
                continue
            keep = ~uncertain
            idx = idx[keep]
            sample = sample[keep]
        elif layer_on:
            keep = ~uncertain
            idx = idx[keep]
            sample = sample[keep]
        if sample.size == 0:
            continue

        flip = idx["flip"]
        sample[flip] *= -1

        matrix_name = _MATRIX_NAMES.get(kind, "technosphere_matrix")
        matrix = getattr(lca, matrix_name)
        matrix[idx["row"], idx["col"]] = sample

        if matrix_name == "technosphere_matrix" and hasattr(lca, "solver"):
            delattr(lca, "solver")


def exchange_uncertainty_type(index: Index) -> int:
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
