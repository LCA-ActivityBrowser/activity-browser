## Quick Installation
<details><summary><b>Familiar with Conda already? Do a quick install</b></summary>

You can install and start the activity-browser like this:
1. Install [Miniconda](https://docs.anaconda.com/miniconda/#miniconda-latest-installer-links).
2. ```bash 
   conda create -n ab -c conda-forge activity-browser
   conda activate ab
   activity-browser
   ```
</details>

## The Anaconda package manager
Skip this step if you already have a working installation of Anaconda or Miniconda, but make sure to keep your 
conda installation up-to-date: `conda update -n base conda`.

You need the python package manager [Anaconda](https://anaconda.org) to install Activity Browser. 
You can install the full [Anaconda user interface (navigator)](https://www.anaconda.com/download/success) 
or just the minimal command-line installer,
[Miniconda](https://docs.anaconda.com/miniconda/#miniconda-latest-installer-links).
If needed, see also the 
[conda user guide](https://docs.conda.io/projects/conda/en/latest/user-guide/index.html) 
or the 
[Conda cheat sheet](https://docs.conda.io/projects/conda/en/latest/_downloads/843d9e0198f2a193a3484886fa28163c/conda-cheatsheet.pdf).

## Add the Conda-Forge channel
The Activity Browser has many dependencies that are managed by the 
[conda-forge](https://conda.io/docs/user-guide/tasks/manage-channels.html) 
channel. 
Open a cmd-window or terminal (in Windows you may have to use the Anaconda prompt) and type the following:
```bash
conda config --prepend channels conda-forge
```

## Installing Activity Browser
You can now install Activity Browser by creating a python environment (`ab`)

Depending on your computer and internet connection, it can take a while for this to complete.
You will need to confirm that you really want to install the environment.

```bash
conda create -n ab -c conda-forge activity-browser
```

## Activating and running Activity Browser
To run Activity Browser, you need to activate your environment with 
`conda activate ab` and then run activity browser 
with `activity-browser`.

Congratulations! You've started Activity Browser for the first time!

# Updating Activity Browser
We recommend to regularly update Activity Browser to receive new features & bugfixes. 
These commands will update the Activity Browser and all of its dependencies in the conda environment called `ab`.

```bash
conda activate ab
conda update activity-browser
```

> [!IMPORTANT]
> If you currently have a version <u>below</u> `2.10.0`, please consult 
> [this guide](https://github.com/LCA-ActivityBrowser/activity-browser/discussions/1049)
> to update.