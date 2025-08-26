## Introduction
Thank you for showing interesting in the Beta for Activity Browser 3.0. This release has been a year in the making and we're happy to 
show of the hard work that's been put in and get it to a level where we're happy to show it to the wider public. Most notably AB3 will
support Brightway25 and multifunctionality. But there have also been a lot of changes to the look and experience of the Activity Browser.

Making so many changes inevitably also comes with creating a lot of bugs. We have tried to catch as may of them as we could, but in the 
end noone is better at finding bugs than you, our users, are. We invite you to install the Activity Browser 3.0 Beta and break it in as 
many ways as you possibly can. As long as you report the bugs you find back to us, so we can fix them.

Thank you for your help, and enjoy the new Activity Browser!

> [!IMPORTANT] 
> This is a **beta installation**. As always use of the Activity Browser is **at your own risk**, but take extra care with this installation. Back-up critical projects before opening them. 

## Distributions on PyPI and Anaconda
The Activity Browser 3 Beta is available both on [PyPI]() and [Anaconda](). Because not all necessary libraries are available on Anaconda
right now you need to do an extra `pip install` inside your Conda environment. 

#### Quick-Install PyPI
```
pip install activity-browser
```

#### Quick-Install Anaconda
```
conda create -n ab_beta -c conda-forge lca::activity-browser
conda activate ab_beta
pip install PySide6
```

For more elaborate installing instructions check out the page below for both [installing from PyPI](#installing-from-pypi) and [installing from Anaconda](#installing-from-anaconda).

## Installing from PyPI
Installing from the Python Package Index (PyPI) can be done using the standard `pip` command. We strongly recommended installing the
Activity Browser into a separate [virtual environment](https://realpython.com/python-virtual-environments-a-primer/)

First make sure you have Python installed on your PC by entering the following command into your terminal or command prompt.

```
python --version
```
If you get an error please install Python [using their install instructions](https://www.python.org/downloads/).

### Creating a virtual environment
Firstly, create a directory for your virtual environments, such as C:/Users/me/virtualenvs/. Then create a virtual environment in that 
location using the following command:
```
python -m venv C:/Users/me/virtualenvs/ab-beta
```
Afterwards, you need to activate the virtual environment, which differs between operating systems and shells. Using Window Command Prompt
activate the environment using this command:
```
C:\Users\me\virtualenvs\ab-beta\Scripts\activate.bat
```
For a full overview of activation commands, [check out the documentation here](https://docs.python.org/3/library/venv.html#how-venvs-work)

### Activity Browser Beta installation
After creating the virtual environment, installing the Beta should be as simple as using the following command:
```
pip install activity-browser
```

### Launching the Activity Browser
The Activity Browser can then be launched like so:
```
activity-browser
```

## Installing from Anaconda
First make sure you have Conda installed

```
conda --version
```

If you get an error, please download and install miniconda from anaconda.com https://www.anaconda.com/download/success

### Activity Browser Beta installation
Next we're going to create a new environment for the Activity Browser Beta release.

```
conda create -n ab_beta -c conda-forge lca::activity-browser
```

This will go through a few steps, some of which like `solving environment` may take a while. After installation has finished you can
activate the environment like so:

```
conda activate ab_beta
```

### PySide6 installation
We will need to install `PySide6` from a different source, as the fully functional version is not available on anaconda.

```
pip install PySide6
```

### Launching the Activity Browser
Launch the Activity Browser like you would normally
```
activity-browser
```