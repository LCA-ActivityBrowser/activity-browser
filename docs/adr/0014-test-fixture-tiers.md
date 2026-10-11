# Test fixture tiers: cheapest Brightway boot that still asserts

Activity Browser tests default to the cheapest fixture that still expresses the assertion: a per-test Brightway project without the main window or MetaDataStore for domain/actions; a Qt widget plus that project (owned via the Qt test helper) when only widget/model behavior is needed; and the full database + main window fixture only for UI chrome or MetaDataStore behavior. Read-only tests in one module may share a module-scoped Brightway project; mutating tests keep per-test isolation. Keep about one expensive UI/MDS smoke per feature area so the suite stays lean without losing wiring coverage.

## Status

accepted

## Consequences

- Prefer merging asserts over adding another MetaDataStore boot.
- Do not add OS-specific skips or pytest markers solely for speed without revisiting this ADR.
- Day-to-day cheat sheet: `tests/README.md`.
