# recipe

Conda build recipe for Activity Browser.

## Overview

This directory contains the conda-build recipe for packaging and distributing Activity Browser via conda-forge. The recipe defines how to build the conda package from source.

## Key File

- **`meta.yaml`** - Conda package metadata and build instructions

## meta.yaml Structure

The `meta.yaml` file contains several sections:

### Package Section
Defines package name and version:
```yaml
package:
  name: activity-browser
  version: {{ VERSION }}
```

### Source Section
Specifies where to get the source code:
```yaml
source:
  path: ..  # Local path for development
  # Or from GitHub release:
  # url: https://github.com/LCA-ActivityBrowser/activity-browser/archive/{{ version }}.tar.gz
```

### Build Section
Build configuration:
```yaml
build:
  number: 0
  noarch: python  # Pure Python package
  entry_points:
    - activity-browser = activity_browser:run_activity_browser
```

### Requirements Section
Dependencies for build and runtime:

```yaml
requirements:
  host:
    - python >=3.9
    - pip
    - setuptools
  run:
    - python >=3.9
    - brightway2 >=2.4
    - pyside6 >=6.0
    - qtpy >=2.0
    # ... more dependencies
```

### About Section
Package metadata:
```yaml
about:
  home: https://github.com/LCA-ActivityBrowser/activity-browser
  license: LGPL-3.0
  summary: GUI for Brightway2 LCA framework
  description: Activity Browser is a GUI for the Brightway2 LCA framework
  doc_url: https://lca-activitybrowser.github.io/activity-browser/
```

## Building Locally

### Prerequisites
- conda-build installed: `conda install conda-build`
- Conda environment set up

### Build Command
```bash
conda build recipe/
```

This will:
1. Create a clean build environment
2. Install dependencies
3. Build the package from source
4. Run tests
5. Create a conda package (.tar.bz2)

### Build Variants
For different Python versions:
```bash
conda build recipe/ --python 3.9
conda build recipe/ --python 3.10
conda build recipe/ --python 3.11
```

## conda-forge

Activity Browser is distributed via conda-forge, the community-led conda package repository.

### conda-forge Repository
The conda-forge recipe is maintained in a separate repository:
https://github.com/conda-forge/activity-browser-feedstock

### Update Process
When a new version is released:
1. conda-forge bot detects new GitHub release
2. Opens PR to update version and SHA256
3. Maintainers review and merge
4. Package is built for all platforms
5. Published to conda-forge channel

### Maintainers
conda-forge package maintainers can:
- Update the recipe
- Adjust dependencies
- Fix build issues
- Release new versions

## Installation

Users install from conda-forge:
```bash
conda install -c conda-forge activity-browser
```

Or with mamba (faster):
```bash
mamba install -c conda-forge activity-browser
```

## Dependencies

Keep dependencies in sync:
- `meta.yaml` (conda recipe)
- `pyproject.toml` (pip/setuptools)
- `setup.py` (legacy setup)

Ensure all three specify the same dependencies and versions.

## Platform Support

Activity Browser supports:
- **Linux** - x86_64, aarch64
- **macOS** - x86_64, arm64 (Apple Silicon)
- **Windows** - x86_64

The recipe should specify `noarch: python` if the package is pure Python, or include platform-specific builds if needed.

## Troubleshooting

### Build Failures
- Check dependency versions
- Verify source path/URL
- Review build logs
- Test in clean environment

### Import Errors
- Missing dependencies in run requirements
- Incorrect entry points
- Module import issues

### Test Failures
- Tests timing out
- Missing test dependencies
- Platform-specific issues

## Development Workflow

1. **Local Development**
   - Edit source code
   - Test locally with `python -m activity_browser`

2. **Update Recipe**
   - Modify `meta.yaml` if dependencies changed
   - Update version number

3. **Build and Test**
   - Run `conda build recipe/`
   - Install and test locally

4. **Release**
   - Tag release on GitHub
   - conda-forge bot updates feedstock
   - Package published automatically

## Resources

- [conda-build documentation](https://docs.conda.io/projects/conda-build/)
- [conda-forge documentation](https://conda-forge.org/docs/)
- [Activity Browser feedstock](https://github.com/conda-forge/activity-browser-feedstock)
