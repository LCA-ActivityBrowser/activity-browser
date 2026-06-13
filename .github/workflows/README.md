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

---

## Branch context

- **`main`**: Legacy branch.
- **`beta`**: Stable branch for the current Activity Browser; this branch is deployed to PyPI and Conda.
- **`major`**: Main branch for ongoing new developments. From time to time, `major` is merged into `beta` for major updates once they are stable enough.

### General developer workflow

- Develop fixes/features in dedicated branches.
- Merge these branches into **`major`** via pull requests (preferred).
- Direct pushes to **`major`** are allowed, but PRs are recommended.
- Automated testing runs on both **`major`** (main development/testing line) and **`beta`** (stability guardrail).

---

## 1. Automated Testing (`testing.yaml`)

**Trigger:** Push or pull request to the `major` and `beta` branches

**Purpose:** Ensures code quality by running the test suite across multiple operating systems and Python versions.

### Matrix Strategy
- **Operating Systems:** Ubuntu (latest), Windows (latest), macOS 15, macOS (latest)
- **Python Versions:** 3.10, 3.11, 3.12
- **Total combinations:** 12 test runs per trigger

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
- **Python Versions:** 3.10, 3.11, 3.12
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


## Workflow Dependencies

### Secrets Required
- `GITHUB_TOKEN` - Automatically provided by GitHub Actions
- `CONDA_LCA` - Anaconda upload token for beta releases
- `CONDA_UPLOAD_TOKEN` - Anaconda upload token for stable releases

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
- Current support: Python 3.10-3.12, Ubuntu/Windows/macOS

### Release Process
1. **Beta release:** Push to `beta` branch -> auto-publishes beta version
2. **Executable stand-alone AB versions:** Push to `beta` or tag -> uploads platform artifacts
3. **Stable release:** Create and push a tag -> creates GitHub release and publishes to Anaconda
4. **Close milestone:** Users get release comments automatically

### Monitoring
- Check daily canary runs to catch dependency issues
- Review failed test runs in PR checks before merging
- Monitor PyPI and Anaconda Cloud for successful uploads

