# GitHub Actions Workflows

This document describes the GitHub Actions workflows used in the Activity Browser project.

## Overview

The Activity Browser project uses several GitHub Actions workflows to automate testing, deployment, and project management tasks:

1. **Automated Testing** - Runs tests on every push/PR, plus a daily schedule for dependency-drift detection
2. **Canary Installation** - Daily PyPI install checks (separate from the test suite)
3. **Semver Publish** - Publishes tagged releases to PyPI and Anaconda (`lca`)
4. **Build Executable** - Builds distributable app binaries
5. **GitHub Release** - Creates GitHub Releases (changelog) and updates the wiki
6. **Milestone Comments** - Automatically notifies users when issues are resolved in releases
7. **Documentation Deployment** - No workflow, done via GitHub settings
8. **Traffic Archive** - Daily github-repo-stats snapshots and HTML/PDF reports on branch `github-repo-stats`

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

- Automated testing runs on pushes and pull requests to **`main`** and **`dev`**, and daily on the default-branch tip (`main`) for dependency-drift detection.
- Semver tags (excluding `*-stand-alone`) publish PyPI + `lca` and create a GitHub Release.

---

## 1. Automated Testing (`testing.yaml`)

**Triggers:**
- Push or pull request to the `main` and `dev` branches
- Scheduled daily at **08:00 UTC** (`cron: 0 8 * * *`) — dependency-drift canary on the **default branch** tip (`main`)
- `workflow_dispatch` — manual run from the Actions UI (branch picker selects which ref is tested)

**Purpose:** Ensures code quality by running the test suite across multiple operating systems and Python versions. The daily schedule catches quiet-day **dependency drift**: tip of `main` plus a fresh PyPI resolve of open version ranges still passes pytest. This is separate from the PyPI install canary (below); it does not build executables.

### Matrix Strategy
- **Operating Systems:** Ubuntu (latest), Windows (latest), macOS 15, macOS (latest)
- **Python Versions:** 3.11, 3.12, 3.13, 3.14
- **Total combinations:** 16 test runs per trigger, plus one Ubuntu / Python 3.12 job pinned to pandas 2.3.x (`tests-pandas2`) so pandas 2.3 and 3 both stay green.

### Steps
1. Checkout code
2. Set up Python for the specified version
3. Install Qt libraries (Linux only)
4. Update pip, setuptools, and wheel
5. Install package with testing dependencies: `pip install .[testing]`
6. Run pytest with minimal output: `pytest -s --no-header --no-summary -q`

### Environment
- Sets `QT_QPA_PLATFORM=offscreen` for headless GUI testing
- Uses `fail-fast: false` to run all combinations even if some fail

### Schedule vs manual dispatch
- **Schedule** always uses the workflow file on the default branch and checks out that tip (`main`).
- **`workflow_dispatch`** can target any branch you select in the Actions UI (useful for ad-hoc runs; not limited to `main`).

---

## 2. Canary Installation (`install-canary.yaml`)

**Trigger:** Scheduled daily at **07:00 UTC** (cron: `0 7 * * *`) — one hour before the Automated Testing schedule

**Purpose:** Proactively detects dependency issues by performing fresh installations of Activity Browser from **PyPI** daily (install-only; does not run the test suite).

### Matrix Strategy
- **Operating Systems:** Ubuntu (latest), Windows (latest), macOS 15, macOS (latest)
- **Python Versions:** 3.11, 3.12, 3.13, 3.14
- **Timeout:** 12 minutes per job

### Steps
1. Checkout code
2. Set up Python
3. Install activity-browser from PyPI (not from source)
4. Generate environment info with `pip freeze`
5. Upload frozen requirements as artifact for each OS/Python combination

### Notes
- Uses `bash -e {0}` shell to exit on error
- Helps catch breaking changes that prevent the published package from installing
- Artifacts show exact dependency versions that successfully installed
- Pair with the daily Automated Testing schedule for “installs” vs “source + fresh deps still pass tests”

---

## 3. Semver Publish (`python-package-deploy.yml`)

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

**Trigger (on `dev` / feature branches):**
- `pull_request` → `dev`
- `push` → `dev`
- `workflow_dispatch` (optional manual rebuild)

**Purpose:** Builds stand-alone Activity Browser packages with PyInstaller (onedir) plus
platform installers; uploads workflow artifacts. Version stamp defaults to
`{latest PyPI activity-browser}-stand-alone`. See [`packaging/README.md`](../../packaging/README.md).

**Default branch (`main`):** keep a **minimal stub** with the same workflow `name` and
`on: workflow_dispatch` only (PR #1791 pattern). That unlocks **Run workflow** in the
Actions UI; choose **`dev`** in the branch dropdown so the full job matrix runs.

### Matrix Strategy
- **Windows** → Inno Setup installer
- **Linux** → AppImage
- **macOS** (Apple Silicon) → unsigned DMG

After packaging, each OS job smoke-launches the stand-alone under offscreen Qt
(`packaging/smoke-standalone.sh`) and fails if the process dies during startup.

### Publishing
Use **Release Stand-alone** (below).

---

## 4b. Release Stand-alone (`release-standalone.yml`)

**Trigger:** `workflow_dispatch` only (full file on `dev`; stub on `main` for the UI).

**Purpose:** Downloads artifacts from a Build Executable run and creates an immutable
GitHub Release tagged `{AB}-stand-alone` with versioned installer assets. Docs and the
in-app updater use the Releases page / API filter on `*-stand-alone` tags (ADR-0015).

### Dispatch inputs
- `build_run_id` — optional; empty = latest successful Build Executable on `source_branch`
- `source_branch` — default `dev`
- `ab_version` — optional; empty = PyPI latest

---

## 5. GitHub Release (`release.yaml`)

**Trigger:** Push of a git tag (job skipped when the tag ends in `-stand-alone`)

**Purpose:** Creates a GitHub Release with an auto-generated PR-label changelog and updates the wiki.
PyPI / `lca` uploads are handled by [Semver Publish](#3-semver-publish-python-package-deployyml).

### Steps
1. Checkout code
2. **Generate Changelog** from PR labels (`.github/changelog-configuration.json`)
3. **Create GitHub Release** on the tagged commit (`commit: main`)
4. **Update Wiki** via `.github/scripts/update_wiki.sh`

### Notes
- After the Release is created, maintainers **Edit release** to prepend a curated preamble (CONTRIBUTING)
- `*-stand-alone` tags are handled only by Release Stand-alone

---

## 6. Milestone Comments (`comment-milestoned-issues.yaml`)

**Trigger:** When a milestone is closed

**Purpose:** Automatically notifies users on closed issues when their issue has been implemented in a release.

### Steps
1. Uses `actions/github-script@v5` to run JavaScript automation
2. Gets milestone number and title from the event
3. Lists all issues associated with the milestone
4. For each closed issue (not PRs):
   - Posts a comment with:
     - Link to the new release
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

## 7. Documentation deployment

Documentation is currently deployed by **GitHub Pages "Deploy from a branch"** (not by a repository workflow file).

- Recommended Pages setting: branch `main`, folder `/docs`
- Expected Actions entry for docs: GitHub-managed `pages build and deployment`

---

## 8. Traffic Archive (`traffic-archive.yaml`)

**Trigger:** Daily at 23:00 UTC (`cron: 0 23 * * *`), or manual `workflow_dispatch`

**Purpose:** GitHub only retains repository traffic insights for about 14 days. This workflow uses [`jgehrcke/github-repo-stats`](https://github.com/marketplace/actions/github-repo-stats) to snapshot traffic (views/clones, referrers, paths), plus stars/forks evolution, then commits data and HTML/PDF reports to the `github-repo-stats` branch.

### Steps
1. Skip with a notice if `GHRS_GITHUB_API_TOKEN` is not configured
2. Run github-repo-stats (reads Traffic API, aggregates history, commits to `databranch`)

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
- `GHRS_GITHUB_API_TOKEN` - PAT (`repo` scope) for Traffic API + pushing reports to `github-repo-stats` (see [Traffic Archive](#8-traffic-archive-traffic-archiveyaml))

### Configuration Files
- `.github/conda-envs/build.yml` - Conda environment for building packages
- `.github/changelog-configuration.json` - Changelog generation configuration
- `.github/scripts/update_wiki.sh` - Wiki update script
- `recipe/meta.yaml` - Conda package recipe
- `pyproject.toml` - Python package configuration

---

## Development Notes

### Running Tests Locally
To run the same tests that CI runs:
```bash
pip install .[testing]
pytest -s --no-header --no-summary -q
```

### Testing Matrix Changes
When modifying the test matrix (OS or Python versions):
- Update both `testing.yaml` and `install-canary.yaml` to keep them in sync
- Consider the maintenance burden of additional combinations
- Current support: Python 3.11-3.14, Ubuntu/Windows/macOS

### Release Process
1. **Stable release:** Push annotated semver tag on `main` → GitHub Release + PyPI + `lca` (then Edit release for curated preamble; see CONTRIBUTING)
2. **Stand-alone:** Build Executable on `dev` → Release Stand-alone → `{ver}-stand-alone` tag
3. **Close milestone:** Users get release comments automatically
4. **conda-forge:** remains AB2 until forge deps allow AB3; defer bot upgrades (ADR-0017)

### Monitoring
- Check daily **canary installation** (07:00 UTC) and scheduled **Automated Testing** (08:00 UTC) for dependency issues; rely on GitHub workflow-failure notifications
- Review failed test runs in PR checks before merging
- Monitor PyPI and Anaconda Cloud for successful uploads

