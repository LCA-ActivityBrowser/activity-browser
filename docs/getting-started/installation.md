---
title: Installation
parent: Getting started
nav_order: 1
---

# Installing the Activity Browser
{: .fs-9 }

Choose one of three paths: [stand-alone](#stand-alone-installers) (easiest; no Python), [PyPI](#installing-from-pypi), or [Anaconda](#installing-from-anaconda).
{: .fs-6 .fw-300 }

## Stand-alone installers
**No Python required.**

[Download installers](https://github.com/LCA-ActivityBrowser/activity-browser/releases){: .btn .btn-primary .fs-5 .mb-2 }

Pick a tag ending in `-stand-alone`, then the file for your OS (Windows `.exe`, macOS Apple Silicon `.dmg`, Linux `.AppImage`). 
Builds are **unsigned**, so browser/SmartScreen warnings on Windows and Gatekeeper on macOS are expected.

- **Windows:** run the installer; Microsoft blocks unknown apps with a "Windows protected your PC" prompt; you can bypass this by clicking More info and then Run anyway
- **macOS (ARM):** open the DMG; drag to Applications; After attempting to launch the app and dismissing the Gatekeeper warning, go to System Settings > Privacy & Security, scroll down, and click Open Anyway
- **macOS (Intel):** not supported yet
- **Linux:** mark the file as executable via `chmod +x` filename or by right-clicking the file, opening Properties > Permissions, and checking Allow executing file as program

## Installing from PyPI

Install with `pip` into a dedicated [virtual environment](https://realpython.com/python-virtual-environments-a-primer/).

### Checking Python

Supported versions: **3.11, 3.12, 3.13, and 3.14**.

```
python --version
```

If that fails, or the version is outside the range above, install a supported Python from [python.org](https://www.python.org/downloads/) (on Windows, enable **Add python.exe to PATH**).

### Setting up a virtual environment

Create a directory for virtual environments (for example `C:/Users/me/virtualenvs/` or `~/virtualenvs/`), then:

```
python -m venv C:/Users/me/virtualenvs/ab-beta
```

To force a specific supported version on Windows (here 3.12):

```
py -3.12 -m venv C:/Users/me/virtualenvs/ab-beta
```

Activate it:

```
# Windows:
C:\Users\me\virtualenvs\ab-beta\Scripts\activate

# macOS / Linux:
source ~/virtualenvs/ab-beta/bin/activate
```

### Installing the Activity Browser

With the virtual environment activated:

```
pip install activity-browser
```

### Launching the Activity Browser

```
activity-browser
```

## Installing from Anaconda

Install with conda into a dedicated environment.

### Checking Conda

Supported Python versions: **3.11, 3.12, 3.13, and 3.14** (Conda installs a compatible Python into the new environment).

```
conda --version
```

If that fails, install [Miniconda](https://docs.anaconda.com/miniconda/) ([install guide](https://docs.anaconda.com/miniconda/install/)), reopen your terminal, then keep Conda up to date:

```
conda update conda
```

### Installing the Activity Browser

Create and populate the environment:

```
conda create -n ab_beta -c conda-forge -c lca -c cmutel lca::activity-browser
```

To pin a specific supported Python (here 3.12):

```
conda create -n ab_beta -c conda-forge -c lca -c cmutel lca::activity-browser python=3.12
```



Solving can take a while. When it finishes, activate the environment:

```
conda activate ab_beta
```

### Launching the Activity Browser

```
activity-browser
```
