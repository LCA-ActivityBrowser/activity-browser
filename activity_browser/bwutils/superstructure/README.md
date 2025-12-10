# superstructure

Superstructure scenario analysis tools for Activity Browser.

## Overview

This directory implements superstructure functionality, which enables scenario-based LCA analysis. Superstructures allow users to model multiple scenarios within a single database by using parameters to switch between alternative technologies, processes, or supply chains.

## What is a Superstructure?

A superstructure is an LCA model that contains multiple possible configurations:
- Alternative technologies (e.g., different energy sources)
- Multiple scenarios (e.g., current vs. future)
- Prospective databases (e.g., from [premise](https://premise.readthedocs.io/))
- Switchable pathways (e.g., different material choices)

Parameters control which alternatives are "active" in each scenario.

## Key Concepts

### Scenarios
Named configurations that define parameter values:
```python
scenarios = {
    "baseline": {"electricity_grid_mix": 0.7, "renewable_share": 0.3},
    "high_renewable": {"electricity_grid_mix": 0.2, "renewable_share": 0.8}
}
```

### Parameters
Variables that control exchange amounts or activity selection:
- **Amount parameters** - Control exchange quantities
- **Switch parameters** - Enable/disable exchanges (0 or 1)
- **Share parameters** - Allocate between alternatives (sum to 1)

### Alternative Processes
Multiple activities representing different technology choices:
- Linked via parameterized exchanges
- Only one "active" per scenario
- Controlled by parameter values

## Features

### Scenario Management
- Create, edit, delete scenarios
- Copy scenarios for variations
- Compare scenarios side-by-side
- Switch between scenarios

### Parameter Configuration
- Define parameter ranges
- Set scenario-specific values
- Link parameters to exchanges
- Validate parameter consistency

### Scenario Calculations
- Run LCA for multiple scenarios
- Compare results across scenarios
- Visualize scenario differences
- Export scenario results

## Usage Pattern

### Creating a Superstructure
```python
from activity_browser.bwutils.superstructure import Superstructure

# Create superstructure
ss = Superstructure(name="Energy scenarios")

# Add scenarios
ss.add_scenario("baseline", parameters={...})
ss.add_scenario("high_renewable", parameters={...})
```

### Running Scenario Analysis
```python
# Calculate all scenarios
results = ss.calculate_scenarios()

# Compare results
comparison = ss.compare_scenarios(["baseline", "high_renewable"])
```

## Integration with Parameters

Superstructures leverage Activity Browser's parameter system:
- Project parameters define scenarios
- Database parameters set alternative values
- Activity parameters control exchanges
- Formulas link parameters together

See `app/pages/parameters/` for parameter management UI.

## Integration with Premise

Activity Browser supports prospective databases from [premise](https://premise.readthedocs.io/):
- Import premise scenarios
- Map to Activity Browser scenarios
- Run temporal LCA analyses
- Visualize future pathways

## Visualization

Superstructure results can be visualized as:
- **Bar charts** - Compare impacts across scenarios
- **Radar charts** - Multi-dimensional scenario comparison
- **Heatmaps** - Parameter sensitivity across scenarios
- **Sankey diagrams** - Flow differences between scenarios

## File Format

Superstructures can be saved/loaded:
```json
{
  "name": "Energy scenarios",
  "scenarios": {
    "baseline": {
      "parameters": {...},
      "description": "Current situation"
    },
    "future": {
      "parameters": {...},
      "description": "2050 scenario"
    }
  },
  "reference_flow": {...},
  "methods": [...]
}
```

## Development Guidelines

When working with superstructures:

1. **Validate parameters** - Ensure consistency across scenarios
2. **Check constraints** - Share parameters should sum to 1
3. **Handle errors** - Gracefully handle missing or invalid parameters
4. **Use threading** - Scenario calculations can be slow
5. **Cache results** - Avoid recalculating unchanged scenarios
6. **Emit signals** - Notify when scenarios change
7. **Support undo** - Allow reverting parameter changes

## Advanced Features

### Sensitivity Analysis
Test parameter importance:
```python
sensitivity = ss.sensitivity_analysis(
    parameter="renewable_share",
    range=(0, 1),
    steps=10
)
```

### Optimization
Find best parameter values:
```python
optimal = ss.optimize(
    objective="minimize_impact",
    constraints={...}
)
```

### Monte Carlo with Scenarios
Combine uncertainty and scenarios:
```python
results = ss.monte_carlo(
    scenario="future",
    iterations=1000
)
```

## Related Modules

- `app/pages/parameters/` - Parameter management UI
- `bwutils/multilca.py` - Multi-functional LCA calculations
- `bwutils/sensitivity_analysis.py` - Sensitivity analysis tools
- `bwutils/montecarlo.py` - Monte Carlo simulation
