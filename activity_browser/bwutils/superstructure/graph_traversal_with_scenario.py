# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals, division

from typing import Optional, Union
from bw2calc import GraphTraversal
from activity_browser.bwutils import MLCA, PresamplesMLCA, SuperstructureMLCA


class GraphTraversalWithScenario(GraphTraversal):

    def __init__(self, mlca: Optional[Union[MLCA, PresamplesMLCA, SuperstructureMLCA]] = None):
        self.mlca = mlca

    def build_lca(self, demand, method):
        return self.mlca.lca, self.mlca.lca.solve_linear_system(), self.mlca.lca.score
