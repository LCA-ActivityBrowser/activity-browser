# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import brightway2 as bw
from bw2analyzer import ContributionAnalysis
from brightway2 import get_activity

ca = ContributionAnalysis()

from .commontasks import wrap_text

class MLCA(object):
    # todo: update description
    # todo: add characterized inventories
    """Wrapper class for performing LCA calculations with many functional units and LCIA methods.

    Needs to be passed a ``calculation_setup`` name.

    This class does not subclass the `LCA` class, and performs all calculations upon instantiation.

    Initialization creates `self.lca_scores`, which is a NumPy array of LCA scores, with rows of functional units and columns of LCIA methods. Ordering is the same as in the `calculation_setup`.

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

        self.lca = bw.LCA(demand=self.func_units_dict, method=self.methods[0])
        self.lca.lci(factorize=True)
        self.method_matrices = []
        self.lca_scores = np.zeros((len(self.func_units), len(self.methods)))

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
                str(func_unit): np.array(self.lca.inventory.sum(axis=1)).ravel()
            })
            # the life cycle inventory disaggregated by contributing process
            self.inventories.update({
                str(func_unit): self.lca.inventory
            })

            for col, cf_matrix in enumerate(self.method_matrices):
                self.lca.characterization_matrix = cf_matrix
                self.lca.lcia_calculation()
                self.lca_scores[row, col] = self.lca.score
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
    def func_units_dict(self):
        """Return a dictionary of functional units (key, demand)."""
        return {key: 1 for func_unit in self.func_units for key in func_unit}

    @property
    def all_databases(self):
        """Get all databases linked to the functional units."""
        databases = list()
        for f in self.fu_activity_keys:
            databases.append(f[0])
            databases.append(*bw.databases[f[0]].get('depends', []))
        return set(databases)

    @property
    def lca_scores_normalized(self):
        return self.lca_scores / self.lca_scores.max(axis=0)

    def get_all_metadata(self):
        """Get metadata in form of a Pandas DataFrame for biosphere and technosphere databases
        for tables and additional aggregation.
        """
        print('Making metadata DataFrame.')
        dfs = []
        for db in self.all_databases:
            df_temp = pd.DataFrame(bw.Database(db))
            df_temp.index = pd.MultiIndex.from_tuples(zip(df_temp['database'], df_temp['code']))
            dfs.append(df_temp)
        self.df_meta = pd.concat(dfs, sort=False)


class Contributions(object):
    """Contribution Analysis built on top of the Multi-LCA class."""
    def __init__(self, mlca):
        if not isinstance(mlca, MLCA):
            raise ValueError('Must pass an MLCA object. Passed:', type(mlca))
        self.mlca = mlca
        self.act_fields = ['reference product', 'name', 'location']
        self.ef_fields = ['name', 'categories', 'type', 'unit']

    def normalize(self, contribution_array):
        """ Normalise the contribution array. """
        scores = contribution_array.sum(axis=1)
        return (contribution_array / scores[:, np.newaxis])

    def build_dict(self, C, FU_M_index, rev_dict, limit, limit_type):
        """ Sort each method or functional unit column independently. """
        topcontribution_dict = {}
        for fu_or_method, col in FU_M_index.items():
            top_contribution = ca.sort_array(C[col, :], limit=limit, limit_type=limit_type)
            cont_per = {}
            cont_per.update({
                ('Rest', ''): C[col, :].sum() - top_contribution[:, 0].sum(),
                ('Total', ''): C[col, :].sum(),
                })
            for value, index in top_contribution:
                cont_per.update({rev_dict[index]: value})
            topcontribution_dict.update({fu_or_method: cont_per})
        return topcontribution_dict

    def get_labels(self, df_meta, key_list, fields=['name', 'reference product', 'location', 'database'],
                   separator=' | ', max_length=False):
        keys = [k for k in key_list]  # need to do this as the keys come from a pd.Multiindex
        translated_keys = []
        for k in keys:
            if k in df_meta.index:
                translated_keys.append(separator.join([str(l) for l in list(df_meta.loc[k][fields])]))
            else:
                translated_keys.append(separator.join([i for i in k if i != '']))
        if max_length:
            translated_keys = [wrap_text(k, max_length=max_length) for k in translated_keys]
        return translated_keys

    def get_labelled_contribution_dict(self, cont_dict, x_fields=None, y_fields=None):
        if not hasattr(self.mlca, 'df_meta'):
            self.mlca.get_all_metadata()
        df = pd.DataFrame(cont_dict)

        # replace column keys with labels
        df.columns = self.get_labels(self.mlca.df_meta, df.columns, fields=y_fields, separator='\n')

        # get metadata for rows
        keys = [k for k in df.index if k in self.mlca.df_meta.index]
        metadata = self.mlca.df_meta.loc[keys][x_fields]

        # join data with metadata
        joined = metadata.join(df, how='outer')

        # replace index keys with labels
        joined.index = self.get_labels(self.mlca.df_meta, joined.index, fields=x_fields)
        joined = joined.reset_index()
        return joined

    def inventory_df(self, type='biosphere'):
        if type == 'biosphere':
            fields = ["name", "categories", "unit", "database"]
            df = pd.DataFrame(self.mlca.inventory)
            df.index = pd.MultiIndex.from_tuples(self.mlca.rev_biosphere_dict.values())
            df.columns = self.get_labels(self.mlca.df_meta, self.mlca.fu_activity_keys, max_length=30)
            metadata = self.mlca.df_meta.loc[list(self.mlca.rev_biosphere_dict.values())][fields]
            joined = metadata.join(df)
            joined.reset_index(inplace=True, drop=True)
        elif type == 'technosphere':
            fields = ["reference product", "name", "location", "database"]
            df = pd.DataFrame(self.mlca.technosphere_flows)
            df.index = pd.MultiIndex.from_tuples(self.mlca.rev_activity_dict.values())
            df.columns = self.get_labels(self.mlca.df_meta, self.mlca.fu_activity_keys, max_length=30)
            metadata = self.mlca.df_meta.loc[list(self.mlca.rev_activity_dict.values())][fields]
            joined = metadata.join(df)
            joined.reset_index(inplace=True, drop=True)
        return joined

    def top_elementary_flow_contributions(self, functional_unit=None, method=None, limit=5, normalize=False,
                                  limit_type="number"):
        """ Return process contributions for either
            * for one impact assessment method and a number of processes or
            * for one process and a number of impact assessment methods. """
        if (functional_unit and method) or (not functional_unit and not method):
            raise ValueError(
                'It must be either by functional unit or by method. Provided: \n Functional unit: {} \n Method: {}'.format(
                    functional_unit, method))
        if method:
            C = self.mlca.elementary_flow_contributions[:, self.mlca.method_index[method], :]
        elif functional_unit:
            C = self.mlca.elementary_flow_contributions[self.mlca.func_key_dict[functional_unit], :, :]

        # Normalise if required
        if normalize:
            C = self.normalize(C)

        if method:
            top_cont_dict = self.build_dict(C, self.mlca.fu_index, self.mlca.rev_biosphere_dict, limit, limit_type)
            return self.get_labelled_contribution_dict(top_cont_dict, x_fields=self.ef_fields,
                                                       y_fields=self.act_fields)
        elif functional_unit:
            top_cont_dict = self.build_dict(C, self.mlca.method_index, self.mlca.rev_biosphere_dict, limit, limit_type)
            return self.get_labelled_contribution_dict(top_cont_dict, x_fields=self.ef_fields,
                                                       y_fields=None)

    def top_process_contributions(self, functional_unit=None, method=None, limit=5, normalize=False,
                                  limit_type="number"):
        """ Return process contributions for either
            * for one impact assessment method and a number of processes or
            * for one process and a number of impact assessment methods. """
        if (functional_unit and method) or (not functional_unit and not method):
            raise ValueError(
                'It must be either by functional unit or by method. Provided: \n Functional unit: {} \n Method: {}'.format(
                    functional_unit, method))
        if method:
            C = self.mlca.process_contributions[:, self.mlca.method_index[method], :]
        elif functional_unit:
            C = self.mlca.process_contributions[self.mlca.func_key_dict[functional_unit], :, :]

        # Normalise if required
        if normalize:
            C = self.normalize(C)

        if method:
            top_cont_dict = self.build_dict(C, self.mlca.fu_index, self.mlca.rev_activity_dict, limit, limit_type)
            return self.get_labelled_contribution_dict(top_cont_dict, x_fields=self.act_fields,
                                                       y_fields=self.act_fields)
        elif functional_unit:
            top_cont_dict = self.build_dict(C, self.mlca.method_index, self.mlca.rev_activity_dict, limit, limit_type)
            return self.get_labelled_contribution_dict(top_cont_dict, x_fields=self.act_fields,
                                                       y_fields=None)