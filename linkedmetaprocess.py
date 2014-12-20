#!/usr/bin/env python
# -*- coding: utf-8 -*-

from metaprocess import ProcessSubsystem
import itertools
import numpy as np
import networkx as nx

class LinkedMetaProcessSystem(object):
    """
    A class for doing stuff with linked meta-procseses.
    Can not:
    - contain 2 processes with the same name
    Args:
    * *mp_list* (``[MetaProcess]``): A list of meta-processes
    """

    def __init__(self, mp_list):
        for mp in mp_list:
            names = set()
            try:
                assert isinstance(mp, ProcessSubsystem)
                assert mp.name not in names  # check if process names are unique
                names.update(mp.name)
            except AssertionError:
                raise ValueError(u"Invalid input: must be Meta-Processes with unique names")
        self.mp_list = mp_list
        self.map_name_mp = dict([(mp.name, mp) for mp in self.mp_list])
        self.map_processes_number = dict(zip(self.processes, itertools.count()))
        self.map_products_number = dict(zip(self.products, itertools.count()))
        self.lca_results = {}  # {meta-process name: lca score}

    @ property
    def processes(self):
        return sorted([mp.name for mp in self.mp_list])

    @ property
    def products(self, mp_list=None):
        return sorted(set(itertools.chain(*[[x[0] for x in y.pp
            ] for y in self.mp_list])))

    @ property
    def pp_matrix(self):
        matrix = np.zeros((len(self.products), len(self.processes)))
        for mp in self.mp_list:
            for product, amount in mp.pp:
                matrix[self.map_products_number[product], self.map_processes_number[mp.name]] = amount
        return matrix

    def ppm(self):
        return self.processes, self.products, self.pp_matrix

    def get_processes(self, name_list):
        return [self.map_name_mp.get(name, None) for name in name_list]

    def get_process_names(self, mp_list):
        """
        Input: a list of meta-processes. Output: a list of process names.
        :param mp_list:
        :return:
        """
        return sorted([mp.name for mp in mp_list])

    def get_product_names(self, mp_list):
        """
        Input: a list of meta-processes. Output: a list of product names.
        :return:
        """
        return sorted(set(itertools.chain(*[[x[0] for x in y.pp
            ] for y in mp_list])))

    def get_pp_matrix(self, mp_list):
        # accepts both a list of names or a list of meta-processes
        if not isinstance(mp_list[0], ProcessSubsystem):
            mp_list = self.get_processes(mp_list)
        matrix = np.zeros((len(self.get_product_names(mp_list)), len(mp_list)))
        map_processes_number = dict(zip(self.get_process_names(mp_list), itertools.count()))
        map_products_number = dict(zip(self.get_product_names(mp_list), itertools.count()))
        for mp in mp_list:
            for product, amount in mp.pp:
                matrix[map_products_number[product], map_processes_number[mp.name]] = amount
        return matrix, map_processes_number, map_products_number

    def scaling_vector_foreground_demand(self, process_list, demand):
        # matrix
        matrix, map_processes, map_products = self.get_pp_matrix(process_list)
        try:
            # TODO: define conditions that must be met (e.g. square, single-output); Processes can still have multiple outputs (system expansion)
            assert matrix.shape[0] == matrix.shape[1]  # matrix needs to be square to be invertable!
        except AssertionError:
            print "Matrix must be square!", matrix.shape[0], matrix.shape[1]
            return False
        # demand vector
        demand_vector = np.zeros((len(matrix),))
        for name, amount in demand.items():
            demand_vector[map_products[name]] = amount
        # scaling vector
        try:
            scaling_vector = np.linalg.solve(matrix, demand_vector).tolist()
        except np.linalg.linalg.LinAlgError:
            print "Singular matrix. Cannot solve."
            return False
        except:
            print "Could not solve matrix"
        scaling_dict = dict([(name, scaling_vector[index]) for name, index in map_processes.items()])
        # # foreground product demand (can be different from scaling vector if diagonal values are not 1)
        # foreground_demand = {}
        # for name, amount in scaling_dict.items():
        #     number_in_matrix = map_processes[name]
        #     product = [name for name, number in map_products.items() if number == number_in_matrix][0]
        #     foreground_demand.update({
        #         product: amount*matrix[number_in_matrix, number_in_matrix]
        #     })
        return scaling_dict  # foreground_demand


    def product_process_dict(self, process_list=None, product_list=None):
        """
        returns dict, where products are keys and meta-processes producing these products are list values
        if process/product lists are provided, these are used as filters
        otherwise all processes/products are considered
        """
        if not process_list:
            process_list = self.processes
        if not product_list:
            product_list = self.products
        product_processes = {}
        for mp in self.mp_list:
            output = mp.outputs[0][1]  # assuming all processes are single-output!!
            name = mp.name
            if output in product_list and name in process_list:
                product_processes[output] = product_processes.get(output, [])
                product_processes[output].append(name)
        return product_processes

    def edges(self):
        edges = []
        for mp in self.mp_list:
            for input in mp.cuts:
                edges.append((input[2], mp.name))
            for output in mp.outputs:
                edges.append((mp.name, output[1]))
        return edges

    def upstream_products_processes(self, product):
        """
        Returns all upstream products and processes related to a certain product (functional unit)
        :param product:
        :return:
        """
        G = nx.DiGraph()
        G.add_edges_from(self.edges())
        product_ancestors = nx.ancestors(G, product)  # set
        product_ancestors.update([product])  # add product (although not an ancestor in a strict sense)
        # split up into products and processes
        ancestor_processes = [a for a in product_ancestors if a in self.processes]
        ancestor_products = [a for a in product_ancestors if a in self.products]
        return ancestor_processes, ancestor_products

    def all_pathways(self, functional_unit):
        """
        Returns a list of tuples. Each tuple contains the meta-processes that make up a unique pathway to produce the functional unit.
        :param functional_unit:
        :return:
        """
        ancestor_processes, ancestor_products = self.upstream_products_processes(functional_unit)
        product_processes = self.product_process_dict(process_list=ancestor_processes, product_list=ancestor_products)
        # get all combinations of meta-processes
        # TODO: this can give too many combinations, if not all processes are in a specific path
        unique_pathways = list(itertools.product(*product_processes.values()))
        return unique_pathways

    def lca_processes(self, method, process_list=None, factorize=False):
        """
        returns dict where: keys = PSS name, value = LCA score
        """
        if not process_list:
            process_list = self.processes
        map_process_lcascore = dict([(mp.name, mp.lca(method, factorize=factorize))
                                     for mp in self.mp_list if mp.name in process_list])
        return map_process_lcascore

    def lca_linked_processes(self, method, process_list, demand):
        scaling_dict = self.scaling_vector_foreground_demand(process_list, demand)
        lca_scores = self.lca_processes(method, process_list)
        # multiply scaling vector with process LCA scores
        output = {}
        # TODO: process contribution
        for process, amount in scaling_dict.items():
            output.update({
                process: amount*lca_scores[process],
                'total score': output.get('total score', 0) + amount*lca_scores[process],
            })
        return output

    def lca_alternatives(self, method, demand):
        # assume that only one product is demanded for now (functional unit)
        lca_results = []
        for alternative in self.all_pathways(demand.keys()[0]):
            lca_results.append({
                'path': alternative,
                'lca results': self.lca_linked_processes(method, alternative, demand)
            })
        return lca_results









