# Activity Browser Contributing Guidelines

## Reporting bugs and proposing improvements

You can contribute to the development of the AB by reporting bugs. Please raise an issue in
the [main repository](https://github.com/LCA-ActivityBrowser/activity-browser/) and describe the buggy behaviour.
Use a short and descriptive title for the issue. Ideally describe what you expected to happen vs.
what actually happened. If there is a visual component to the bug, please also add a screenshot (just drag-and-drop
into your issue text). You can also add the output of the debug window or console if there is an error message
related to the bug.

If you have general proposals or improvement ideas for the AB, you can also open an issue in
the [main repository](https://github.com/LCA-ActivityBrowser/activity-browser/).

## Pull requests

If you want to propose changes to the code or the documentation, or if you have created a feature that you
want to add to the AB, please open a [pull request](https://help.github.com/articles/about-pull-requests/).
We use the [fork and pull model](https://help.github.com/articles/about-collaborative-development-models/)
for external contributions. Fork the [AB repo](https://github.com/LCA-ActivityBrowser/activity-browser/), apply
your changes in your forked repository and open pull requests from there. Please also add a short description
of what your PR accomplishes.

Whenever you open a pull requests, there are a few automated tests that will be run. If the Travis or
AppVeyor tests fail, it is likely that there is an error somewhere in your PR. You can check the logs of the
CI services to see what failed.

## Setting up a development environment

If you want to contribute code, we suggest the following setup:

- Set up the conda channels as explained in the readme
- Create a new conda environment, where only the dependencies of the AB are installed:
```
conda create -n dev_ab
conda activate dev_ab
conda install --channel conda-forge --only-deps activity-browser
```
- `cd` into your forked repository
- start the AB with this command: `python run-activity-browser.py`

## Running and writing tests

If you want to check whether your changes break anything essential, you can run the automated tests.
This requires some additional packages.

```bash
conda activate dev_ab
conda install pytest pytest-mock pytest-qt
```

You can then run the tests inside the repo like this:

```bash
py.test
# OR
pytest
# OR
python -m pytest
```

An AB window will open and perform some automated actions. If you interfere, test will most likely fail.

In an ideal case, you can write your own tests for new features that you add. Please see the tests that
are already present in the `tests` folder or look at the
[pytest-qt documentation](https://pytest-qt.readthedocs.io/en/latest/) for inspiration and examples.
