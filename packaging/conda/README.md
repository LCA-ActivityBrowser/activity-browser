# packaging/conda

Conda-build recipe for Activity Browser (in-repo **conda** install-channel builds).

## Overview

`meta.yaml` defines how to build the conda package from this repository (used by deploy CI for the `lca` channel). The public **conda-forge** recipe lives in a separate feedstock: https://github.com/conda-forge/activity-browser-feedstock

## Key file

- **`meta.yaml`** — package metadata and build instructions

`source.path` is `../..` so conda-build resolves the repository root from this directory.

## Building locally

Prerequisites: `conda-build` installed.

```bash
conda build packaging/conda/
```

Optional Python variants:

```bash
conda build packaging/conda/ --python 3.11
conda build packaging/conda/ --python 3.12
conda build packaging/conda/ --python 3.13
```

## Dependencies

Keep dependencies in sync across:

- `packaging/conda/meta.yaml` (conda recipe)
- `pyproject.toml` (pip / setuptools)
- `setup.py` (legacy shim still invoked by this recipe’s build script)

## Installation (users)

Until AB3 is on conda-forge, install from the `lca` channel (pin required so conda does not pick AB2 from conda-forge):

```bash
conda create -n ab -c conda-forge -c lca -c cmutel lca::activity-browser
```

## Resources

- [conda-build documentation](https://docs.conda.io/projects/conda-build/)
- [conda-forge documentation](https://conda-forge.org/docs/)
- [Activity Browser feedstock](https://github.com/conda-forge/activity-browser-feedstock)
- Parent map: [`packaging/README.md`](../README.md)
