"""
Brightway parameter recalculation and parameter Monte Carlo matrix overlay.

- :mod:`activity_browser.bwutils.parameters.manager` — formula chain and sampling
- :mod:`activity_browser.bwutils.parameters.parameter_montecarlo` — ``MultiLCA`` hook and matrix indices

See ``README.md`` in this directory.
"""

from activity_browser.bwutils.parameters.manager import (
    MonteCarloParameterManager,
    ParameterManager,
)
from activity_browser.bwutils.parameters.parameter_montecarlo import (
    activity_col_in_lca,
    activity_id_from_key,
    apply_parameter_exchanges,
    bind_parameter_hook,
    exchange_from_param_row,
    matrix_coords_for_param_row,
    product_row_in_lca,
)

__all__ = [
    "ParameterManager",
    "MonteCarloParameterManager",
    "bind_parameter_hook",
    "apply_parameter_exchanges",
    "matrix_coords_for_param_row",
    "exchange_from_param_row",
    "activity_id_from_key",
    "activity_col_in_lca",
    "product_row_in_lca",
]
