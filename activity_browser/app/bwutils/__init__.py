# -*- coding: utf-8 -*-
"""
bwutils is a collection of methods that build upon brightway2 and are generic enough to provide here so that we avoid
re-typing the same code in different parts of the Activity Browser.
"""
import brightway2 as bw
from .metadata import AB_metadata
from .montecarlo import CSMonteCarloLCA
from .multilca import MLCA, Contributions
from .presamples import PresamplesMLCA


def cleanup():
    n_dir = bw.projects.purge_deleted_directories()
    print('Deleted {} unused project directories!'.format(n_dir))
