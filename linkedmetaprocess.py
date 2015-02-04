#!/usr/bin/env python
# -*- coding: utf-8 -*-

from metaprocess import MetaProcess
import itertools
import numpy as np
import networkx as nx  # TODO: get rid of this dependency
import pickle


class LinkedMetaProcessSystem(object):
    """
    A linked meta-process system holds several interlinked meta-processes. It has methods for:

    * loading / saving linked meta-process systems
    * returning information, e.g. product and process names, the product-process matrix
    * determining all alternatives to produce a given functional unit
    * calculating LCA results for individual meta-processes
    * calculating LCA results for a demand from the linked meta-process system (possibly for all alternatives)

    Meta-processes *cannot* contain:

    * 2 processes with the same name
    * identical names for products and processes (recommendation is to capitalize process names)

    Args:

    * *mp_list* (``[MetaProcess]``): A list of meta-processes
    """

    def __init__(self, mp_list=None):
        self.mp_list = []
        self.map_name_mp = dict()
        self.map_processes_number = dict()
        self.map_products_number = dict()
        self.map_number_processes = dict()
        self.map_number_products = dict()
        self.name_map = {}  # {activity key: output name}
        self.raw_data = []
        self.has_multi_output_processes = False
        self.has_loops = False
        if mp_list:
            self.update(mp_list)

    def update(self, mp_list):
        """
        Updates the linked meta-process system every time processes
        are added, modified, or deleted.
        Errors are thrown in case of:

        * identical names for products and processes
        * identical names of different meta-processes
        * if the input is not of type MetaProcess()
        """
        product_names, process_names = set(), set()
        for mp in mp_list:
            if not isinstance(mp, MetaProcess):
                raise ValueError(u"Input must be of MetaProcesses type.")
            try:
                assert mp.name not in process_names  # check if process names are unique
                process_names.add(mp.name)
                product_names.update(self.get_product_names([mp]))
            except AssertionError:
                raise ValueError(u'Meta-Process names must be unique.')
        for product in product_names:
            if product in process_names:
                raise ValueError(u'Product and Process names cannot be identical.')
        self.mp_list = mp_list
        self.map_name_mp = dict([(mp.name, mp) for mp in self.mp_list])
        self.map_processes_number = dict(zip(self.processes, itertools.count()))
        self.map_products_number = dict(zip(self.products, itertools.count()))
        self.map_number_processes = {v: k for k, v in self.map_processes_number.items()}
        self.map_number_products = {v: k for k, v in self.map_products_number.items()}
        self.update_name_map()
        self.raw_data = [mp.mp_data for mp in self.mp_list]
        # multi-output
        self.has_multi_output_processes = False
        for mp in self.mp_list:
            if mp.is_multi_output:
                self.has_multi_output_processes = True
        # check for loops
        G = nx.DiGraph()
        G.add_edges_from(self.edges())
        if [c for c in nx.simple_cycles(G)]:
            self.has_loops = True
        else:
            self.has_loops = False

        print '\nMeta-process system with', len(self.products), 'products and', len(self.processes), 'processes.'
        print 'Loops:', self.has_loops, ', Multi-output processes:', self.has_multi_output_processes

    def update_name_map(self):
        """
        Updates the name map, which maps product names (outputs or cuts) to activity keys.
        This is used in the Activity Browser to automatically assign a product name to already known activity keys.
        """
        for mp in self.mp_list:
            for output in mp.outputs:
                self.name_map[output[0]] = self.name_map.get(output[0], set())
                self.name_map[output[0]].add(output[1])
            for cut in mp.cuts:
                self.name_map[cut[0]] = self.name_map.get(cut[0], set())
                self.name_map[cut[0]].add(cut[2])

    # SHORTCUTS

    @ property
    def processes(self):
        """Returns all process names."""
        return sorted([mp.name for mp in self.mp_list])

    @ property
    def products(self):
        """Returns all product names."""
        return sorted(set(itertools.chain(*[[x[0] for x in y.pp
            ] for y in self.mp_list])))

    # DATABASE METHODS (FILE I/O, LMPS MODIFICATION)

    def load_from_file(self, filepath, append=False):
        """
        Loads a meta-process database, makes a MetaProcess object from each meta-process and
        adds them to the linked meta-process system.

        Args:

        * filepath: file path
        * append: adds loaded meta-processes to the existing database if True
        """
        try:
            with open(filepath, 'r') as infile:
                raw_data = pickle.load(infile)
        except:
            raise IOError(u'Could not load file.')
        mp_list = [MetaProcess(**mp) for mp in raw_data]
        if append:
            self.add_mp(mp_list, rename=True)
        else:
            self.update(mp_list)

    def save_to_file(self, filepath):
        """Saves data for each meta-process in the meta-process data format using pickle and updates the linked meta process system."""
        with open(filepath, 'w') as outfile:
            pickle.dump(self.raw_data, outfile)

    def add_mp(self, mp_list, rename=False):
        """
        Adds meta-processes to the linked meta-process system.

        *mp_list* can contain meta-process objects or the original data format used to initialize meta-processes.
        """
        new_mp_list = []
        for mp in mp_list:
            if not isinstance(mp, MetaProcess):
                mp = MetaProcess(**mp)
            new_mp_list.append(mp)
        if rename:
            for mp in new_mp_list:
                if mp.name in self.processes:
                    mp.name += '__ADDED'
        self.update(self.mp_list + new_mp_list)

    def remove_mp(self, mp_list):
        """
        Remove meta-processes from the linked meta-process system.

        *mp_list* can be a list of meta-process objects or meta-process names.
        """
        for mp in mp_list:
            if not isinstance(mp, MetaProcess):
                mp = self.get_processes([mp])
            self.mp_list.remove(mp[0])
        self.update(self.mp_list)

    # METHODS THAT RETURN DATA FOR A SUBSET OR THE ENTIRE LMPS

    def get_processes(self, mp_list=None):
        """
        Returns a list of meta-processes.

        *mp_list* can be a list of meta-process objects or meta-process names.
        """
        # if empty list return all meta-processes
        if not mp_list:
            return self.mp_list
        else:
            # if name list find corresponding meta-processes
            if not isinstance(mp_list[0], MetaProcess):
                return [self.map_name_mp.get(name, None) for name in mp_list if name in self.processes]
            else:
                return mp_list

    def get_process_names(self, mp_list=None):
        """Returns a the names of a list of meta-processes."""
        return sorted([mp.name for mp in self.get_processes(mp_list)])

    def get_product_names(self, mp_list=None):
        """Returns the output and input product names of a list of meta-processes.

        *mp_list* can be a list of meta-process objects or meta-process names.
        """
        return sorted(set(itertools.chain(*[[x[0] for x in y.pp
            ] for y in self.get_processes(mp_list)])))

    def get_output_names(self, mp_list=None):
        """ Returns output product names for a list of meta-processes."""
        return sorted(list(set([name for mp in self.get_processes(mp_list) for name in mp.output_names])))

    def get_cut_names(self, mp_list=None):
        """ Returns cut/input product names for a list of meta-processes."""
        return sorted(list(set([name for mp in self.get_processes(mp_list) for name in mp.cut_names])))

    def product_process_dict(self, mp_list=None, process_names=None, product_names=None):
        """
        Returns a dictionary that maps meta-processes to produced products (key: product, value: meta-process).
        Optional arguments ``mp_list``, ``process_names``, ``product_names`` can used as filters.
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
        """
        Returns an edge list for all edges within the linked meta-process system.

        *mp_list* can be a list of meta-process objects or meta-process names.
        """
        edges = []
        for mp in self.get_processes(mp_list):
            for cut in mp.cuts:
                edges.append((cut[2], mp.name))
            for output in mp.outputs:
                edges.append((mp.name, output[1]))
        return edges

    def get_pp_matrix(self, mp_list=None):
        """
        Returns the product-process matrix as well as two dictionaries
        that hold row/col values for each product/process.

        *mp_list* can be used to limit the scope to the contained processes
        """
        mp_list = self.get_processes(mp_list)
        matrix = np.zeros((len(self.get_product_names(mp_list)), len(mp_list)))
        map_processes_number = dict(zip(self.get_process_names(mp_list), itertools.count()))
        map_products_number = dict(zip(self.get_product_names(mp_list), itertools.count()))
        for mp in mp_list:
            for product, amount in mp.pp:
                matrix[map_products_number[product], map_processes_number[mp.name]] += amount
        return matrix, map_processes_number, map_products_number

    # ALTERNATIVE PATHWAYS

    def upstream_products_processes(self, product):
        """Returns all upstream products and processes related to a certain product (functional unit)."""
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
        Returns all alternative pathways to produce a given functional unit. Data output is a list of lists.
        Each sublist contains one path made up of products and processes.
        The input Graph may not contain cycles. It may contain multi-output processes.

        Args:

        * *functional_unit*: output product
        """
        def dfs(current_node, visited, parents, direction_up=True):
            # print current_node
            if direction_up:
                visited += [current_node]
            if current_node in self.products:
                # go up to all processes if none has been visited previously, else go down
                upstream_processes = G.predecessors(current_node)
                if upstream_processes and not [process for process in upstream_processes if process in visited]:
                    parents += [current_node]
                    for process in upstream_processes:
                        dfs(process, visited[:], parents[:])  # needs a real copy due to mutable / immutable
                else:  # GO DOWN or finish
                    if parents:
                        downstream_process = parents.pop()
                        dfs(downstream_process, visited, parents, direction_up=False)
                    else:
                        results.append(visited)
                        # print 'Finished'
            else:  # node = process; upstream = product
                # go to one upstream product, if there is one unvisited, else go down
                upstream_products = G.predecessors(current_node)
                unvisited = [product for product in upstream_products if product not in visited]
                #print 'unvisited:', unvisited
                if unvisited:  # GO UP
                    parents += [current_node]
                    dfs(unvisited[0], visited, parents)
                else:  # GO DOWN or finish
                    if parents:
                        downstream_product = parents.pop()
                        dfs(downstream_product, visited, parents, direction_up=False)
                    else:
                        print 'Finished @ process, this should not happen if a product was demanded.'
            return results

        results = []
        G = nx.DiGraph()
        G.add_edges_from(self.edges())
        return dfs(functional_unit, [], [])

    # LCA

    def scaling_vector_foreground_demand(self, mp_list, demand):
        """
        Returns a scaling dictionary for a given demand and matrix defined by a list of processes (or names).
        Keys: process names. Values: scaling vector values.

        Args:

        * *mp_list*: meta-process objects or names
        * *demand* (dict): keys: product names, values: amount
        """
        # matrix
        matrix, map_processes, map_products = self.get_pp_matrix(mp_list)
        try:
            # TODO: define conditions that must be met (e.g. square, single-output); Processes can still have multiple outputs (system expansion)
            assert matrix.shape[0] == matrix.shape[1]  # matrix needs to be square to be invertable!
            # demand vector
            demand_vector = np.zeros((len(matrix),))
            for name, amount in demand.items():
                demand_vector[map_products[name]] = amount
            # scaling vector
            scaling_vector = np.linalg.solve(matrix, demand_vector).tolist()
            scaling_dict = dict([(name, scaling_vector[index]) for name, index in map_processes.items()])
            # # foreground product demand (can be different from scaling vector if diagonal values are not 1)
            # foreground_demand = {}
            # for name, amount in scaling_dict.items():
            #     number_in_matrix = map_processes[name]
            #     product = [name for name, number in map_products.items() if number == number_in_matrix][0]
            #     foreground_demand.update({
            #         product: amount*matrix[number_in_matrix, number_in_matrix]
            #     })
            return scaling_dict  # , foreground_demand
        except AssertionError:
            print "Product-Process Matrix must be square! Currently", matrix.shape[0], 'products and', matrix.shape[1], 'processes.'

    def lca_processes(self, method, process_names=None, factorize=False):
        """Returns a dictionary where *keys* = meta-process name, *value* = LCA score
        """
        return dict([(mp.name, mp.lca(method, factorize=factorize))
                     for mp in self.get_processes(process_names)])

    def lca_linked_processes(self, method, process_names, demand):
        """
        Performs LCA for a given demand from a linked meta-process system.
        Works only for square matrices (see scaling_vector_foreground_demand).

        Returns a dictionary with the following keys:

        * *path*: involved process names
        * *demand*: product demand
        * *scaling vector*: result of the demand
        * *LCIA method*: method used
        * *process contribution*: contribution of each process
        * *relative process contribution*: relative contribution
        * *LCIA score*: LCA result

        Args:

        * *method*: LCIA method
        * *process_names*: selection of processes from the linked meta-process system (that yields a square matrix)
        * *demand* (dict): keys: product names, values: amount
        """
        scaling_dict = self.scaling_vector_foreground_demand(process_names, demand)
        if not scaling_dict:
            return
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
            'path': process_names,
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
        Calculation of LCA results for all alternatives in a linked meta-process system that yield a certain demand.
        Results are stored in a list of dictionaries as described in 'lca_linked_processes'.

        Args:

        * *method*: LCIA method
        * *demand* (dict): keys: product names, values: amount
        """
        if self.has_multi_output_processes:
            print '\nCannot calculate LCAs for alternatives as system contains ' \
                  'loops (', self.has_loops, ') / multi-output processes (', self.has_multi_output_processes, ').'
        else:
            # assume that only one product is demanded for now (functional unit)
            path_lca_data = []
            for path in self.all_pathways(demand.keys()[0]):
                path_lca_data.append(self.lca_linked_processes(method, path, demand))
            return path_lca_data
