# templates

Bundled spreadsheet templates shipped with Activity Browser (top-level package folder so they are easy to find).

## Layout

- **`scenarios/`** — scenario difference / parameter-scenario workbooks for calculation-setup Scenario mode
  - `flow-scenarios.xlsx` / `.csv` — empty flow scenario (SDF) headers; xlsx includes a `README` sheet
  - `parameter-scenarios.xlsx` / `.csv` — empty parameter scenario headers; xlsx includes a `README` sheet
- **`impact-categories/`** — LCIA / impact-category interchange starters
  - `ab-lcia.xlsx` / `ab-lcia.cfs.csv` + `ab-lcia.metadata.csv` — **AB impact-category file** (multi–impact-category; recommended default)
  - `bw2io-lcia.xlsx` / `bw2io-lcia.csv` + `bw2io-lcia.metadata.csv` — **bw2io impact-category file** (one impact category per CF file)

## Usage

Package path: `activity_browser/templates/`. Resolve at runtime via:

```python
from pathlib import Path
import activity_browser

templates = Path(activity_browser.__file__).resolve().parent / "templates"
flow = templates / "scenarios" / "flow-scenarios.xlsx"
```

Excel workbooks: **data sheet first**, then **`README`** (and metadata sheets where applicable).  
CSV files: header row, then notes on lines starting with `#` (ignored on import).

Scenario import comments (Excel and CSV):

- **Rows:** start with `#` in the first cell (CSV: `comment="#"`; Excel: `skiprows` — not `comment="#"`).
- **Columns:** name starts with `_` (e.g. `_notes`; dropped via `usecols`).

**Get template → flow-scenarios** always copies the empty starter file (does not generate from project parameters).

Impact categories: **Impact categories → Get template…** in the application menu (AB impact-category file is the default choice).

## Maintenance

- Keep column headers aligned with `SUPERSTRUCTURE` / parameter-scenario import expectations in `bwutils/superstructure`.
- Keep impact-category templates aligned with `bwutils.impact_categories`.
- When adding new `.xlsx` / `.csv` templates, include them in `MANIFEST.in` so they ship in wheels/sdists.
