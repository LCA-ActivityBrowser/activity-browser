---
title: Installation
parent: Getting started
nav_order: 1
---

# Installing the Activity Browser
{: .fs-9 }

The Activity Browser 3 Beta is available on [PyPI](#installing-from-pypi) (recommended for most users) and [Anaconda](#installing-from-anaconda). Stand-alone installers (no Python install required) are published on [GitHub Releases](#stand-alone-installers) when maintainers promote a CI build.
{: .fs-6 .fw-300 }

### Supported Python versions
3.11, 3.12, 3.13, and 3.14 (PyPI / Anaconda). Stand-alone builds bundle their own Python runtime.


### New to Python?

The Activity Browser runs on Python.
If you have never installed or used Python before, start by installing a supported version from [python.org](https://www.python.org/downloads/).
Their [beginner's guide](https://wiki.python.org/moin/BeginnersGuide) walks through the basics.
If you prefer the Anaconda route below, install [Miniconda](https://docs.anaconda.com/miniconda/) instead and follow the [official installation instructions](https://docs.anaconda.com/miniconda/install/).

### Check your Python version

Make sure you have Python available by entering the following command into your terminal or command prompt.

```
python --version
```
If you get an error, install a supported Python from [python.org](https://www.python.org/downloads/), or install [Miniconda](https://docs.anaconda.com/miniconda/) if you plan to use the Anaconda path below.

## Installing from PyPI
Installing the AB from the Python Package Index (PyPI) can be done using the standard `pip` command. We strongly recommended installing the Activity Browser into a separate [virtual environment](https://realpython.com/python-virtual-environments-a-primer/)

### Creating a virtual environment
Firstly, create a directory for your virtual environments, such as C:/Users/me/virtualenvs/.
IF YOUR PYTHON VERSION IS SUPPORTED BY THE AB (see Supported Python versions), you can create a virtual environment in that location like this:
```
python -m venv C:/Users/me/virtualenvs/ab-beta
```
In case your python version is not supported, you can specify a specific python version like this (here python 3.12):
```
py -3.12 -m venv C:/Users/me/virtualenvs/ab-beta
```
Afterwards, activate the virtual environment:

```
# Windows:
C:\Users\me\virtualenvs\ab-beta\Scripts\activate

# macOS / Linux:
source ~/virtualenvs/ab-beta/bin/activate
```

### Activity Browser installation
After creating and activating the virtual environment, installing the Beta should be as simple as using the following command:
```
pip install activity-browser
```

### Launching the Activity Browser
The Activity Browser can then be launched by entering the following command:
```
activity-browser
```

## Installing from Anaconda
First make sure you have Conda installed

```
conda --version
```

And make sure your Conda is up to date

```
conda update conda
```


If you get an error, please download and install miniconda from anaconda.com https://www.anaconda.com/download/success

### Activity Browser Beta installation
Next we're going to create a new environment for the Activity Browser Beta release.
IF YOUR PYTHON VERSION IS SUPPORTED BY THE AB (see Supported Python versions), you can create the environment like this:
```
conda create -n ab_beta -c conda-forge -c lca -c cmutel lca::activity-browser
```
In case your python version is not supported, you can specify a specific python version like this (here python 3.12):
```
conda create -n ab_beta -c conda-forge -c lca -c cmutel lca::activity-browser python=3.12
```

Pin `lca::activity-browser`. Without that pin, conda prefers `conda-forge::activity-browser`, which is still Activity Browser 2 (Brightway2 + PySide2).

This will go through a few steps, some of which like `solving environment` may take a while. After installation has finished, activate the environment (same command on Windows, macOS, and Linux):

```
conda activate ab_beta
```

### Launching the Activity Browser
Launch the Activity Browser like you would normally
```
activity-browser
```

## Stand-alone installers

Pre-built packages are produced when a maintainer manually runs the **Build Executable** workflow in GitHub Actions (on the chosen branch) and uploaded as workflow artifacts. Maintainers then attach selected builds to [GitHub Releases](https://github.com/LCA-ActivityBrowser/activity-browser/releases).

| Platform | File |
|---|---|
| Windows | `ActivityBrowser-<version>-windows-x64-setup.exe` |
| macOS (Apple Silicon) | `ActivityBrowser-<version>-macos-arm64.dmg` |
| Linux | `ActivityBrowser-<version>-linux-x86_64.AppImage` |

Each release asset set also includes a `*-dependencies.txt` file listing the Python packages that were bundled into that build.

### Windows

1. Download the `*-windows-x64-setup.exe` installer from the Release.
2. Run it and accept the LGPL license terms.
3. Start Activity Browser from the Start Menu (or the desktop shortcut if you enabled that option).

Windows may show a SmartScreen warning for unsigned installers — choose **More info** → **Run anyway** if you trust the GitHub Release source.

### macOS (Apple Silicon)

1. Download the `*-macos-arm64.dmg`.
2. Open the DMG and drag **Activity Browser** to **Applications** (or run it from the DMG).
3. These builds are **not notarized**. On first launch, Gatekeeper may block the app:
   - In Finder, **Control-click** (right-click) the app → **Open** → confirm **Open**.
   - After that, normal double-clicks work for that user account.

Intel Macs are not covered by the current CI macOS artifact.

### Linux

1. Download the `*-linux-x86_64.AppImage`.
2. Make it executable: `chmod +x ActivityBrowser-*-linux-x86_64.AppImage`
3. Run it: `./ActivityBrowser-*-linux-x86_64.AppImage`

You may need FUSE (or a distro-specific AppImage runtime) depending on your distribution.
