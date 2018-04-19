# -*- coding: utf-8 -*-
import numpy as np
import brightway2 as bw
from bw2analyzer import ContributionAnalysis

ca = ContributionAnalysis()


class MLCA(object):
    """Wrapper class for performing LCA calculations with many functional units and LCIA methods.

    Needs to be passed a ``calculation_setup`` name.

    This class does not subclass the `LCA` class, and performs all calculations upon instantiation.

    Initialization creates `self.results`, which is a NumPy array of LCA scores, with rows of functional units and columns of LCIA methods. Ordering is the same as in the `calculation_setup`.

    Class adapted from bw2calc.multi_lca.MultiLCA to include also CONTRIBUTION ANALYSIS.

    """
    def __init__(self, cs_name):
        try:
            cs = bw.calculation_setups[cs_name]
        except KeyError:
            raise ValueError(
                "{} is not a known `calculation_setup`.".format(cs_name)
            )
        self.func_units = cs['inv']
        self.methods = cs['ia']
        self.method_dict = {m: i for i, m in enumerate(self.methods)}
        self.lca = bw.LCA(demand=self.all, method=self.methods[0])
        self.lca.lci(factorize=True)
        self.method_matrices = []
        self.results = np.zeros((len(self.func_units), len(self.methods)))

        # contribution matrices
        self.process_contributions = np.zeros(
            (len(self.func_units), len(self.methods), self.lca.technosphere_matrix.shape[0]))
        self.elementary_flow_contributions = np.zeros(
            (len(self.func_units), len(self.methods), self.lca.biosphere_matrix.shape[0]))
        (self.rev_activity_dict, self.rev_product_dict,
         self.rev_biosphere_dict) = self.lca.reverse_dict()

        for method in self.methods:
            self.lca.switch_method(method)
            self.method_matrices.append(self.lca.characterization_matrix)

        for row, func_unit in enumerate(self.func_units):
            self.lca.redo_lci(func_unit)
            for col, cf_matrix in enumerate(self.method_matrices):
                self.lca.characterization_matrix = cf_matrix
                self.lca.lcia_calculation()
                self.results[row, col] = self.lca.score
                self.process_contributions[row, col] = self.lca.characterized_inventory.sum(axis=0)
                self.elementary_flow_contributions[row, col] = np.array(
                    self.lca.characterized_inventory.sum(axis=1)).ravel()

    @property
    def all(self):
        """Get all possible databases by merging all functional units"""
        return {key: 1 for func_unit in self.func_units for key in func_unit}

    @property
    def results_normalized(self):
        return self.results / self.results.max(axis=0)

    # CONTRIBUTION ANALYSIS
    def top_process_contributions(self, method_name=None, limit=5, relative=True):
        if method_name:
            method = self.method_dict[method_name]
        else:
            method = 0
        contribution_array = self.process_contributions[:, method, :]
        if relative:
            fu_scores = contribution_array.sum(axis=1)
            contribution_array = contribution_array / fu_scores[:, np.newaxis]
        topcontribution_dict = {}
        for col, fu in enumerate(self.func_units):
            top_contribution = ca.sort_array(contribution_array[col, :], limit=limit)
            cont_per_fu = {}
            cont_per_fu.update(
                {('Rest', ''): contribution_array[col, :].sum() - top_contribution[:, 0].sum()})
            for value, index in top_contribution:
                cont_per_fu.update({self.rev_activity_dict[index]: value})
            topcontribution_dict.update({next(iter(fu.keys())): cont_per_fu})
        return topcontribution_dict

    def top_elementary_flow_contributions(self, method_name=None, limit=5, relative=True):
        if method_name:
            method = self.method_dict[method_name]
        else:
            method = 0
        contribution_array = self.elementary_flow_contributions[:, method, :]
        if relative:
            fu_scores = contribution_array.sum(axis=1)
            contribution_array = contribution_array / fu_scores[:, np.newaxis]
        topcontribution_dict = {}
        for col, fu in enumerate(self.func_units):
            top_contribution = ca.sort_array(contribution_array[col, :], limit=limit)
            cont_per_fu = {}
            cont_per_fu.update(
                {('Rest', ''): contribution_array[col, :].sum() - top_contribution[:, 0].sum()})
            for value, index in top_contribution:
                cont_per_fu.update({self.rev_biosphere_dict[index]: value})
            topcontribution_dict.update({next(iter(fu.keys())): cont_per_fu})
        return topcontribution_dict
