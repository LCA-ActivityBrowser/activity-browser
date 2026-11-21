# MetaDataStore reloads on Brightway `on_database_write` (hold under `SafeBWConnection`)

A full `Database.write` replaces inventory without per-activity signals, so the **Metadata store** refreshes by listening to Brightway’s `on_database_write`—not via call-site helpers on importers. That blinker can fire while a worker still holds SQLite (`SafeBWConnection` open), and modal `processEvents` can run a GUI reload too early (NULL names → UI `nan`). **Decision:** `request_metadata_reload(name)` schedules immediately, or while `hold_metadata_reloads()` is active only remembers names. On `SafeBWConnection` exit: close peewee, then `release_metadata_reloads()` (schedules each remembered name). Do not wrap Brightway’s `send`. Parameterized-flow rebuild keeps normal blinker timing via `ABSignals` (ADR-0010). Writers must emit (`signal=True` or equivalent `.send()`); silent writes stay stale. Register→`add_database` may load early; the write notification is authoritative. Excel/BW2Package must not schedule metadata reload themselves.

## Considered Options

- Call-site post-thread `schedule_*` on importers — two paths only; re-teaches every writer.
- Wrap/defer Brightway `on_database_write.send` — correct but hard to reason about.
- Eager schedule on blinker with no hold — races worker + `processEvents`.

## Consequences

- Only Metadata store reload scheduling is held; other blinker listeners see the write when Brightway sends it.
- Reload scheduler is created on the GUI thread at loader init; `schedule_database_metadata_reload` only emits.
- Holding is per-thread (`names is None` vs a `set`); `SafeBWConnection` is only used once around `ABThread.run_safely`.
