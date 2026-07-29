# Agent documentation map

Human-oriented overview of how Activity Browser stores context, rules, and architecture guidance for AI agents (and for developers who work with those agents).

If you forget how this was set up, **start here**.

## Maintenance

When you change how agent documentation is organized — new or removed `.cursor/rules`, move `CONTEXT.md` / `docs/adr` / `docs/agents`, switch issue tracker, or change the S/M/L workflow — **update this README in the same change**. The same requirement is encoded in `.cursor/rules/development-workflow.mdc`.

## What is committed vs local-only

| Path | Committed? | Purpose |
|---|---|---|
| `AGENTS.md` | Yes | Primary entry point for agents (architecture, placement, testing, CI pointers) |
| `CONTEXT.md` | Yes | Domain glossary (agents + developers; not a public docs-site glossary) |
| `docs/adr/` | Yes | Architecture Decision Records |
| `docs/agents/` | Yes | This map + Matt Pocock skill config (tracker, domain, triage) |
| `.cursor/rules/` | Yes | Cursor rules (workflow + per-module conventions) |
| `.github/copilot-instructions.md` | Yes | Thin pointer to `AGENTS.md` for GitHub Copilot |
| `.scratch/` | **No** (gitignored) | Local specs and tickets while trying the workflow |

Skills themselves (e.g. `/grill-with-docs`, `/to-spec`) live in the developer’s agent skills install (e.g. `~/.agents/skills/`), not in this repo. This repo only records **how** those skills should behave here via `docs/agents/*.md`.

## How the pieces relate

```text
AGENTS.md          ← agents read this first
    │
    ├── CONTEXT.md              domain vocabulary
    ├── docs/adr/               hard-to-reverse decisions
    ├── docs/agents/            this map + skill config
    ├── .cursor/rules/          always-on + path-scoped conventions
    └── .github/copilot-…       points back to AGENTS.md

S/M/L workflow     ← .cursor/rules/development-workflow.mdc
    │
    ├── S: consult docs → implement → /code-review
    ├── M: /grill-with-docs → /to-spec → /implement → /code-review
    └── L: … → /to-tickets (local .scratch/) → /implement → /code-review
```

Slash skills with `disable-model-invocation` are **not** auto-run. The workflow rule classifies work and **asks the human** to invoke the next `/skill`. The rule is the traffic light; the skills are the workstations.

## Files in `docs/agents/`

| File | Role |
|---|---|
| `README.md` | This map |
| `issue-tracker.md` | Where specs/tickets live (currently **local** `.scratch/`) |
| `domain.md` | How skills should consume `CONTEXT.md` and ADRs |
| `triage-labels.md` | Mapping for triage role labels |

## Module READMEs (code-adjacent)

Package-level notes remain useful and are not replaced by this tree:

- `activity_browser/app/README.md`
- `activity_browser/ui/README.md`
- `activity_browser/bwutils/README.md`
- `activity_browser/mod/README.md`
- `tests/README.md`

## Switching to GitHub Issues later

Issue tracker is **local by choice** while the workflow is proven. To move to GitHub Issues for collaborative agent tickets, update `issue-tracker.md` (and the `## Agent skills` blurb in `AGENTS.md`) and refresh this README in the same change. Re-running `/setup-matt-pocock-skills` is optional if you prefer to edit the files directly.
