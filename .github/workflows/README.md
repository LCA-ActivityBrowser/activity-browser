# GitHub Actions Workflows

This document describes the GitHub Actions workflows used in the Activity Browser project.

## Overview

The Activity Browser project uses several GitHub Actions workflows to automate testing, deployment, and project management tasks:

1. **Automated Testing** - Runs tests on every push and PR
2. **Canary Installation** - Daily installation checks to catch dependency issues
3. **Beta Deployment** - Publishes beta releases to PyPI and Anaconda
4. **Build Executable** - Builds distributable app binaries
5. **Stable Release** - Creates releases and publishes to Anaconda
6. **Milestone Comments** - Automatically notifies users when issues are resolved in releases
7. **Documentation Deployment** - No workflow, done via GitHub settings
8. **Traffic Archive** - Daily github-repo-stats snapshots and HTML/PDF reports on branch `github-repo-stats`

---

## Branch context

- **`main`**: Legacy branch. Do not use for new development.
- **`major`**: Integration branch for ongoing development and testing.
- **`beta`**: Stable branch for the current Activity Browser; this branch is deployed to PyPI and Conda.

### General developer workflow

```text
feature/short-topic  →  pull request  →  major  →  pull request  →  beta
```

1. Create a short-lived feature branch from **`major`**.
2. Open a pull request into **`major`** when the change is ready (preferred over direct pushes).
3. Merge feature pull requests with **“Create a merge commit”**.
4. When a milestone is stable enough, open a pull request from **`major` into `beta`**.
5. Merge into **`beta`** with **“Create a merge commit”** — not squash and merge.

**Why not squash into `beta`?** Squash merges create new commits that are not ancestors of the commits on
`major`. Later pull requests from `major` to `beta` will then list already-released work again. Regular merge
commits keep the branches linked.

If hotfixes land on **`beta`** first, merge **`beta` back into `major`** so both branches stay aligned.

See [`CONTRIBUTING.md`](../../CONTRIBUTING.md#branching-and-git-workflow) for the full contributor and
maintainer guide (fork workflow, local merges, and release steps).

### CI and deployment

- Automated testing runs on pushes and pull requests to **`major`** and **`beta`**.
- Pushing to **`beta`** triggers beta deployment (see [Beta Deployment](#3-beta-deployment-python-package-deployyml) below).

---

## 1. Automated Testing (`testing.yaml`)

**Trigger:** Push or pull request to the `major` and `beta` branches

**Purpose:** Ensures code quality by running the test suite across multiple operating systems and Python versions.

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

---

## 2. Canary Installation (`install-canary.yaml`)

**Trigger:** Scheduled daily at 7:00 AM UTC (cron: `0 7 * * *`)

**Purpose:** Proactively detects dependency issues by performing fresh installations of Activity Browser from PyPI daily.

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
- Helps catch breaking changes in dependencies before users encounter them
- Artifacts show exact dependency versions that successfully installed

---

## 3. Beta Deployment (`python-package-deploy.yml`)

**Trigger:** Push to `beta` branch or any tag

**Purpose:** Publishes beta versions to PyPI (test and production) and Anaconda Cloud.

### Version Scheme
- Beta version format: `3.0.0bYYYYMMDDHHMM` (UTC timestamp, PEP 440 compatible)

### Steps
1. Checkout with full git history (`fetch-depth: "0"`)
2. Set version number from UTC timestamp
3. Set up Python 3.11
4. Install `build` package
5. Build wheel and source distribution
6. **PyPI Publishing:**
   - Publish to Test PyPI (with `skip-existing: true`)
   - Publish to production PyPI
7. **Conda Publishing:**
   - Set up Conda environment from `.github/conda-envs/build.yml`
   - Build Conda package: `conda build -c conda-forge -c cmutel ./recipe/`
   - Upload to Anaconda Cloud using `CONDA_LCA` secret token

### Permissions
- Requires `id-token: write` for PyPI trusted publishing

---

## 4. Build Executable (`build-executable.yml`)

**Trigger:** Push to `beta` branch or any tag

**Purpose:** Builds application executables using PyInstaller and uploads them as workflow artifacts.

### Matrix Strategy
- **Operating Systems:** Ubuntu (latest), Windows (latest), macOS 15, macOS (latest)

### Steps
1. Checkout code
2. Install system dependencies (Linux only)
3. Set up Python 3.12
4. Install and use `uv`
5. Sync dependencies and install PyInstaller
6. Build executable via `pyinstaller.spec`
7. Upload `dist/*` as artifact (`activity-browser-${os}`)

---

## 5. Stable Release (`release.yaml`)

**Trigger:** Push of any git tag

**Purpose:** Creates GitHub releases with auto-generated changelogs and publishes stable versions to Anaconda.

### Steps
1. Checkout code
2. **Generate Changelog:**
   - Uses `mikepenz/release-changelog-builder-action@v4`
   - Configuration from `.github/changelog-configuration.json`
   - Builds changelog from PRs with labels
3. **Create GitHub Release:**
   - Uses `ncipollo/release-action@v1`
   - Includes generated changelog as release notes
   - Targets `main` branch commit
4. **Build and Upload Conda Package:**
   - Set up Conda environment (Python 3.11)
   - Build with `conda build recipe/`
   - Upload to Anaconda using `CONDA_UPLOAD_TOKEN` secret
5. **Update Wiki:**
   - Runs `.github/scripts/update_wiki.sh` to automatically update documentation

### Notes
- Only runs on tagged commits (version releases)
- Creates public GitHub releases visible to users
- Updates project wiki documentation automatically

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

- Recommended Pages setting: branch `major`, folder `/docs`
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
   git checkout major   # or whatever branch you were on
   ```
3. Merge this workflow to the default branch used for Actions, then run **Actions → Archive GitHub traffic → Run workflow** once.
4. (Optional) Serve the HTML report via GitHub Pages — see [Viewing the report](#viewing-the-report) below.

Data lives only on `github-repo-stats` and does not pollute `major` / `beta`.

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
- `CONDA_LCA` - Anaconda upload token for beta releases
- `CONDA_UPLOAD_TOKEN` - Anaconda upload token for stable releases
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
1. **Beta release:** Push to `beta` branch -> auto-publishes beta version
2. **Executable stand-alone AB versions:** Push to `beta` or tag -> uploads platform artifacts
3. **Stable release:** Create and push a tag -> creates GitHub release and publishes to Anaconda
4. **Close milestone:** Users get release comments automatically

### Monitoring
- Check daily canary runs to catch dependency issues
- Review failed test runs in PR checks before merging
- Monitor PyPI and Anaconda Cloud for successful uploads

