---
title: Parameter scenario files
parent: Advanced topics
---
# Parameter scenario files
{: .fs-9 }

How to structure Excel or CSV files when you want to vary **Brightway parameters** across scenarios in Activity Browser.
{: .fs-6 .fw-300 }

## What this file type is for

Parameter scenario files list **which parameters** you want to touch and **what values** they take in each named scenario (column). Activity Browser uses the same parameter definitions, groups, and formulas already stored in your project.

On **import**, a parameter scenario file is **converted automatically** into an internal **flow (superstructure) scenario table**: the tool resolves formulas, finds the affected exchanges, and builds the rows expected for calculation. You normally edit parameters; the software derives the flow-level changes.

You can **save or export** the scenario from the calculation setup like any other scenario table; the exported file will be in **flow scenario** form (superstructure columns plus scenario value columns), not in the original parameter layout.

## Required columns

The importer recognizes a parameter scenario file when the table contains **exactly** these two headers (spelling and casing matter):

- **`Name`** — Brightway parameter name, as in the Parameters tables.
- **`Group`** — Parameter group, as in Brightway: e.g. `project` for global parameters, a **database name** for database-scoped parameters, or the **activity parameter group** for activity-scoped parameters.

Every other column (except the optional `default` column below) is treated as a **scenario**: its header becomes the scenario name, and the cells are numeric overrides for that scenario.

## Optional `default` column

You may include a column named **`default`** (case-insensitive: `default`).

- It is **only for your own reference** (documentation, reporting, or sharing the file with colleagues).
- Activity Browser **does not use** this column when building scenarios or evaluating formulas. It does **not** act as a fallback value for empty scenario cells.

So: keep `default` if it helps you document intended baselines, but the calculations rely on **project data** and the **scenario columns**, not on that column.

## Scenario columns and empty cells

Each scenario column holds the value you want for the given `(Group, Name)` parameter **in that scenario**.

- If a cell contains a **number**, that value is applied for that scenario (and, for parameters that also have a stored formula, an explicit cell **overrides** the formula for that parameter in that scenario so your number is respected).
- If a cell is **empty** (or otherwise missing), Activity Browser **does not** treat that as “read the `default` column”. Instead, the parameter keeps the **`amount` currently stored in your Brightway project** for that parameter when the scenario row is filled in. In other words: leave a cell blank when you want **no change** from what is already in the database for that parameter in that scenario.

If you need every scenario to start from a specific baseline you only have on paper, either enter those numbers in each scenario column or update the parameter amounts in Brightway first; the spreadsheet `default` column alone will not enforce that baseline in the tool.

## Practical layout example

| Name   | Group              | default | Low COP | High COP |
|--------|--------------------|--------:|--------:|---------:|
| COP    | my_foreground_db   | 3.5     | 3.0     | 4.2      |
| P1     | my_foreground_db   | 1.0     |         | 1.1      |

- **`Low COP`** and **`High COP`** are two scenarios.
- The `default` column is optional documentation; it is ignored by the conversion.
- Empty **`P1`** under **Low COP** means: use the stored project amount for `P1` in that scenario.

Scenario columns keep the **order they have in the file** in the resulting flow scenario table.

## What gets converted to flows

The conversion considers **formula-bearing exchanges** linked to your parameters, in line with your model. The set of **`Group`** values that appear in the file helps determine **which output databases / scopes** are in play. Parameters that only exist in the file but not in the project, or rows with no matching exchanges, can lead to errors or empty results—your parameter definitions should match the project.

## File formats and import

You can use the same formats as for other scenario imports supported in the Calculation Setup (e.g. Excel `.xlsx` / `.xls`, CSV). The file is read as a table; ensure **`Name`** and **`Group`** are present so Activity Browser selects **parameter scenario** mode rather than a raw flow scenario file.

## Related reading

- [Scenario calculations](scenario-calculations.md) — combining scenarios, extending scenarios, and the difference between parameter and flow scenarios at a high level.
