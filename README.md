# An Activity Browser to brightway2 and extensions #

## User interface ##

Brightway2 is an open source software for life cycle assessment (LCA) (see here: http://brightwaylca.org/). This package extends brightway2 with a user interface based on PyQt - the Activity Browser.

## Extensions ##
### Fast screening of alternative life cycles and LCA based optimization ###

The Activity Browser is extended with a tool to group life cycle inventories into meta-level processes (called *meta-processes* or *process subsystems*). These can be used to efficiently re-link parts of life cycle process chains to form previously not modelled life cycles. This can be extremely efficient for screening alternative life cycles (e.g. different upstream technologies). For more complex systems (including multi-output activities) it serves as an efficient bridge towards optimization problems, both in data preparation as well as regarding the formulation of the problem to be analysed.

## Documentation ##
More documentation including a journal article are in the pipeline and should soon be available.

## Installation requirements ##

* you need a Python environment with PyQt and Pyside installed. You also need to have brightway2 installed.

## Contributions and contact##

* you are welcome to contribute
* please feel free to contact me: steubing@ifu.baug.ethz.ch
