---
title: Installation
parent: Getting started
nav_order: 1
---

# Installing the Activity Browser
{: .fs-9 }

The easiest path for most users is a [stand-alone installer](#stand-alone-installers) (no Python setup). You can also install from [PyPI](#installing-from-pypi) or [Anaconda](#installing-from-anaconda) if you want Activity Browser inside your own Python environment.
{: .fs-6 .fw-300 }

## Stand-alone installers

Download the build for your OS (same files as the [stand-alone GitHub Release](https://github.com/LCA-ActivityBrowser/activity-browser/releases/tag/stand-alone)):

[Windows](https://github.com/LCA-ActivityBrowser/activity-browser/releases/download/stand-alone/ActivityBrowser-stand-alone-windows-x64-setup.exe){: .btn .btn-primary .fs-5 .mb-2 .mr-2 }
[macOS (Apple Silicon)](https://github.com/LCA-ActivityBrowser/activity-browser/releases/download/stand-alone/ActivityBrowser-stand-alone-macos-arm64.dmg){: .btn .btn-primary .fs-5 .mb-2 .mr-2 }
[Linux](https://github.com/LCA-ActivityBrowser/activity-browser/releases/download/stand-alone/ActivityBrowser-stand-alone-linux-x86_64.AppImage){: .btn .btn-primary .fs-5 .mb-2 .mr-2 }

[All stand-alone releases on GitHub](https://github.com/LCA-ActivityBrowser/activity-browser/releases/tag/stand-alone){: .btn .fs-5 .mb-4 }

Stand-alone builds report version `{PyPI-version}-stand-alone` (for example `3.0.0b202611151932-stand-alone`) so you can match them to the corresponding Activity Browser release on PyPI/conda.

| Platform | File (stable name) |
|---|---|
| Windows | `ActivityBrowser-stand-alone-windows-x64-setup.exe` |
| macOS (Apple Silicon) | `ActivityBrowser-stand-alone-macos-arm64.dmg` |
| Linux | `ActivityBrowser-stand-alone-linux-x86_64.AppImage` |

### Windows

1. Download the Windows installer with the button above.
2. Run it and accept the LGPL license terms.
3. Start Activity Browser from the Start Menu (or the desktop shortcut if you enabled that option).

Windows builds are **not code-signed**. Firefox/Chrome may warn that the file
“contains a virus or malware”, and SmartScreen may block the installer — these
are common false positives for new unsigned apps. If you trust the official
GitHub Release, choose **Keep** / **Download anyway**, then SmartScreen
**More info** → **Run anyway**.

### macOS (Apple Silicon)

1. Download the DMG with the button above.
2. Open the DMG and drag **Activity Browser** to **Applications** (or run it from the DMG).
3. These builds are **not notarized**. On first launch, Gatekeeper may block the app:
   - In Finder, **Control-click** (right-click) the app → **Open** → confirm **Open**.
   - After that, normal double-clicks work for that user account.

Intel Macs are not covered by the current CI macOS artifact.

### Linux

1. Download the AppImage with the button above.
2. Make it executable: `chmod +x ActivityBrowser-stand-alone-linux-x86_64.AppImage`
3. Run it: `./ActivityBrowser-stand-alone-linux-x86_64.AppImage`

You may need FUSE (or a distro-specific AppImage runtime) depending on your distribution.

---

### Supported Python versions (PyPI / Anaconda only)
3.11, 3.12, 3.13, and 3.14. Stand-alone builds bundle their own Python runtime.

### New to Python?

If you prefer PyPI or Anaconda instead of stand-alone, install a supported Python from [python.org](https://www.python.org/downloads/) or [Miniconda](https://docs.anaconda.com/miniconda/) ([install guide](https://docs.anaconda.com/miniconda/install/)).

### Check your Python version

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
