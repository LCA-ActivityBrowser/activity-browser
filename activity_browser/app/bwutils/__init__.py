# -*- coding: utf-8 -*-
"""
bwutils is a collection of methods that build upon brightway2 and are generic enough to provide here so that we avoid
re-typing the same code in different parts of the Activity Browser.
"""
import brightway2 as bw
from .metadata import AB_metadata
from .multilca import MLCA, Contributions
from .pedigree import PedigreeMatrix
from .presamples import PresamplesContributions, PresamplesMLCA
from .uncertainty import (
    CFUncertaintyInterface, ExchangeUncertaintyInterface,
    ParameterUncertaintyInterface, get_uncertainty_interface
)
from .montecarlo import MonteCarloLCA
from .sensitivity_analysis import GlobalSensitivityAnalysis

def cleanup():
    n_dir = bw.projects.purge_deleted_directories()
    print('Deleted {} unused project directories!'.format(n_dir))
