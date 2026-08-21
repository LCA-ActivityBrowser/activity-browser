# Parameterized Flows follow Brightway’s `ParameterizedExchange` index

The Parameters page **Parameterized Flows** table, recalculation, and Monte Carlo all use Brightway’s `ParameterizedExchange` index (activity-parameter group), not a scan of formula-bearing flows. A `bwutils` helper rebuilds that index for the **written** database on `on_database_write` when the database is small or already has parameters. **Small** means at most **1,000 outgoing flows**. Skip databases above that cap that have no database/activity parameters; otherwise delete that database’s index rows, index every process that has a formula-bearing flow (dummy activity parameter if needed), then recalculate those groups. A database over the cap that already has parameters still gets a full pass. Single-flow formula edits stay on ExchangeModify. No one-shot backfill of existing projects.

Brightway `Database.write` sends `on_database_write` only when `projects.dataset.is_sourced` is true (default false), or when the caller passes `signal=True`. Excel import extra-sends that signal after bw2io writes with signals off. Database duplicate and BW25 migration pass `signal=True` so the same handler rebuilds the copy.

## Considered Options

- Scan formula-bearing flows on every Parameters-page sync (shows flows that will not recalculate).
- Fill the index only on Excel import via bw2io `activate_parameters` (misses database-parameter-only processes and other writes).
- One-shot backfill of open projects (rejected: user rebuilds those by rewrite).
