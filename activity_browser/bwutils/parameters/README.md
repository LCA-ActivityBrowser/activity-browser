# Parameter utilities (`bwutils/parameters`)

Brightway **parameter recalculation** and **parameter Monte Carlo** for Activity Browser calculation engines. Parameter editors live under `app/pages/parameters/`; this package is used by Monte Carlo LCA and related tools.

## Monte Carlo flow (parameters checkbox on)

```text
bd.parameters.recalculate()     # sync exchange amounts in DB (once)
        │
        ▼
MultiLCA + matrix/CF draws      # technosphere / biosphere / CF resampling each iteration
        │
        ▼
after_matrix_iteration hook     # sample uncertain params → recalc formulas
        │
        ▼
apply_parameter_exchanges()     # overwrite A/B matrix cells (parameters win on overlap)
        │
        ▼
LCI / LCIA → scores
```

## Modules

| Module | Role |
|--------|------|
| `manager.py` | `ParameterManager`, `MonteCarloParameterManager` — formula evaluation order (project → database → activity → exchanges) |
| `parameter_montecarlo.py` | Map recalculated amounts to `bw2calc` matrix indices; `functional_sqlite` process ↔ product via `bw_functional` |
| `utils.py` (parent `bwutils`) | `Parameter`, `Parameters`, `StaticParameters`, `Index`, `Indices` |

`montecarlo.MonteCarloLCA` wires the hook and sets `keep_first_iteration_flag = True` (reuse baseline matrix for iteration 0).

## Imports

```python
from activity_browser.bwutils.parameters import (
    MonteCarloParameterManager,
    bind_parameter_hook,
    activity_id_from_key,
)
```

Activity Browser loads `bw_functional` at startup (`__main__.py`). Standalone scripts using `functional_sqlite` must `import bw_functional` (see `scripts/test_parameter_mc.py`).

## `functional_sqlite`

Parameterized exchanges often reference the **process** code; `bw2calc` matrix columns use the **reference product**. `parameter_montecarlo.py` resolves that with `Process.products()` / `Product.processor`, not code suffixes.

Parameter **scenarios** (`convert_parameter_to_flow_scenarios.py`) use `activity_group_by_output_key()` for `(database, output_code)` → parameter group.

## Related code

- `commontasks.parameters_in_scope` — UI parameter scope
- `superstructure/convert_parameter_to_flow_scenarios.py` — scenario conversion (separate from MC hook)

## Future work

- Share recalculation with scenario conversion (override handling differs today)
- Scope `ParameterManager.indices` to calculation-setup databases
- Upstream matrix-index helpers in `bw2calc` / `bw_functional`
