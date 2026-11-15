---
title: Installation
parent: Getting started
nav_order: 1
---

# Installing the Activity Browser
{: .fs-9 }

The Activity Browser 3 Beta is available both on [PyPI](#installing-from-pypi) (our recommended path) and [Anaconda](#installing-from-anaconda). Please follow the respective instructions below.
{: .fs-6 .fw-300 }

### Supported Python versions
3.11, 3.12, 3.13, and 3.14.

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
