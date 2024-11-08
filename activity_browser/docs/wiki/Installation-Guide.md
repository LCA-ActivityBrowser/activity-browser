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
Anaconda is somewhat like an app-store for python programs.
You can install the full [Anaconda user interface (navigator)](https://www.anaconda.com/download/success) 
or just the minimal command-line installer,
[Miniconda](https://docs.anaconda.com/miniconda/#miniconda-latest-installer-links).
If needed, see also the 
[conda user guide](https://docs.conda.io/projects/conda/en/latest/user-guide/index.html) 
or the 
[Conda cheat sheet](https://docs.conda.io/projects/conda/en/latest/_downloads/843d9e0198f2a193a3484886fa28163c/conda-cheatsheet.pdf).

- Install the Anaconda manager of your choice from the above options.
- Start `Anaconda Prompt` from the start menu.
  - This is a terminal window with `conda`, you will need this prompt for all next steps. 

## Add the conda-forge channel
Open an Anaconda prompt window and type the following (and `Enter`):
```bash
conda config --prepend channels conda-forge
```

<details><summary><b>More information about this step</b></summary>

Activity Browser has many dependencies that are managed by 
[conda-forge](https://conda.io/docs/user-guide/tasks/manage-channels.html).
By adding the channel you can install python packages from there.

The line above means:
- `conda`: a command for conda
- `config`: change something in the configuration (settings) of `conda`
- `--prepend channels`: in the channels from which conda can install things, add to the top (prepend)
- `conda-forge`:  the channel name
</details>

## Creating an environment and Installing Activity Browser
Next, we create a python environment, in which we install Activity Browser 

```bash
conda create -n ab -c conda-forge activity-browser
```

> [!NOTE]
> Installing Activity Browser can take some time, this depends on the speed of your internet connection and computer.

<details><summary><b>More information about this step</b></summary>

We create a separate environment, this allows Activity Browser to work with the specific versions of other libraries 
it needs without interfering with other python packages.

The line above means:
- `conda`: a command for conda
- `create -n ab`: create a new e**n**vironment (`-n`) with the name `ab`
- `-c conda-forge`: from the **c**hannel (`-c`) `conda-forge`
- `activity-browser`: install the package `activity-browser`

You can have as many environments as you like, you can also install different versions of Activity Browser 
in different environments, for example for different [plugins](Plugins), or just for using different version of 
Activity Browser. 

All environments will have access to the same projects and databases in Activity Browser. 

</details>

## Activating and running Activity Browser
To run Activity Browser, you need to activate your environment with
```bash
conda activate ab
```

And then run activity browser 
with.
```bash
activity-browser
```

Congratulations! You've started Activity Browser for the first time!

Every time you want to start Activity Browser, you need to start an anaconda prompt 
and do `conda activate ab` and then `activity browser`.

## Updating Activity Browser
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