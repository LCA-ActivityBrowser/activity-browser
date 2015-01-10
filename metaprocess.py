#!/usr/bin/env python
# -*- coding: utf-8 -*-
from brightway2 import *
from bw2data.utils import recursive_str_to_unicode
import itertools
import numpy as np
import uuid

class MetaProcess(object):
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
    # TODO: introduce UUID for meta-processes?

    # INTERNAL METHODS FOR CONSTRUCTING META-PROCESSES

    def __init__(self, name, outputs, chain, cuts, output_based_scaling=True, **kwargs):
        self.key = None  # created when PSS saved to a DB
        self.name = name
        self.cuts = cuts
        self.output_based_scaling = output_based_scaling
        self.chain = self.remove_cuts_from_chain(chain, self.cuts)
        self.depending_databases = list(set(c[0] for c in self.chain))
        self.filtered_database = self.getFilteredDatabase(self.depending_databases, self.chain)
        self.edges = self.construct_graph(self.filtered_database)
        self.scaling_activities, self.isSimple = self.getScalingActivities(self.chain, self.edges)
        self.outputs = self.pad_outputs(outputs)
        self.mapping, self.demand, self.matrix, self.supply_vector = \
            self.get_supply_vector(self.chain, self.edges, self.scaling_activities, self.outputs)
        self.get_edge_lists()
        self.pad_cuts()
        # a bit of convenience for users
        self.output_names = [o[1] for o in self.outputs]
        self.cut_names = [c[2] for c in self.cuts]

    def remove_cuts_from_chain(self, chain, cuts):
        """Remove chain items if they are the parent of a cut. Otherwise this leads to unintended LCIA results.

        """
        for cut in cuts:
            if cut[0] in chain:
                chain.remove(cut[0])
                print "PSS WARNING: Cut removed from chain: " + str(cut[0])
        return set(chain)

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
        return list(heads), isSimple

    def pad_outputs(self, outputs):
        """If not present, add to outputs default
        - name
        - amount (1)

        Args:
            * *outputs* (list): outputs

        Returns:
            Padded outputs

        """
        padded_outputs = []
        for i, output in enumerate(outputs):  # add default name and quantity if necessary
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
        reverse_mapping = dict(*[zip(itertools.count(), sorted(chain))])

        # MATRIX (that relates to processes in the chain)
        # Diagonal values (usually 1, but there are exceptions)
        M = len(chain)
        matrix = np.zeros((M, M))
        for m in range(M):
            key = reverse_mapping[m]
            if key in self.scaling_activities and not self.output_based_scaling:
                print "Did not apply output based scaling: scaling activity set to 1.0, " \
                      "which may not relate to manually defined output product quantities."
                diagonal_value = 1.0
            else:
                try:
                    ds = Database(key[0]).load()[key]
                    # amount does not work for ecoinvent 2.2 multioutput as co-products are not in exchanges
                    diagonal_value = [exc.get('amount', '') for exc in ds['exchanges'] if exc['type'] == "production"][0]
                except IndexError:
                    print "WARNING: Amount could not be determined. Perhaps this is a multi-output activity. " \
                          "Results may be wrong."
                    diagonal_value = 1.0
            matrix[m,m] = diagonal_value
        # Non-diagonal values
        # Only add edges that are within our system, but allow multiple links to same product (simply add them)
        for in_, out_, a in [x for x in edges if x[0] in chain and x[1] in chain]:
            matrix[
                mapping[in_],
                mapping[out_]
            ] -= a
        # DEMAND VECTOR
        demand = np.zeros((M,))
        for sa in scaling_activities:
            if not self.output_based_scaling:
                demand[mapping[sa]] = 1.0
            else:
                for o in [output for output in outputs if output[0] == sa]:
                    demand[mapping[sa]] += o[2]
        return mapping, demand, matrix, np.linalg.solve(matrix, demand).tolist()

    def get_edge_lists(self):
        """Get lists of external and internal edges with original flow values or scaled to the meta-process"""
        self.external_edges = \
            [x for x in self.edges if (x[0] not in self.chain and x[:2] not in set([y[:2] for y in self.cuts]))]
        self.internal_edges = \
            [x for x in self.edges if (x[0] in self.chain and x[:2] not in set([y[:2] for y in self.cuts]))]
        self.internal_edges_with_cuts = \
            [x for x in self.edges if (x[0] in self.chain or x[:2] in set([y[:2] for y in self.cuts]))]
        # scale these edges
        self.external_scaled_edges = \
            [(x[0], x[1], x[2] * self.supply_vector[self.mapping[x[1]]]) for x in self.external_edges]
        self.internal_scaled_edges = \
            [(x[0], x[1], x[2] * self.supply_vector[self.mapping[x[1]]]) for x in self.internal_edges]
        self.internal_scaled_edges_with_cuts = \
            [(x[0], x[1], x[2] * self.supply_vector[self.mapping[x[1]]]) for x in self.internal_edges_with_cuts]

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

    # METHODS THAT RETURN META-PROCESS DATA

    @property
    def mp_data(self):
        mp_data_dict = {
            'name': self.name,
            'outputs': self.outputs,
            'chain': list(self.chain),
            'cuts': self.cuts,
            'output_based_scaling': self.output_based_scaling,
        }
        return mp_data_dict

    def get_product_inputs_and_outputs(self):
        return [(cut[2], -cut[3]) for cut in self.cuts] + [(output[1], output[2]) for output in self.outputs]

    @property
    def pp(self):
        """Shortcut, as full method uses no global state"""
        return self.get_product_inputs_and_outputs()

    # LCA

    def get_background_lci_demand(self, foreground_amount):
        demand = {}  # dictionary for the brightway2 LCA object {activity key: amount}
        for sa in self.scaling_activities:
            demand.update({sa: self.demand[self.mapping[sa]]*foreground_amount})
        for cut in self.cuts:
            demand.update({cut[0]: -cut[3]*foreground_amount})
        return demand

    def lca(self, method, amount=1.0, factorize=False):
        if not self.scaling_activities:
            raise ValueError("No scaling activity")
        if hasattr(self, "calculated_lca"):
            self.calculated_lca.method = method
            self.calculated_lca.lcia()
        else:
            demand = self.get_background_lci_demand(amount)
            self.calculated_lca = LCA(demand, method=method)
            self.calculated_lca.lci()
            if factorize:
                self.calculated_lca.decompose_technosphere()
            self.calculated_lca.lcia()
        return self.calculated_lca.score

    def lci(self, amount=1.0):
        if not self.scaling_activities:
            raise ValueError("No scaling activity")
        demand = self.get_background_lci_demand(amount)
        self.calculated_lca = LCA(demand={self.key: amount})
        return self.calculated_lca.lci()

    # SAVE AS REGULAR ACTIVITY

    def save_as_bw2_dataset(self, db_name="MP default", unit=None,
            location=None, categories=[], save_aggregated_inventory=False):
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
        # GATHER DATASET INFORMATION
        self.key = (unicode(db_name), unicode(uuid.uuid4().urn[9:]))
        activity = self.scaling_activities[0]
        metadata = Database(activity[0]).load()[activity]
        # unit: if all scaling activities have the same unit, then set a unit, otherwise 'several'
        if self.scaling_activities != 1:
            units_set = set([Database(sa[0]).load()[sa].get(u'unit', '') for sa in self.scaling_activities])
            if len(units_set) > 1:
                unit = 'several'  # if several units, display nothing
            else:
                unit = units_set.pop()
        # EXCHANGES
        exchanges = []
        if not save_aggregated_inventory:  # save inventory as scaling activities - cuts
            # scaling activities
            for sa in self.scaling_activities:
                exchanges.append({
                    "amount": self.demand[self.mapping[sa]],
                    "input": sa,
                    "type": "biosphere" if sa[0] in (u"biosphere", u"biosphere3") else "technosphere",
                })
            # cuts
            for cut in self.cuts:
                exchanges.append({
                    "amount": -cut[3],
                    "input": cut[0],
                    "type": "biosphere" if cut[0] in (u"biosphere", u"biosphere3") else "technosphere",
                })
        else:  # save aggregated inventory of all processes in chain
            exchanges = [{
                "amount": exc[2],
                "input": exc[0],
                "type": "biosphere" if exc[0][0] in (u"biosphere", u"biosphere3") else "technosphere",
            } for exc in self.external_scaled_edges]
        # Production amount
        exchanges.append({
            # Output value unless several outputs, then 1.0
            "amount": self.outputs[0][2] if len(self.outputs) == 1 else 1.0,
            "input": self.key,
            "type": "production"
        })
        # WRITE DATASET INFORMATION
        data[self.key] = {
            "name": self.name,
            "unit": unit or metadata.get(u'unit', ''),
            "location": location or metadata.get(u'location', ''),
            "categories": categories,
            "type": "process",
            "exchanges": exchanges,
        }

        # TODO: Include uncertainty from original databases. Can't just scale
        # uncertainty parameters. Maybe solution is to use "dummy" processes
        # like we want to do to separate inputs of same flow in any case.
        # data = db.relabel_data(data, db_name)
        db.write(recursive_str_to_unicode(data))
        db.process()
