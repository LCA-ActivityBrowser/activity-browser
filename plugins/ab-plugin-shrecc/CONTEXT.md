# SHRECC plugin — Domain Context

Canonical glossary for the Activity Browser SHRECC plugin. Prefer these terms over synonyms. Host AB concepts (Project, Database, Plugin, …) stay in the Activity Browser root `CONTEXT.md`; this file covers plugin-only language and will move with the plugin when it becomes a standalone repo.

Architecture / host contracts: Activity Browser `docs/adr/0012-plugins-contribution-api.md` and `docs/plugins/`.

## Glossary

### SHRECC workflow

One closable tab on the SHRECC plugin page: a Brightway **project** this workflow uses, a configuration, optional in-memory Create results (Inspect), and optional Write of output databases. Stages are **Configure**, **Inspect**, and **Write**. Later stages (e.g. Analysis) may be added with the same always-visible, disabled-until-gated pattern; they are not shipped as placeholders. **Create** is a run action on Configure, not a stage.
_Avoid_: Create & inspect (as a stage name); treating Create as a stage

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

An in-flight Create or Write for this plugin; at most one plugin-wide at a time.

## Synonyms to avoid (prefer glossary term)

| Avoid drifting to… | Prefer |
|---|---|
| bound project | workflow project |
| project stale | project mismatch |
| inspect stale / stale (UI) | configuration mismatch |
| Create & inspect (stage) | Inspect stage; Create is an action |
| output database name on Configure | Write options on Write stage |
