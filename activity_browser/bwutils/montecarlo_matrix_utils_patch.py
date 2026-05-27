"""
Runtime patch for Brightway matrix_utils Monte Carlo NaN sampling.

When ``use_distributions=True`` and a matrix contains both uncertain and
deterministic entries, processed datapackages often store ``loc=NaN`` for
deterministic rows in the ``distributions`` vector. ``stats_arrays`` type 0/1
returns ``loc`` unchanged, so NaN enters technosphere, biosphere, and
characterization matrices.

Upstream fix: ``contrib/brightway-upstream/matrix_utils-resource_group.patch``
"""

from __future__ import annotations

import numpy as np

_PATCHED = False


def _sample_from_distributions(self) -> np.ndarray:
    """Draw from stats_arrays, but keep deterministic amounts from ``data``."""
    drawn = np.asarray(next(self.rng), dtype=np.float64)
    distributions = self.get_resource_by_suffix("distributions")
    deterministic = distributions["uncertainty_type"] < 2
    if not deterministic.any():
        return drawn
    static = self.get_resource_by_suffix("data")
    drawn = drawn.copy()
    drawn[deterministic] = static[deterministic]
    return drawn


def _calculate_patched(self, vector: np.ndarray = None):
    """``ResourceGroup.calculate`` with deterministic rows taken from ``data``."""
    from matrix_utils.aggregation import aggregate_with_sparse

    if self.empty:
        self.data_current = np.array([])
        return self.row_matrix, self.col_matrix, self.data_current

    if vector is not None:
        data = vector
    elif self.vector:
        if self.use_distributions and self.has_distributions:
            data = self._sample_from_distributions()
        else:
            try:
                data = next(self.data_original)
            except TypeError:
                data = self.data_original
    else:
        data = self.data_original[:, self.indexer.index % self.ncols]

    data = data.copy()
    data = self.apply_masks(data)

    try:
        data[self.flip] *= -1
    except KeyError:
        pass

    self.data_current = data.copy()

    if self.aggregate:
        return aggregate_with_sparse(
            self.row_masked,
            self.col_masked,
            data,
            self.count,
        )
    return self.row_matrix, self.col_matrix, data


def apply_matrix_utils_mc_patch() -> None:
    """Apply the matrix_utils MC patch once (idempotent)."""
    global _PATCHED
    if _PATCHED:
        return

    from matrix_utils.resource_group import ResourceGroup

    if getattr(ResourceGroup.calculate, "__name__", "") == "_calculate_patched":
        _PATCHED = True
        return

    ResourceGroup._sample_from_distributions = _sample_from_distributions
    ResourceGroup.calculate = _calculate_patched
    _PATCHED = True
