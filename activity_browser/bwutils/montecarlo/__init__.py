"""Monte Carlo LCA engine and helpers."""

from activity_browser.bwutils.montecarlo.engine import MonteCarloLCA, perform_MonteCarlo_LCA
from activity_browser.bwutils.montecarlo.matrix_patch import apply_matrix_utils_mc_patch
from activity_browser.bwutils.montecarlo.scenarios import build_overlay_from_df

apply_matrix_utils_mc_patch()  # TODO: remove once bw2data 4.8 includes the matrix_utils fix

__all__ = [
    "MonteCarloLCA",
    "perform_MonteCarlo_LCA",
    "apply_matrix_utils_mc_patch",
    "build_overlay_from_df",
]
