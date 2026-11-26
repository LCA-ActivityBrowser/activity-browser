---
name: pr
description: Open a GitHub PR for Activity Browser — dedicated branch, best-practice body, exactly one changelog label plus optional area labels. User-invoked as /PR.
disable-model-invocation: true
---

# /PR — open a pull request

Open (or update) a PR into **`dev`** with a user-facing title, a solid body, and labels.

Do **not** create a git commit unless the user already asked to commit in this conversation.

## Progress

```
- [ ] 1. Preconditions
- [ ] 2. Dedicated branch
- [ ] 3. Push
- [ ] 4. Title + body
- [ ] 5. Create / update PR
- [ ] 6. Labels
- [ ] 7. Return URL
```

## 1. Preconditions

Run in parallel: `git status`, `git branch -vv`, `git log --oneline -8`, `git diff` / `git diff --stat` (staged + unstaged + against upstream if any).

**Done when:** you know whether the work is committed, which branch you are on, and what the PR should describe.

- If there are **uncommitted** changes that belong in the PR: **stop** and ask the user to commit (or explicitly allow a commit). Do not invent a commit.
- If a PR for this branch already exists: update it (title/body/labels) instead of opening a duplicate; still complete steps 4–7 as needed.

## 2. Dedicated branch

Integration branches: `main`, `dev`, `master`, `AB2_legacy`.

- If **already** on a non-integration branch: keep it.
- If on an integration branch: create and check out a dedicated branch named from the change (`fix/…`, `feature/…`, `change/…`, `docs/…`, `ci/…`). Prefer a short slug from the user request or the dominant diff.

**Done when:** `HEAD` is on a dedicated branch that contains the commits to ship.

## 3. Push

```bash
git push -u origin HEAD
```

**Done when:** the branch is on `origin` and tracks it.

## 4. Title + body

**Title:** one line a **user** can understand in the GitHub Release notes. No issue numbers. No internal jargon.

**Body:** use a HEREDOC with `gh pr create`. Structure:

```markdown
## Summary
- 1–3 bullets: what changed and why

## Checklist
- [x] / [ ] items from `.github/PULL_REQUEST_TEMPLATE.md` that apply
- Link related issues with closing keywords when appropriate (`Fixes #123`)

## Test plan
- Concrete steps a reviewer can run
```

Fill the checklist honestly from the diff (docs/tests/wiki). Prefer merge-commit guidance already in the template comments; target base is **`dev`**.

**Done when:** title and body are drafted from the actual diff (not generic filler).

## 5. Create / update PR

```bash
gh pr create --base dev --title "…" --body "$(cat <<'EOF'
…
EOF
)"
```

If a PR already exists for this branch:

```bash
gh pr edit --title "…" --body "…"
```

**Done when:** `gh pr view --json url,number` succeeds for this branch.

## 6. Labels

Read `.github/release.yml` if unsure of current changelog labels.

**Exactly one** changelog label (required):

| Label | Use when |
|---|---|
| `breaking` | Breaks existing user/API behaviour in an important way |
| `feature` | New user-facing capability |
| `ui` | UI-only / interaction presentation |
| `change` | Small non-feature, non-bug behaviour or code change |
| `bug` | Fixes incorrect behaviour |
| `documentation` | Docs / wiki / comments-as-docs only |
| `ci` | CI, packaging, workflows |
| `dependencies` | Dependency add/remove/pin |

**Optional area labels** (zero or more, if the diff clearly fits):

`graphs and visualisation`, `monte-carlo`, `parameters`, `javascript`, `data imports`, `scenarios`, `results`

Apply with `gh pr edit <n> --add-label "…"`. If a wrong changelog label is already present, remove it so exactly one remains.

**Done when:** the PR has exactly one changelog label, plus any fitting area labels; `gh pr view --json labels` confirms.

## 7. Return URL

Reply with the PR URL and the labels applied (changelog + area).

**Done when:** the user has the link.
