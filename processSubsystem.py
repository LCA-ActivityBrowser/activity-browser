#!/usr/bin/env python
# -*- coding: utf-8 -*-
from brightway2 import *
from bw2data.utils import recursive_str_to_unicode
import itertools
import numpy as np
import warnings

class ProcessSubsystem(object):
    """A description of a simplified supply chain, which has the following characteristics:

    * It produces one or more outputs (products)
    * It has at least one process from an inventory database
    * It can have links back into the inventory process that are cut; these links can then be replaced at another point with alternative supply chains.
    * It has one scaling activity, which determines the amounts of the various inputs and outputs

    Args:
        * *name* (``str``): Name of the new process
        * *outputs* (``[(key, str, optional float)]``): A list of products produced by the simplified process. Format is ``(key into inventory database, product name, optional amount of product produced)``.
        * *chain* (``[key]``): A list of inventory processes in the supply chain (not necessarily in order).
        * *cuts* (``[(key, key, str)]``): A set of linkages in the supply chain that should be cut. These will appear as **negative** products (i.e. inputs) in the process-product table. Format is (input key, output key, product name).
        * *scaling activity* (key, optional): The reference activities for the supply chain. **Required** for circular supply chains; in simple supply chains, the scaling activity is calculated automatically.

    """
    def __init__(self, name, outputs, chain, cuts, **kwargs):
        self.key = None  # created when PSS saved to a DB
        self.name = name
        self.cuts = cuts
        self.chain = self.remove_cuts_from_chain(chain, self.cuts)
        self.depending_databases = list(set(c[0] for c in self.chain))
        self.filtered_database = self.getFilteredDatabase(self.depending_databases, self.chain)
        self.edges = self.construct_graph(self.filtered_database)
        self.isSimple, self.scaling_activities = self.getScalingActivities(self.chain, self.edges)
        self.outputs = self.pad_outputs(outputs)
        # self.check_outputs()
        self.mapping, self.matrix, self.supply_vector = \
            self.get_supply_vector(self.chain, self.edges, self.scaling_activities, self.outputs)
        self.pad_cuts()

    def remove_cuts_from_chain(self, chain, cuts):
        """Remove chain items if they are the parent of a cut. Otherwise this leads to unintended LCIA results.

        """
        for cut in cuts:
            if cut[0] in chain:
                chain.remove(cut[0])
                print "PSS WARNING: Cut removed from chain: " + str(cut[0])
        return set(chain)

    def pad_cuts(self):
        """
        Make sure that each cut includes the amount that is cut. This is retrieved from self.internal_scaled_edges_with_cuts
        """
        for i, c in enumerate(self.cuts):
            for e in self.internal_scaled_edges_with_cuts:
                if c[:2] == e[:2]:
                    try:
                        self.cuts[i] = (c[0], c[1], c[2], e[2])
                    except IndexError:
                        print "Problem with cut data: " + str(c)

    def pad_outputs(self, outputs):
        """Add default amount (1) to outputs if not present.

        Args:
            * *outputs* (list): outputs

        Returns:
            Padded outputs

        """
        padded_outputs = []
        for i, output in enumerate(outputs):  # add default name and quantity
            try:
                output_name = output[1]
            except IndexError:
                output_name = "Output " + str(i)
            try:
                output_quantity = float(output[2])
            except IndexError:
                output_quantity = 1.0
            except ValueError:
                print "ValueError in output quantity. Set to 1.0"
                output_quantity = 1.0
            padded_outputs.append((output[0], output_name, output_quantity))
        # add outputs that were not specified
        for sa in self.scaling_activities:
            if sa not in [o[0] for o in outputs]:
                print "PSS WARNING: Adding an output that was not specified: " + str(sa)
                padded_outputs.append((sa, "Unspecified Output", 1.0))
        # remove outputs that were specified, but are *not* outputs
        for o in outputs:
            if o[0] not in self.scaling_activities:
                print "PSS WARNING: Removing a specified output that is *not* actually an output: " + str(o[0])
                padded_outputs.remove(o)
        return padded_outputs

    def getFilteredDatabase(self, depending_databases, chain):
        """Extract the supply chain for this process from larger database.

        Args:
            * *nodes* (set): The datasets to extract (keys in db dict)
            * *db* (dict): The inventory database, e.g. ecoinvent

        Returns:
            A filtered database, in the same dict format

        """
        output = {}
        for name in depending_databases:
            db = Database(name).load()
            output.update(
                dict([(k, v) for k, v in db.iteritems() if k in chain])
            )
        return output

    def construct_graph(self, db):
        """Construct a list of edges.

        Args:
            * *db* (dict): The supply chain database

        Returns:
            A list of (in, out, amount) edges.

        """
        return list(itertools.chain(*[[(tuple(e["input"]), k, e["amount"])
                    for e in v["exchanges"] if e["type"] != "production"] for k, v in db.iteritems()]))

    def getScalingActivities(self, chain, edges):
        """Which are the scaling activities (at least one)?

        Calculate by filtering for processes which are not used as inputs.

        Args:
            * *chain* (set): The supply chain processes
            * *edges* (list): The list of supply chain edges

        Returns:
            Boolean isSimple, List heads.

        """
        used_inputs = [x[0] for x in edges if x[0] in chain]
        heads = set([tuple(x[1]) for x in edges if x[1] not in used_inputs])
        isSimple = len(heads) == 1
        return isSimple, list(heads)

    def get_supply_vector(self, chain, edges, scaling_activities, outputs):
        """Construct supply vector (solve linear system) for the supply chain of this simplified product system.

        Args:
            * *chain* (list): Nodes in supply chain
            * *edges* (list): List of edges
            * *scaling_activities* (key): Scaling activities

        Returns:
            Mapping from process keys to supply vector indices
            Supply vector (as list)

        """
        mapping = dict(*[zip(sorted(chain), itertools.count())])
        M = len(chain)
        matrix = np.zeros((M, M))
        # Set ones on diagonal; standard LCA stuff
        matrix[range(M), range(M)] = 1
        # Only add edges that are within our system
        # But, allow multiple links to same product (simply add them)
        for in_, out_, a in [x for x in edges if x[0] in chain and x[1] in chain]:
            matrix[
                mapping[in_],
                mapping[out_]
            ] -= a
        demand = np.zeros((M,))
        for a in scaling_activities:
            for o in [output for output in outputs if output[0] == a]:
                demand[mapping[a]] += o[2]
        return mapping, matrix, np.linalg.solve(matrix, demand).tolist()

    @property
    def external_edges(self):
        """Get list of edges outside our system, which are not cut"""
        return [x for x in self.edges if (x[0] not in self.chain and \
            x[:2] not in set([y[:2] for y in self.cuts]))]

    @property
    def external_scaled_edges(self):
        """Adjust edge amounts by scaling vector"""
        mapping, matrix, supply_vector = self.get_supply_vector(self.chain, self.edges,
            self.scaling_activities, self.outputs)
        return [(x[0], x[1], x[2] * supply_vector[mapping[x[1]]]
            ) for x in self.external_edges]

    @property
    def internal_edges(self):
        """Get list of edges in chain, i.e. that are not part of external edges or cuts"""
        return [x for x in self.edges if (x[0] in self.chain and \
            x[:2] not in set([y[:2] for y in self.cuts]))]

    @property
    def internal_edges_with_cuts(self):
        """Get list of edges in chain, i.e. that are not part of external edges or cuts"""
        return [x for x in self.edges if (x[0] in self.chain or \
            x[:2] in set([y[:2] for y in self.cuts]))]

    @property
    def internal_scaled_edges(self):
        """Scale internal edges according to scaling activities"""
        mapping, matrix, supply_vector = self.get_supply_vector(self.chain, self.edges,
            self.scaling_activities, self.outputs)
        return [(x[0], x[1], x[2] * supply_vector[mapping[x[1]]]
            ) for x in self.internal_edges]

    @property
    def internal_scaled_edges_with_cuts(self):
        """Scale internal edges (including cuts) according to scaling activities"""
        mapping, matrix, supply_vector = self.get_supply_vector(self.chain, self.edges,
            self.scaling_activities, self.outputs)
        return [(x[0], x[1], x[2] * supply_vector[mapping[x[1]]]
            ) for x in self.internal_edges_with_cuts]

    @property
    def pss_data(self):
        pss_data_dict = {
            'name': self.name,
            'outputs': self.outputs,
            'chain': list(self.chain),
            'cuts': self.cuts,
        }
        return pss_data_dict

    def save_supply_chain_as_new_dataset(self, db_name="PSS default", unit=None,
            location=None, categories=[]):
        """Save simplified process to a database.

        Creates database if necessary; otherwise *adds* to existing database. Uses the ``unit`` and ``location`` of ``self.scaling_activities[0]``, if not otherwise provided. Assumes that one unit of the scaling activity is being produced.

        Args:
            * *db_name* (str): Name of Database
            * *unit* (str, optional): Unit of the simplified process.
            * *location* (str, optional): Location of the simplified process.
            * *categories* (list, optional): Category/ies of the scaling activity.

        """
        db = Database(db_name)
        if db_name not in databases:
            db.register()
            data = {}
        else:
            data = db.load()
        # put together dataset information
        self.key = (db_name, self.name)  # TODO: change to UUID
        activity = self.scaling_activities[0]
        metadata = Database(activity[0]).load()[activity]
        # unit: if all scaling activities have the same unit, then set a unit, otherwise 'NA'
        if self.scaling_activities != 1:
            units_set = set([Database(sa[0]).load()[sa].get(u'unit', '') for sa in self.scaling_activities])
            if len(units_set) > 1:
                unit = 'several'  # if several units, display nothing
            else:
                unit = units_set.pop()
        data[self.key] = {
            "name": self.name,
            "unit": unit or metadata.get(u'unit', ''),
            "location": location or metadata.get(u'location', ''),
            "categories": categories,
            "type": "process",
            "exchanges": [{
                "amount": exc[2],
                "input": exc[0],
                "type": "biosphere" \
                    if exc[0][0] in (u"biosphere", u"biosphere3") \
                    else "technosphere",
                } for exc in self.external_scaled_edges],
        }
        # Production amount
        data[self.key]["exchanges"].append({
            "amount": 1,
            "input": self.key,
            "type": "production"
        })
        # TODO: Include uncertainty from original databases. Can't just scale
        # uncertainty parameters. Maybe solution is to use "dummy" processes
        # like we want to do to separate inputs of same flow in any case.
        # data = db.relabel_data(data, db_name)
        db.write(recursive_str_to_unicode(data))
        db.process()

    def lca(self, method, factorize=False):
        if not self.scaling_activities:
            raise ValueError("No scaling activity")
        if hasattr(self, "calculated_lca"):
            self.calculated_lca.method = method
            self.calculated_lca.lcia()
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                if not self.key:
                    self.save_supply_chain_as_new_dataset()
                self.calculated_lca = LCA(demand={self.key: 1}, method=method)
                self.calculated_lca.lci()
                if factorize:
                    self.calculated_lca.decompose_technosphere()
                self.calculated_lca.lcia()
        return self.calculated_lca.score

    def lci(self):
        if not self.scaling_activities:
            raise ValueError("No scaling activity")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if not self.key:
                self.save_supply_chain_as_new_dataset()
            self.calculated_lca = LCA(demand={self.key: 1})
        return self.calculated_lca.lci()

    # TODO
    def process_products(self, nodes, edges, cuts, outputs, scaling_activities, database):
        """Provide data for construction of process-product table.

        Note that products from multi-output activities are **not** scaled using the amounts in ``outputs``.

        Args:
            * *nodes* (list): List of processes in supply chain
            * *edges* (list): List of edges from ``construct_graph``
            * *cuts* (list): List of cuts from supply chain to inventory database
            * *outputs* (list): List of products
            * *scaling_activities* (key): The scaling activities
            * *database* (dict): Inventory database for supply chain

        Output:
            List of (name, amount) product names and amounts.

        """
        products_from_cuts = [(c[2],
            # Get edge amount
            filter(lambda y: y[0] == c[0] and y[1] == c[1], edges)[0][2] \
            # times supply amount of edge end times -1
            * self.supply_vector[self.mapping[c[1]]] * -1
            ) for c in cuts]

        # Cuts can be from multiple inputs but the same product
        # TODO: TEST
        r = {}
        for product, amount in products_from_cuts:
            r[product] = r.get(product, 0) + amount
        products_from_cuts = list(r.iteritems())

        activity = scaling_activities[0]  # TODO: extend to multiple activities
        a_data = database[activity]
        if a_data.get("multioutput", False):
            # Special handling for MO processes
            products_from_outputs = [(o[1], a_data["multioutput"][o[0]]
                ) for o in outputs]
        else:
            # One output from scaling activity or manually-specified
            # multi-output process
            products_from_outputs = [(o[1], o[2]) for o in outputs]

        return products_from_cuts + products_from_outputs

    @property
    def pp(self):
        """Shortcut, as full method uses no global state"""
        return self.process_products(self.chain, self.edges, self.cuts,
            self.outputs, self.scaling_activities, self.filtered_database)
