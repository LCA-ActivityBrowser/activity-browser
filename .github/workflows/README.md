# GitHub Actions Workflows

This document describes every workflow under `.github/workflows/` (plus docs Pages, which has no repo workflow file).

## Inventory

| File | Actions UI name | Role |
|---|---|---|
| `testing.yaml` | Automated Testing | Pytest on PR + daily source dependency-drift |
| `install-canary.yaml` | canary installation | Daily published **pip** + **conda** install checks |
| `python-package-deploy.yml` | Publish release to PyPI and Anaconda | Semver tag → PyPI + `lca` |
| `build-executable.yml` | Build Executable | Stand-alone installers (artifacts) |
| `release-standalone.yml` | Release Stand-alone | Promote build artifacts → `{ver}-stand-alone` GitHub Release |
| `release.yaml` | stable release | Semver tag → GitHub Release + wiki |
| `comment-milestoned-issues.yaml` | comment when milestone is closed | Comment on issues when a milestone closes |
| `traffic-archive.yaml` | Archive GitHub traffic | Daily traffic/stats snapshots on `github-repo-stats` |
| *(none)* | pages build and deployment | Docs via GitHub Pages “Deploy from a branch” |

---

## Branch context

- **`main`**: AB3 stable (default). Public versions are cut with semver tags.
- **`dev`**: AB3 integration for ongoing development and testing.
- **`AB2_legacy`**: AB2 line (critical fixes only). See [ADR-0017](../../adr/0017-ab3-release-channels-and-branches.md).

### General developer workflow

```text
feature/short-topic  →  pull request  →  dev  →  pull request  →  main
main  →  annotated tag x.y.z  →  GitHub Release + PyPI + lca
```

1. Create a short-lived feature branch from **`dev`**.
2. Open a pull request into **`dev`** when the change is ready (preferred over direct pushes).
3. Merge feature pull requests with **“Create a merge commit”**.
4. When a milestone is ready for the stable line, open a pull request from **`dev` into `main`**.
5. Merge into **`main`** with **“Create a merge commit”** — not squash and merge. Merges do **not** publish packages.

**Why not squash into `main`?** Squash merges break shared history between `dev` and `main`.

If hotfixes land on **`main`** first, merge **`main` back into `dev`** so both branches stay aligned.

See [`CONTRIBUTING.md`](../../CONTRIBUTING.md#branching-and-git-workflow) for the full contributor and
maintainer guide (fork workflow, local merges, and release steps).

### CI and deployment

- Automated testing runs on pull requests targeting **`main`** or **`dev`** (including each new commit on the PR), and daily on the default-branch tip (`main`) for dependency-drift detection. **`schedule` only fires from the default-branch workflow file** — the cron in `testing.yaml` must be on `main` to run.
- Semver tags (excluding `*-stand-alone`) publish PyPI + `lca` and create a GitHub Release.
- Stand-alone builds run automatically on PRs into **`main`**, or manually via **Run workflow** (prefer branch **`dev`**); they use `*-stand-alone` tags and never go through Semver Publish / stable release.

---

## 1. Automated Testing (`testing.yaml`)

**Actions name:** Automated Testing

**Triggers:**
- Pull request targeting `main` or `dev` (re-runs when the PR branch is updated with new commits)
- Scheduled daily at **08:00 UTC** (`cron: 0 8 * * *`) — dependency-drift check on the **default branch** tip (`main`)
- `workflow_dispatch` — manual run from the Actions UI (branch picker selects which ref is tested)

**Purpose:** Ensures code quality by running the test suite across multiple operating systems and Python versions. The daily schedule catches quiet-day **dependency drift**: tip of `main` plus a fresh PyPI resolve of open version ranges still passes pytest. This is separate from the pip/conda install canary (below); it does not build executables.

### Matrix Strategy
- **Operating Systems:** Ubuntu (latest), Windows (latest), macOS 15, macOS (latest)
- **Python Versions:** 3.11, 3.12, 3.13, 3.14
- **Total combinations:** 16 test runs per trigger, plus one Ubuntu / Python 3.12 job pinned to pandas 2.3.x (`tests-pandas2`) so pandas 2.3 and 3 both stay green.

### Steps
1. Checkout code (`actions/checkout@v4`)
2. Set up Python for the specified version (`actions/setup-python@v5`)
3. Install Qt libraries on Linux (`tlambert03/setup-qt-libs@v1`)
4. Upgrade pip, setuptools, and wheel
5. Install package with testing dependencies: `pip install .[testing]`
6. Run pytest: `pytest -q --no-cov -o log_cli=false --durations=25`

### Environment
- Sets `QT_QPA_PLATFORM=offscreen` for headless GUI testing
- Uses `fail-fast: false` to run all combinations even if some fail

### Schedule vs manual dispatch
- **Schedule** always uses the workflow file on the default branch and checks out that tip (`main`).
- **`workflow_dispatch`** can target any branch you select in the Actions UI (useful for ad-hoc runs; not limited to `main`).

---

## 2. Canary Installation (`install-canary.yaml`)

**Actions name:** canary installation

**Triggers:**
- Scheduled daily at **07:00 UTC** (`cron: 0 7 * * *`) — one hour before the Automated Testing schedule
- `workflow_dispatch` — manual run from the Actions UI

**Purpose:** Checks whether the **published** packages for the **pip** and **conda** install channels still install today (install-only; does not run the test suite; does not install from the git tree). This is separate from scheduled Automated Testing, which checks out `main` and runs `pip install .[testing]` + pytest.

### Matrix Strategy (sparse 4+4 per installer)
- **Ubuntu (latest):** Python 3.11, 3.12, 3.13, 3.14
- **Windows (latest):** Python 3.11, 3.14
- **macOS (latest, ARM):** Python 3.11, 3.14
- **Timeouts:** 12 minutes (pip), 30 minutes (conda)
- **Total:** 8 pip jobs + 8 conda jobs

The canary matrix is intentionally **not** identical to `testing.yaml` (full OS × Python). Sparse corners keep most install/drift signal at lower cost.

### Pip job (`canary-installs-pip`)
1. Set up Python for the matrix version (no checkout)
2. `pip install activity-browser` from PyPI
3. `pip freeze` → artifact `requirements-<os>-<python>`

### Conda job (`canary-installs-conda`)
1. Set up **micromamba** (CI solver; user docs still show `conda create …`)
2. Create env with channels `conda-forge`, `lca`, `cmutel`, flexible priority, `lca::activity-browser`, and pinned `python=` matching the matrix
3. `micromamba list --export` → artifact `conda-env-<os>-<python>`

### Notes
- No `actions/checkout` — the run SHA identifies the workflow file, not the installed AB source
- Artifacts use `actions/upload-artifact@v4`
- Pair with the daily Automated Testing schedule for “published install channels” vs “source tip + fresh deps still pass tests”

---

## 3. Semver Publish (`python-package-deploy.yml`)

**Actions name:** Publish release to PyPI and Anaconda

**Trigger:** Push of a git tag (job skipped when the tag ends in `-stand-alone`)

**Purpose:** Publishes the tagged version to PyPI (test and production) and Anaconda Cloud (`lca`).

### Version Scheme
- `VERSION` = tag name (e.g. `3.0.0`)

### Steps
1. Checkout with full git history (`fetch-depth: "0"`)
2. Set `VERSION` from the tag
3. Set up Python 3.11
4. Install `build` package
5. Build wheel and source distribution
6. **PyPI Publishing:**
   - Publish to Test PyPI (with `skip-existing: true`)
   - Publish to production PyPI
7. **Conda Publishing:**
   - Set up Conda environment from `.github/conda-envs/build.yml`
   - Build Conda package: `conda build -c conda-forge -c cmutel -c lca ./recipe/`
   - Upload to Anaconda Cloud using `CONDA_LCA`

### Permissions
- Requires `id-token: write` for PyPI trusted publishing

---

## 4. Build Executable (`build-executable.yml`)

**Actions name:** Build Executable

**Triggers:**
- `pull_request` → `main`
- `workflow_dispatch` with optional input `ab_version` (empty = latest `activity-browser` on PyPI)

**Purpose:** Builds stand-alone Activity Browser packages with PyInstaller (onedir) plus
platform installers; uploads workflow artifacts. Version stamp defaults to
`{latest PyPI activity-browser}-stand-alone`. See [`packaging/README.md`](../../packaging/README.md)
and ADR-0016 (Mac micromamba / umfpack).

**Branch note:** Auto-runs on PRs into **`main`**. For ad-hoc / stand-alone cuts, prefer **Run workflow**
with branch **`dev`**. Merges do not publish a stand-alone release.

### Matrix Strategy
- **Windows** (`windows-latest`) → Inno Setup installer (`windows-x64`)
- **Linux** (`ubuntu-latest`) → AppImage (`linux-x86_64`)
- **macOS** (`macos-latest`, Apple Silicon) → unsigned DMG (`macos-arm64`)

Win/Linux freeze via **uv**; macOS freeze via **micromamba**. After packaging, each OS job
smoke-launches the stand-alone under offscreen Qt (`packaging/smoke-standalone.sh`) and fails
if the process dies during startup. Artifacts use `actions/upload-artifact@v4`.

### Publishing
Use **Release Stand-alone** (below).

---

## 5. Release Stand-alone (`release-standalone.yml`)

**Actions name:** Release Stand-alone

**Trigger:** `workflow_dispatch` only

**Purpose:** Downloads artifacts from a Build Executable run and creates an immutable
GitHub Release tagged `{AB}-stand-alone` with versioned installer assets. Docs and the
in-app updater use the Releases page / API filter on `*-stand-alone` tags (ADR-0015).

Prefer **Run workflow** with branch **`dev`** so GitHub uses the full workflow file.

### Dispatch inputs
- `build_run_id` — optional; empty = latest successful Build Executable on `source_branch`
- `source_branch` — default `dev` (required input)
- `ab_version` — optional; empty = PyPI latest

### Permissions
- `contents: write`, `actions: read`

---

## 6. GitHub Release / stable release (`release.yaml`)

**Actions name:** stable release

**Trigger:** Push of a git tag (job skipped when the tag ends in `-stand-alone`)

**Purpose:** Creates a GitHub Release with an auto-generated PR-label changelog and updates the wiki.
PyPI / `lca` uploads are handled by [Semver Publish](#3-semver-publish-python-package-deployyml).

### Steps
1. Checkout code (`actions/checkout@v4`)
2. **Generate Changelog** from PR labels (`mikepenz/release-changelog-builder-action@v4`, `.github/changelog-configuration.json`)
3. **Create GitHub Release** on the tagged commit (`ncipollo/release-action@v1`, `commit: main`)
4. **Update Wiki** via `.github/scripts/update_wiki.sh`

### Notes
- After the Release is created, maintainers **Edit release** to prepend a curated preamble (CONTRIBUTING)
- `*-stand-alone` tags are handled only by Release Stand-alone

---

## 7. Milestone Comments (`comment-milestoned-issues.yaml`)

**Actions name:** comment when milestone is closed

**Trigger:** When a milestone is closed (`milestone` types: `closed`)

**Purpose:** Automatically notifies users on closed issues when their issue has been implemented in a release.

### Steps
1. Uses `actions/github-script@v5` to run JavaScript automation
2. Gets milestone number and title from the event
3. Lists all issues associated with the milestone
4. For each closed issue (not PRs):
   - Posts a comment with:
     - Link to the new release (`releases/tag/{milestone_title}`)
     - Instructions to update Activity Browser
     - Link to subscribe to the updates mailing list
     - Bot disclaimer

### Comment Template
The bot posts a formatted note:
- Informs that the issue is implemented in version X
- Provides update instructions
- Offers subscription to updates mailing list (brightway.groups.io)
- Includes bot identification

---

## 8. Documentation deployment

Documentation is currently deployed by **GitHub Pages "Deploy from a branch"** (not by a repository workflow file).

- Recommended Pages setting: branch `main`, folder `/docs`
- Expected Actions entry for docs: GitHub-managed `pages build and deployment`

---

## 9. Traffic Archive (`traffic-archive.yaml`)

**Actions name:** Archive GitHub traffic

**Trigger:** Daily at 23:00 UTC (`cron: 0 23 * * *`), or manual `workflow_dispatch`

**Purpose:** GitHub only retains repository traffic insights for about 14 days. This workflow uses [`jgehrcke/github-repo-stats`](https://github.com/marketplace/actions/github-repo-stats) (`v1.4.2`) to snapshot traffic (views/clones, referrers, paths), plus stars/forks evolution, then commits data and HTML/PDF reports to the `github-repo-stats` branch.

### Steps
1. Skip with a notice if `GHRS_GITHUB_API_TOKEN` is not configured
2. Run github-repo-stats (reads Traffic API, aggregates history, commits to `databranch: github-repo-stats`)

### One-time setup
1. Create a classic PAT with **`repo`** scope (needed for Traffic API + pushing to the data branch). Store it as repository secret `GHRS_GITHUB_API_TOKEN`.
2. Create an empty orphan data branch (recommended by upstream):
   ```bash
   git checkout --orphan github-repo-stats
   git rm -rf .
   git commit --allow-empty -m "Initialize github-repo-stats data branch"
   git push -u origin github-repo-stats
   git checkout main   # or whatever branch you were on
   ```
3. Merge this workflow to the default branch used for Actions, then run **Actions → Archive GitHub traffic → Run workflow** once.
4. (Optional) Serve the HTML report via GitHub Pages — see [Viewing the report](#viewing-the-report) below.

Data lives only on `github-repo-stats` and does not pollute `main` / `dev`.

### Viewing the report

After at least one successful workflow run, open the data branch:

- **Browse data:** [branch `github-repo-stats`](https://github.com/LCA-ActivityBrowser/activity-browser/tree/github-repo-stats)
- **Latest HTML report:** [`…/LCA-ActivityBrowser/activity-browser/latest-report/report.html`](https://github.com/LCA-ActivityBrowser/activity-browser/blob/github-repo-stats/LCA-ActivityBrowser/activity-browser/latest-report/report.html)
- **Latest PDF report:** [`…/latest-report/report.pdf`](https://github.com/LCA-ActivityBrowser/activity-browser/blob/github-repo-stats/LCA-ActivityBrowser/activity-browser/latest-report/report.pdf) (use **Download** / raw if the blob view is awkward)

The HTML report is meant for a browser (charts via Altair/Vega). GitHub’s blob preview is a weak substitute; for a proper dashboard:

1. Repo **Settings → Pages** → source **Deploy from a branch** → branch **`github-repo-stats`** / root (or a docs-compatible layout if you prefer).
2. After Pages is live, set `ghpagesprefix` in `traffic-archive.yaml` to the site URL **without** a trailing slash, e.g. `https://LCA-ActivityBrowser.github.io/activity-browser`, then re-run the workflow so report links resolve correctly.
3. Open  
   `https://LCA-ActivityBrowser.github.io/activity-browser/LCA-ActivityBrowser/activity-browser/latest-report/report.html`  
   (exact host/path depends on your Pages setup).

The first report is sparse; charts improve as daily snapshots accumulate.

---

## Workflow Dependencies

### Secrets Required
- `GITHUB_TOKEN` - Automatically provided by GitHub Actions
- `CONDA_LCA` - Anaconda upload token for AB3 releases (`lca` channel)
- `GHRS_GITHUB_API_TOKEN` - PAT (`repo` scope) for Traffic API + pushing reports to `github-repo-stats` (see [Traffic Archive](#9-traffic-archive-traffic-archiveyaml))

### Configuration Files
- `.github/conda-envs/build.yml` - Conda environment for building packages
- `.github/changelog-configuration.json` - Changelog generation configuration
- `.github/scripts/update_wiki.sh` - Wiki update script
- `recipe/meta.yaml` - Conda package recipe
- `pyproject.toml` - Python package configuration
- `packaging/` - Stand-alone build scripts and smoke test

---

## Development Notes

### Running Tests Locally
To run the same tests that CI runs:
```bash
pip install .[testing]
pytest -q --no-cov -o log_cli=false --durations=25
```

### Testing Matrix Changes
When modifying OS or Python support:
- Update `testing.yaml` for the full pytest matrix
- Update `install-canary.yaml` only if the supported install-channel set changes; its sparse 4+4 matrix need not match testing cell-for-cell
- Current support: Python 3.11-3.14, Ubuntu/Windows/macOS

### Release Process
1. **Stable release:** Push annotated semver tag on `main` → GitHub Release + PyPI + `lca` (then Edit release for curated preamble; see CONTRIBUTING)
2. **Stand-alone:** Build Executable (PR into `main`, or manual from `dev`) → Release Stand-alone → `{ver}-stand-alone` tag
3. **Close milestone:** Users get release comments automatically
4. **conda-forge:** remains AB2 until forge deps allow AB3; defer bot upgrades (ADR-0017)

### Monitoring
- Check daily **canary installation** (07:00 UTC) and scheduled **Automated Testing** (08:00 UTC) for dependency issues; rely on GitHub workflow-failure notifications
- Remember: schedules only run from the default-branch (`main`) copy of the workflow file
- Review failed test runs in PR checks before merging
- Monitor PyPI and Anaconda Cloud for successful uploads
