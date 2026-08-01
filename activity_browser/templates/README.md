# templates

Bundled spreadsheet templates shipped with Activity Browser (top-level package folder so they are easy to find).

## Layout

- **`scenarios/`** — scenario difference / parameter-scenario workbooks for calculation-setup Scenario mode
  - `flow-scenarios.xlsx` / `.csv` — empty flow scenario (SDF) headers; xlsx includes a `README` sheet
  - `parameter-scenarios.xlsx` / `.csv` — empty parameter scenario headers; xlsx includes a `README` sheet

Future additions may include Brightway Excel database examples under additional subfolders (e.g. `databases/`).

## Usage

Package path: `activity_browser/templates/`. Resolve at runtime via:

```python
from pathlib import Path
import activity_browser

templates = Path(activity_browser.__file__).resolve().parent / "templates"
flow = templates / "scenarios" / "flow-scenarios.xlsx"
```

Excel workbooks: **data sheet first**, then **`README`**.  
CSV files: header row, blank rows, then notes on lines starting with `#` (ignored on import).

Rows or columns whose first cell / header starts with `#` are ignored by scenario import (Excel and CSV).

**Get template → flow-scenarios** always copies the empty starter file (does not generate from project parameters).

## Maintenance

- Keep column headers aligned with `SUPERSTRUCTURE` / parameter-scenario import expectations in `bwutils/superstructure`.
- When adding new `.xlsx` / `.csv` templates, include them in `MANIFEST.in` so they ship in wheels/sdists.
