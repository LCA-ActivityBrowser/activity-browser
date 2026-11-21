# Three documentation audiences; AB docs stay practitioner-facing

GitHub Pages publishes only `docs/` (AB docs for AB users / LCA practitioners). Architecture Decision Records live in `adr/`; agent workflow and skill config live in `.agents/` (with root `AGENTS.md` / `CONTEXT.md`). Agents should read `docs/`, check whether behavior changes need practitioner-facing updates, and when they edit `docs/` use edit-then-flag confirmation — never write `docs/` in a programmer or agent voice.

## Status

accepted

## Considered Options

- Keep ADRs and agent notes under `docs/` and Jekyll-`exclude` them — rejected; still mixes audiences in the Pages tree and polluted the public nav when exclude was missing
- Put ADRs under `.agents/` — rejected; `CONTRIBUTING.md` and humans should not dig through agent-config paths for decisions
- Hard write-ban on `docs/` for agents — rejected; behavior changes that users must know belong in AB docs, with explicit user confirmation of those edits

## Consequences

- Public site nav is AB-docs-only; engineering/agent material is repo-local (and GitHub blob links)
- Path references use `adr/` and `.agents/`, not `docs/adr` / `docs/agents`
- `docs/README.md` (site authoring guide) is Jekyll-excluded; it is not practitioner content
