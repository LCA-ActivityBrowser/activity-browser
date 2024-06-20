# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals

from typing import Optional, Union

from activity_browser.bwutils import MLCA, SuperstructureMLCA

try:
    # try bw25 import
    from bw2calc.graph_traversal import \
        AssumedDiagonalGraphTraversal as GraphTraversal
except ImportError:
    from bw2calc import GraphTraversal


# TODO: This wont be required after migrating to brightway 2.5
class GraphTraversalWithScenario(GraphTraversal):

    def __init__(self, mlca: Optional[Union[MLCA, SuperstructureMLCA]] = None):
        self.mlca = mlca

    def build_lca(self, demand, method):
        return self.mlca.lca, self.mlca.lca.solve_linear_system(), self.mlca.lca.score
