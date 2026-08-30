# Agent documentation map

Human-oriented overview of how Activity Browser stores context, rules, and architecture guidance for AI agents (and for developers who work with those agents).

If you forget how this was set up, **start here**.

This tree is **not** part of the public GitHub Pages site. AB docs for LCA practitioners live only under `docs/` (see ADR-0018).

## Maintenance

When you change how agent documentation is organized — new or removed `.cursor/rules`, move `CONTEXT.md` / `adr` / `.agents`, switch issue tracker, or change the S/M/L workflow — **update this README in the same change**. The same requirement is encoded in `.cursor/rules/development-workflow.mdc`.

## What is committed vs local-only

| Path | Committed? | Purpose |
|---|---|---|
| `AGENTS.md` | Yes | Primary entry point for agents (architecture, placement, testing, CI pointers) |
| `CONTEXT.md` | Yes | Domain glossary (agents + developers; not a public docs-site glossary) |
| `adr/` | Yes | Architecture Decision Records (engineering audience; not published on Pages) |
| `.agents/` | Yes | This map + Matt Pocock skill config (tracker, domain, triage) |
| `docs/` | Yes | AB docs site for AB users (LCA practitioners) |
| `.cursor/rules/` | Yes | Cursor rules (workflow + per-module conventions) |
| `.github/copilot-instructions.md` | Yes | Thin pointer to `AGENTS.md` for GitHub Copilot |
| `.scratch/` | **No** (gitignored) | Local specs and tickets while trying the workflow |

Skills themselves (e.g. `/grill-with-docs`, `/to-spec`) live in the developer’s agent skills install (e.g. `~/.agents/skills/`), not in this repo. This repo only records **how** those skills should behave here via `.agents/*.md`.

## Three audiences

| Audience | Home | Voice / use |
|---|---|---|
| **AB docs** | `docs/` | AB users (LCA practitioners); GitHub Pages |
| **Engineering** | `adr/` (+ `CONTRIBUTING.md`, module READMEs) | Human contributors and agents; decision records |
| **Agent steering** | `.agents/`, root `AGENTS.md` / `CONTEXT.md`, `.cursor/rules/` | Agents and maintainers of agent workflow |

## AB docs (`docs/`) — agent policy

- **Read** `docs/` when AB/UI behavior matters; it often has useful practitioner-facing context.
- After behavior-changing work, **check** whether `docs/` needs updating for LCA practitioners.
- If yes, **edit** those pages (default: edit-then-flag — list the `docs/` changes and ask the user to confirm). Ask first only for large rewrites or undecided AB behavior.
- Keep `docs/` language oriented at **AB users (LCA practitioners)**, not agents or programmers. Implementation detail belongs in `adr/`, `.agents/`, module READMEs, or `AGENTS.md` / `CONTEXT.md`.

## How the pieces relate

```text
AGENTS.md          ← agents read this first
    │
    ├── CONTEXT.md              domain vocabulary
    ├── adr/                    hard-to-reverse decisions
    ├── .agents/                this map + skill config
    ├── docs/                   AB docs (read; edit with check + user confirm)
    ├── .cursor/rules/          always-on + path-scoped conventions
    └── .github/copilot-…       points back to AGENTS.md

S/M/L workflow     ← .cursor/rules/development-workflow.mdc
    │
    ├── S: consult docs → implement → /code-review
    ├── M: /grill-with-docs → /to-spec → /implement → /code-review
    └── L: … → /to-tickets (local .scratch/) → /implement → /code-review

Git commits         ← `.cursor/rules/always.mdc` (never commit unless the user explicitly asks)
```

Slash skills with `disable-model-invocation` are **not** auto-run. The workflow rule classifies work and **asks the human** to invoke the next `/skill`. The rule is the traffic light; the skills are the workstations.

## Files in `.agents/`

| File | Role |
|---|---|
| `README.md` | This map |
| `issue-tracker.md` | Where specs/tickets live (currently **local** `.scratch/`) |
| `domain.md` | How skills should consume `CONTEXT.md` and ADRs |
| `triage-labels.md` | Mapping for triage role labels |
| `impact-category-interchange.md` | Agent notes pointing at canonical AB docs |

## Module READMEs (code-adjacent)

Package-level notes remain useful and are not replaced by this tree:

- `activity_browser/app/README.md`
- `activity_browser/ui/README.md`
- `activity_browser/bwutils/README.md`
- `activity_browser/mod/README.md`
- `tests/README.md`

## Plugins (AB3 extension system)

Author-facing docs: [`docs/plugins/`](../plugins/index.md) (getting started, API reference, [integration boundaries](../plugins/api-reference.md#integration-boundaries)).

| Area | Path |
|---|---|
| Public facade | `activity_browser/plugins/` (`PluginContext`, loader, version) |
| Plugin loader / main window | `activity_browser/plugins/loader.py`; `activity_browser.app.create_main_window()` after deferred imports |
| Contribution registries | `activity_browser/app/contributions.py` |
| Settings → Plugins UI | `activity_browser/app/pages/settings/plugins.py` |
| Example package (dev/CI) | `plugins/ab-plugin-example/` — `pip install -e ./plugins/ab-plugin-example` |
| ADR | [`docs/adr/0012-plugins-contribution-api.md`](../adr/0012-plugins-contribution-api.md) |
| Local spec / tickets | `.scratch/plugin-system/` (gitignored) |

Plugin tests: `tests/plugins/`. Loader unit tests import `activity_browser.plugins.loader` directly; example tests skip if the package is not installed.

## Switching to GitHub Issues later

Issue tracker is **local by choice** while the workflow is proven. To move to GitHub Issues for collaborative agent tickets, update `issue-tracker.md` (and the `## Agent skills` blurb in `AGENTS.md`) and refresh this README in the same change. Re-running `/setup-matt-pocock-skills` is optional if you prefer to edit the files directly.
