#!/usr/bin/env python
# -*- coding: utf-8 -*-

from metaprocess import MetaProcess
import itertools
import numpy as np
import networkx as nx  # TODO: get rid of this dependency

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
                assert isinstance(mp, MetaProcess)
                assert mp.name not in names  # check if process names are unique
                names.update(mp.name)
            except AssertionError:
                raise ValueError(u"Invalid input: must be Meta-Processes with unique names")
        self.mp_list = mp_list
        self.map_name_mp = dict([(mp.name, mp) for mp in self.mp_list])
        self.map_processes_number = dict(zip(self.processes, itertools.count()))
        self.map_products_number = dict(zip(self.products, itertools.count()))

    # SHORTCUTS

    @ property
    def processes(self):
        return sorted([mp.name for mp in self.mp_list])

    @ property
    def products(self):
        return sorted(set(itertools.chain(*[[x[0] for x in y.pp
            ] for y in self.mp_list])))

    # METHODS THAT RETURN DATA FOR A SUBSET OR THE ENTIRE LMPS

    def get_processes(self, mp_list=None):
        """
        returns a list of meta-processes
        mp_list can either be a list of names or a list of meta-processes
        :param mp_list:
        :return:
        """
        # if empty list return all meta-processes
        if not mp_list:
            return self.mp_list
        else:
            # if name list find corresponding meta-processes
            if not isinstance(mp_list[0], MetaProcess):
                return [self.map_name_mp.get(name, None) for name in mp_list]
            else:
                return mp_list

    def get_process_names(self, mp_list=None):
        """
        Input: a list of meta-processes. Output: a list of process names.
        :param mp_list:
        :return:
        """
        return sorted([mp.name for mp in self.get_processes(mp_list)])

    def get_product_names(self, mp_list=None):
        """
        Input: a list of meta-processes. Output: a list of product names.
        :return:
        """
        return sorted(set(itertools.chain(*[[x[0] for x in y.pp
            ] for y in self.get_processes(mp_list)])))

    def product_process_dict(self, mp_list=None, process_names=None, product_names=None):
        """
        returns dict, where products are keys and meta-processes producing these products are list values
        if process/product names are provided, these are used as filters
        equally, if mp_list is provided, it can be used as a filter
        otherwise all processes/products are considered
        """
        if not process_names:
            process_names = self.processes
        if not product_names:
            product_names = self.products
        product_processes = {}
        for mp in self.get_processes(mp_list):
            for output in mp.outputs:
                output_name = output[1]
                if output_name in product_names and mp.name in process_names:
                    product_processes[output_name] = product_processes.get(output_name, [])
                    product_processes[output_name].append(mp.name)
        return product_processes

    def edges(self, mp_list=None):
        edges = []
        for mp in self.get_processes(mp_list):
            for cut in mp.cuts:
                edges.append((cut[2], mp.name))
            for output in mp.outputs:
                edges.append((mp.name, output[1]))
        return edges

    def get_pp_matrix(self, mp_list=None):
        mp_list = self.get_processes(mp_list)
        matrix = np.zeros((len(self.get_product_names(mp_list)), len(mp_list)))
        map_processes_number = dict(zip(self.get_process_names(mp_list), itertools.count()))
        map_products_number = dict(zip(self.get_product_names(mp_list), itertools.count()))
        for mp in mp_list:
            for product, amount in mp.pp:
                matrix[map_products_number[product], map_processes_number[mp.name]] = amount
        return matrix, map_processes_number, map_products_number

    # ALTERNATIVE PATHWAYS

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
        Returns a list of tuples. Each tuple contains the meta-processes
        that make up a unique pathway to produce the functional unit.
        First all theoretical unique pathways are identified, then the
        theoretical pathways are reduced to actually different pathways
        by eliminating processes that are not actually part of those supply chains.
        Note: A better approach could be a graph traversal algorithm
        to find all paths (see and/or graphs in future).
        :param functional_unit:
        :return:
        """
        ancestor_processes, ancestor_products = self.upstream_products_processes(functional_unit)
        product_processes = self.product_process_dict(process_names=ancestor_processes, product_names=ancestor_products)
        # get all combinations of meta-processes
        # some are merely theoretical, i.e. contain processes that are not actually part of the supply chain
        unique_pathways = list(itertools.product(*product_processes.values()))

        # now we need to eliminate those combinations that don't make sense (if any)
        # each process within a unique path must have a simple path connection to the functional unit
        # otherwise it is not actually part of the supply chain; the code below checks for this
        # and assigns the value True to each process where this holds true
        unique_pathways_cleaned = []
        G = nx.DiGraph()
        G.add_edges_from(self.edges())
        for path in unique_pathways:
            process_part_of_path = {}
            for process in path:
                process_part_of_path.update({process: False})
                simple_paths = nx.all_simple_paths(G, process, functional_unit)
                for simple_path in simple_paths:
                    simple_path = [sp for sp in simple_path if sp in self.processes]
                    if [s in path for s in simple_path].count(True) == len(simple_path):
                        process_part_of_path[process] = True

            # remove process(es) from unique paths if they are not part of it
            for process, part_of_path in process_part_of_path.items():
                if not part_of_path:
                    # print process, path
                    path = list(path)
                    path.remove(process)
                    path = tuple(path)
            unique_pathways_cleaned.append(path)

        return list(set(unique_pathways_cleaned))

    # LCA

    def scaling_vector_foreground_demand(self, process_names, demand):
        """
        Returns a scaling dictionary for a given demand and matrix defined by a list of processes.
        Keys: process names. Values: scaling vector values.
        :param process_names:
        :param demand:
        :return:
        """
        # matrix
        matrix, map_processes, map_products = self.get_pp_matrix(process_names)
        try:
            # TODO: define conditions that must be met (e.g. square, single-output); Processes can still have multiple outputs (system expansion)
            assert matrix.shape[0] == matrix.shape[1]  # matrix needs to be square to be invertable!
        except AssertionError:
            print "Matrix must be square! Current shape:", matrix.shape[0], matrix.shape[1]
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

    def lca_processes(self, method, process_names=None, factorize=False):
        """
        returns dict where: keys = PSS name, value = LCA score
        """
        if not process_names:
            process_names = self.processes
        map_process_lcascore = dict([(mp.name, mp.lca(method, factorize=factorize))
                                     for mp in self.get_processes(process_names)])
        return map_process_lcascore

    def lca_linked_processes(self, method, process_names, demand):
        scaling_dict = self.scaling_vector_foreground_demand(process_names, demand)
        lca_scores = self.lca_processes(method, process_names)
        # multiply scaling vector with process LCA scores
        path_lca_score = 0.0
        process_contribution = {}
        for process, amount in scaling_dict.items():
            process_contribution.update({process: amount*lca_scores[process]})
            path_lca_score = path_lca_score + amount*lca_scores[process]
        process_contribution_relative = {}
        for process, amount in scaling_dict.items():
            process_contribution_relative.update({process: amount*lca_scores[process]/path_lca_score})

        output = {
            'meta-processes': process_names,
            'demand': demand,
            'scaling vector': scaling_dict,
            'LCIA method': method,
            'process contribution': process_contribution,
            'relative process contribution': process_contribution_relative,
            'LCA score': path_lca_score,
        }
        return output

    def lca_alternatives(self, method, demand):
        """
        Returns LCA results (a dict) for all pathways that can supply a given demand.
        'path' points to a tuple containing the processes along a pathway.
        'lca results' points to a dictionary with LCA results for a pathway.
        :param method:
        :param demand:
        :return:
        """
        # assume that only one product is demanded for now (functional unit)
        path_lca_data = []
        for path in self.all_pathways(demand.keys()[0]):
            path_lca_data.append(self.lca_linked_processes(method, path, demand))
        return path_lca_data









