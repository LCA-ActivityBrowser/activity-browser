# -*- coding: utf-8 -*-
import numpy as np
import brightway2 as bw
from bw2analyzer import ContributionAnalysis
from brightway2 import get_activity

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
        # functional units
        self.func_units = cs['inv']
        self.fu_activity_keys = [list(fu.keys())[0] for fu in self.func_units]
        self.fu_index = {k: i for i, k in enumerate(self.fu_activity_keys)}
        self.rev_fu_index = {v: k for k, v in self.fu_index.items()}

        # methods
        self.methods = cs['ia']
        self.method_index = {m: i for i, m in enumerate(self.methods)}
        self.rev_method_index = {v: k for k, v in self.method_index.items()}

        # todo: get rid of the below
        self.method_dict_list = []
        for i, m in enumerate(self.methods):
            self.method_dict_list.append({m: i})

        self.lca = bw.LCA(demand=self.all, method=self.methods[0])
        self.lca.lci(factorize=True)
        self.method_matrices = []
        self.results = np.zeros((len(self.func_units), len(self.methods)))

        # data to be stored
        (self.rev_activity_dict, self.rev_product_dict, self.rev_biosphere_dict) = self.lca.reverse_dict()

        self.scaling_factors = dict()
        self.technosphere_flows = dict()  # Technosphere product flows for a given functional unit

        self.inventory = dict()  # Life cycle inventory (biosphere flows) by functional unit
        self.inventories = dict()  # Inventory (biosphere flows) by activity (e.g. 2000x15000) and functional unit.

        # self.characterized_inventories = np.zeros(
        #     (len(self.func_units), len(self.methods), self.lca.biosphere_matrix.shape[0]))
        self.elementary_flow_contributions = np.zeros(
            (len(self.func_units), len(self.methods), self.lca.biosphere_matrix.shape[0]))
        self.process_contributions = np.zeros(
            (len(self.func_units), len(self.methods), self.lca.technosphere_matrix.shape[0]))

        for method in self.methods:
            self.lca.switch_method(method)
            self.method_matrices.append(self.lca.characterization_matrix)

        for row, func_unit in enumerate(self.func_units):
            self.lca.redo_lci(func_unit)  # lca calculation

            # scaling factors
            self.scaling_factors.update({str(func_unit): self.lca.supply_array})

            # technosphere flows
            self.technosphere_flows.update({
                str(func_unit): np.multiply(self.lca.supply_array, self.lca.technosphere_matrix.diagonal())
            })

            # the life cycle inventory
            self.inventory.update({
                str(func_unit): np.array(self.lca.inventory.sum(axis=1)).ravel() #flatten().tolist()[0]  #.todense()
            })
            # the life cycle inventory disaggregated by contributing process
            self.inventories.update({
                str(func_unit): self.lca.inventory
            })

            for col, cf_matrix in enumerate(self.method_matrices):
                self.lca.characterization_matrix = cf_matrix
                self.lca.lcia_calculation()
                self.results[row, col] = self.lca.score
                #self.characterized_inventories[row, col] = self.lca.characterized_inventory
                self.elementary_flow_contributions[row, col] = np.array(
                    self.lca.characterized_inventory.sum(axis=1)).ravel()
                self.process_contributions[row, col] = self.lca.characterized_inventory.sum(axis=0)

        # todo: get rid of the below
        self.func_unit_translation_dict = {str(get_activity(list(func_unit.keys())[0])): func_unit
                                           for func_unit in self.func_units}
        #self.biosphere_flows_translation_dict =
        self.func_key_dict = {m: i for i, m in enumerate(self.func_unit_translation_dict.keys())}
        self.func_key_list = list(self.func_key_dict.keys())

    @property
    def all(self):
        """Get all possible databases by merging all functional units"""
        return {key: 1 for func_unit in self.func_units for key in func_unit}

    @property
    def results_normalized(self):
        return self.results / self.results.max(axis=0)

    # CONTRIBUTION ANALYSIS
    def top_process_contributions(self, functional_unit=None, method=None, limit=5, normalize=True, limit_type="number"):
        """ Return process contributions either
            * for one impact assessment method and a number of processes or
            * for one process and a number of impact assessment methods. """
        if (functional_unit and method) or (not functional_unit and not method):
            raise ValueError('It must be either by functional unit or by method.')
        if method:
            contribution_array = self.process_contributions[:, self.method_index[method], :]
        elif functional_unit:
            contribution_array = self.process_contributions[self.func_key_dict[functional_unit], :, :]

        # Normalise if required
        if normalize:
            contribution_array = self.normalize(contribution_array)

        if method:
            return self.build_dict(contribution_array, self.func_units,
                                   self.rev_activity_dict, limit, limit_type)
        elif functional_unit:
            return self.build_dict(contribution_array, self.method_dict_list,
                                   self.rev_activity_dict, limit, limit_type)

    def top_elementary_flow_contributions(self, functional_unit=None, method=None, limit=5, normalize=True, limit_type="number"):
        """ Return elementary flow contributions either
            * for one impact assessment method and a number of processes or
            * for one process and a number of impact assessment methods. """
        if (functional_unit and method) or (not functional_unit and not method):
            raise ValueError('It must be either by functional unit or by method.')
        if method:
            contribution_array = self.elementary_flow_contributions[:, self.method_index[method], :]
        elif functional_unit:
            contribution_array = self.elementary_flow_contributions[self.func_key_dict[functional_unit], :, :]

        # Normalised if required
        if normalize:
            contribution_array = self.normalize(contribution_array)

        if method:
            return self.build_dict(contribution_array, self.func_units,
                                   self.rev_biosphere_dict, limit, limit_type)
        elif functional_unit:
            return self.build_dict(contribution_array, self.method_dict_list,
                                   self.rev_biosphere_dict, limit, limit_type)

    def normalize(self, contribution_array):
        """ Normalise the contribution array. """
        scores = contribution_array.sum(axis=1)
        return (contribution_array / scores[:, np.newaxis])

    def build_dict(self, cont_arr, dict_set, rev_dict, limit, limit_type):
        """ Sort each method or functional unit column independently. """
        topcontribution_dict = {}
        for col, cont in enumerate(dict_set):
            top_contribution = ca.sort_array(cont_arr[col, :], limit=limit, limit_type=limit_type)
            cont_per = {}
            cont_per.update({
                ('Total', ''): cont_arr[col, :].sum(),
                ('Rest', ''): cont_arr[col, :].sum() - top_contribution[:, 0].sum()})
            for value, index in top_contribution:
                cont_per.update({rev_dict[index]: value})
            topcontribution_dict.update({next(iter(cont.keys())): cont_per})
        return topcontribution_dict