# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals

from typing import Optional, Union

from activity_browser.bwutils import MLCA, SuperstructureMLCA

from bw_graph_tools import NewNodeEachVisitGraphTraversal


# TODO: This wont be required after migrating to brightway 2.5
class GraphTraversalWithScenario(NewNodeEachVisitGraphTraversal):
    def __init__(self, mlca: Optional[Union[MLCA, SuperstructureMLCA]] = None):
        self.mlca = mlca

    def build_lca(self, demand, method):
        return self.mlca.lca, self.mlca.lca.solve_linear_system(), self.mlca.lca.score
