# SHRECC plugin — Domain Context

Canonical glossary for the Activity Browser SHRECC plugin. Prefer these terms over synonyms. Host AB concepts (Project, Database, Plugin, …) stay in the Activity Browser root `CONTEXT.md`; this file covers plugin-only language and will move with the plugin when it becomes a standalone repo.

Architecture / host contracts: Activity Browser `docs/adr/0012-plugins-contribution-api.md` and `docs/plugins/`. Plugin-local decisions: `docs/adr/` in this package.

## Glossary

### SHRECC Explorer

Plugin-level exploration surface on the SHRECC plugin page: a fixed top-level tab, sibling to **SHRECC workflow** tabs (not inside a workflow). Always available; not gated on Create; not a workflow stage. Purpose today: explore locally available SHRECC-derived datasets before (or without) configuring Create. Reads from the same **data directory** root as Create, via explorer-ready datasets derived from that root (not from in-memory Create results). For v1, the exploration UI is the existing standalone explorer embedded in this tab (not a Qt reimplementation of its pages). The explorer application is supplied by the separate Brightway-free explorer distribution the plugin depends on—not by vendoring page scripts into the plugin. The tab has thin host chrome for data-directory status, **Explorer prepare**, and embed errors; the embedded UI can also be opened in an external browser when the in-tab view feels too tight. **Open in browser** uses the same explorer server as the embedded view (one process).
_Avoid_: Analysis stage; Explore stage; treating Explorer as part of a SHRECC workflow; treating Explorer as Create-gated; treating a Qt rewrite of explorer pages as the v1 plan; treating a local checkout path as the primary distribution model; putting Prepare only inside the embedded explorer UI for v1; a second explorer server just for the external browser

### Data directory

Plugin Settings path for the shared on-disk SHRECC data root used by Create (SHRECC cache / downloads) and by **SHRECC Explorer** (explorer-ready datasets under that root). When unset, SHRECC’s own default location applies.
_Avoid_: explorer-only data path as a separate Settings concept (for the shared-root design); calling NetCDF exports “the cache” without distinguishing them from SHRECC’s working cache

### Explorer prepare

Explicit user action that builds or refreshes explorer-ready datasets (contract NetCDF and needed summaries) from SHRECC cache under the **data directory**. Not automatic on opening **SHRECC Explorer**; not part of Create. Requires usable cache under the data directory; if neither cache nor explorer-ready datasets exist, **SHRECC Explorer** stays on host chrome with an empty state and does not start the embedded explorer until an explorer-ready dataset is available.
_Avoid_: silent auto-export on tab open; treating Prepare as Create; starting the embedded explorer with no explorer-ready dataset

### SHRECC workflow

One closable tab on the SHRECC plugin page: a Brightway **project** this workflow uses, a configuration, optional in-memory Create results (Inspect), and optional Write of output databases. Stages are **Configure**, **Inspect**, and **Write**. Later Create-coupled stages (e.g. Analysis of Create outputs) may be added with the same always-visible, disabled-until-gated pattern; they are not shipped as placeholders and are distinct from **SHRECC Explorer**. **Create** is a run action on Configure, not a stage.
_Avoid_: Create & inspect (as a stage name); treating Create as a stage; treating SHRECC Explorer as a workflow stage

### Workflow project

The Brightway project a SHRECC workflow uses for Create and Write. Shown as that project’s name; not a separate “binding” concept.
_Avoid_: bound project

### Project mismatch

The workflow project is not the currently open Brightway project. UI explains both names and offers to switch the workflow to the open project.
_Avoid_: project stale; bound/stale project (in user-facing copy)

### Configuration mismatch

Configure changed after the last successful Create, so Inspect no longer matches the form. Inspect stays available and keeps showing the last Create results, with a banner that configuration changed and to Create again before Write. Write stays blocked until Create succeeds again.
_Avoid_: inspect stale; stale (alone, in user-facing copy)

### Configure (stage)

The SHRECC workflow stage where the user edits Create-time settings (years, countries, background databases, TYNDP, time, resolution, and related inventory options). Hosts the **Create** run action. Does not include Write-time output database naming or overwrite confirm. Year picking may still allow free entry today; the intended end state is to enable only years for which SHRECC source data is available (prospective years from SHRECC’s TYNDP set; historical years from Energy Charts availability), e.g. a picker built from `suggested_years()` plus prospective styling — deferred follow-up, not current UI.
_Avoid_: putting output database name on Configure

### Inspect (stage)

The SHRECC workflow stage that shows Create quality results: mapping gaps, inventory preview, and create log as named collapsible sections (no A–D letter prefixes). Sections start collapsed when Inspect first becomes available. Does not own output naming or the year write-plan table (those live on Write). Enabled after a successful Create; remains available under configuration mismatch; Write does not. If **Create again** fails after a prior success, Inspect stays available and keeps showing the last successful artifacts (with a failure banner); Write stays blocked until Create succeeds again.
_Avoid_: Resolved config / output database columns on Inspect

### Write (stage)

The SHRECC workflow stage that writes Create outputs into Brightway databases. Holds **Write options** (output database base name + per-year preview) and one **write plan** table: year, source, background database, output database, and New / Will overwrite status. Enabled only when Create succeeded and there is no configuration mismatch (and no project mismatch for the write action). Changing Write options does not cause configuration mismatch.

### Write options

Settings that affect only the Write action: output database naming and whether overwriting existing Brightway databases is confirmed. Stored on the workflow separately from Configure config (not part of the Create fingerprint). Edited on Write: one **output database base name** field plus a live per-year preview (same derivation rules as today’s name preview). Seeded with a default base name such as `shrecc_electricity` when the workflow is created; duplicated with the workflow. Create passes this name into SHRECC as `my_db_name` at construction; Write applies the resolved per-year names to the create handle before `write()`.
_Avoid_: treating output database name as Configure / Create input; dual editors on Configure and Write; requiring per-year name editors for the default UX; keeping `my_db_name` in the Configure fingerprint

### Create (action)

Run action on Configure that builds in-memory SHRECC artifacts for Inspect. Not a workflow stage. UI uses a green run button (calculation-setup style fill; no forward icon until a plugins-safe icon API exists). Label is **Create** on a fresh workflow; **Create again** when retrying after configuration mismatch or a failed Create.
_Avoid_: Create stage; Create & inspect

### TYNDP scenario

ENTSO-E storyline code for prospective electricity mixes in SHRECC. Not an Activity Browser Scenario LCA scenario.
_Avoid_: scenario (alone when meaning TYNDP); Scenario LCA scenario

### Plugin job

An in-flight Create, Write, or **Explorer prepare** for this plugin; at most one plugin-wide at a time.
_Avoid_: allowing Prepare in parallel with Create/Write; treating the embedded explorer process itself as a Plugin job

## Synonyms to avoid (prefer glossary term)

| Avoid drifting to… | Prefer |
|---|---|
| bound project | workflow project |
| project stale | project mismatch |
| inspect stale / stale (UI) | configuration mismatch |
| Create & inspect (stage) | Inspect stage; Create is an action |
| Analysis / Explore stage (for pre-Create browsing) | SHRECC Explorer |
| Separate explorer data path (under shared-root design) | data directory |
| Auto-export on Explorer open | Explorer prepare |
| Prepare in parallel with Create/Write | Plugin job (serial) |
| Start embedded explorer with no prepared dataset | empty state on host chrome |
| output database name on Configure | Write options on Write stage |
