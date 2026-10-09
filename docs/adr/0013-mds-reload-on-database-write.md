# MetaDataStore reloads on Brightway `on_database_write` (hold under `SafeBWConnection`)

A full `Database.write` replaces inventory without per-activity signals, so the **Metadata store** refreshes by listening to Brightway’s `on_database_write`—not via call-site helpers on importers. That blinker can fire while a worker still holds SQLite (`SafeBWConnection` open), and modal `processEvents` can run a GUI reload too early (NULL names → UI `nan`). The same worker also flushes database metadata, and those handlers were applying the Metadata store and emitting `databases_changed` on the worker while the GUI event loop was already running — pandas and a GUI `QObject` off the GUI thread abort CPython 3.11 on Linux. **Decision:** `request_metadata_reload(name)` schedules immediately, or while `hold_metadata_reloads()` is active only remembers names. While that hold is active, `MDSUpdater` does not sync the dataframe (no `load_database` on the worker) and `ABSignals` does not emit `databases_changed`; both wait for release. On `SafeBWConnection` exit: close peewee, then `release_metadata_reloads()` (schedules each remembered name, then posts queued GUI callbacks). Do not wrap Brightway’s `send`. Parameterized-flow rebuild keeps normal blinker timing via `ABSignals` (ADR-0010). Writers must emit (`signal=True` or equivalent `.send()`); silent writes stay stale. On the GUI thread, register→`add_database` may load early; under a hold the write notification is authoritative. Excel/BW2Package must not schedule metadata reload themselves.

## Considered Options

- Call-site post-thread `schedule_*` on importers — two paths only; re-teaches every writer.
- Wrap/defer Brightway `on_database_write.send` — correct but hard to reason about.
- Eager schedule on blinker with no hold — races worker + `processEvents`.

## Consequences

- Metadata reload scheduling, dataframe sync on database-metadata change, and the `databases_changed` UI emit are held. Parameterized-flow rebuild still runs on the writing thread before peewee connections close.
- Reload scheduler is created on the GUI thread at loader init. `schedule_database_metadata_reload` and held callbacks only emit; slots run on the GUI thread (`QueuedConnection`).
- Holding is per-thread (`names is None` vs a `set`); `SafeBWConnection` is only used once around `ABThread.run_safely`.
