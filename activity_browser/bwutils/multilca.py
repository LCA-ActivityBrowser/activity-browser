# -*- coding: utf-8 -*-
from typing import Iterable, Optional, Union
from PySide2.QtWidgets import QMessageBox, QApplication
import numpy as np
import pandas as pd
import brightway2 as bw
from bw2analyzer import ContributionAnalysis

ca = ContributionAnalysis()

from .commontasks import wrap_text
from .metadata import AB_metadata
from .errors import ReferenceFlowValueError


class MLCA(object):
    """Wrapper class for performing LCA calculations with many reference flows and impact categories.

    Needs to be passed a brightway ``calculation_setup`` name.

    This class does not subclass the `LCA` class, and performs all
    calculations upon instantiation.

    Initialization creates `self.lca_scores`, which is a NumPy array
    of LCA scores, with rows of reference flows and columns of impact categories.
    Ordering is the same as in the `calculation_setup`.

    This class is adapted from `bw2calc.multi_lca.MultiLCA` and includes a
    number of additional attributes required to perform process- and
    elementary flow contribution analysis (see class `Contributions` below).

    Parameters
    ----------
    cs_name : str
        Name of the calculation setup

    Attributes
    ----------
    func_units_dict
    all_databases
    lca_scores_normalized
    func_units: list
        List of dictionaries, each containing the reference flow key and
        its required output
    fu_activity_keys: list
        The reference flow keys
    fu_index: dict
        Links the reference flows to a specific index
    rev_fu_index: dict
        Same as `fu_index` but using the indexes as keys
    methods: list
        The impact categories of the calculation setup
    method_index: dict
        Links the impact categories to a specific index
    rev_method_index: dict
        Same as `method_index` but using the indexes as keys
    lca: `bw2calc.lca.LCA`
        Brightway LCA instance used to perform LCA, LCI and LCIA
        calculations
    method_matrices: list
        Contains the characterization matrix for each impact category.
    lca_scores: `numpy.ndarray`
        2-dimensional array of shape (`func_units`, `methods`) holding the
        calculated LCA scores of each combination of reference flow and
        impact assessment method
    rev_activity_dict: dict
        See `bw2calc.lca.LCA.reverse_dict`
    rev_product_dict: dict
        See `bw2calc.lca.LCA.reverse_dict`
    rev_biosphere_dict: dict
        See `bw2calc.lca.LCA.reverse_dict`
    scaling_factors: dict
        Contains the life-cycle inventory scaling factors per reference flow
    technosphere_flows: dict
        Contains the calculated technosphere flows per reference flow
    inventory: dict
        Life cycle inventory (biosphere flows) per reference flow
    inventories: dict
        Biosphere flows per reference flow and impact category combination
    characterized_inventories: dict
        Inventory multiplied by scaling (relative impact on environment) per
        reference flow and impact category combination
    elementary_flow_contributions: `numpy.ndarray`
        3-dimensional array of shape (`func_units`, `methods`, `biosphere`)
        which holds the characterized inventory results summed along the
        technosphere axis
    process_contributions: `numpy.ndarray`
        3-dimensional array of shape (`func_units`, `methods`, `technosphere`)
        which holds the characterized inventory results summed along the
        biosphere axis
    func_unit_translation_dict: dict
        Contains the reference flow key and its expected output linked to
        the brightway activity label.
    func_key_dict: dict
        An index of the brightway activity labels
    func_key_list: list
        A derivative of `func_key_dict` containing just the keys

    Raises
    ------
    ValueError
        If the given `cs_name` cannot be found in brightway calculation_setups

    """
    def __init__(self, cs_name: str):
        try:
            cs = bw.calculation_setups[cs_name]
        except KeyError:
            raise ValueError(
                "{} is not a known `calculation_setup`.".format(cs_name)
            )

        if sum([v for rf in cs['inv'] for v in rf.values()]) == 0:
            msg = QMessageBox()
            msg.setText('Sum of reference flows equals 0')
            msg.setInformativeText('A value greater than 0 must be provided for at least one reference flow.\n' +
                                   'Please enter a valid value before calculating LCA results again.')
            msg.setIcon(QMessageBox.Warning)
            QApplication.restoreOverrideCursor()
            msg.exec_()
            raise ReferenceFlowValueError("Sum of reference flows == 0")

        # reference flows and related indexes
        self.func_units = cs['inv']
        self.fu_activity_keys = [list(fu.keys())[0] for fu in self.func_units]
        self.fu_index = {k: i for i, k in enumerate(self.fu_activity_keys)}
        self.rev_fu_index = {v: k for k, v in self.fu_index.items()}

        # Methods and related indexes
        self.methods = cs['ia']
        self.method_index = {m: i for i, m in enumerate(self.methods)}
        self.rev_method_index = {v: k for k, v in self.method_index.items()}

        # initial LCA and prepare method matrices
        self.lca = self._construct_lca()
        self.lca.lci(factorize=True)
        self.method_matrices = []
        for method in self.methods:
            self.lca.switch_method(method)
            self.method_matrices.append(self.lca.characterization_matrix)

        self.lca_scores = np.zeros((len(self.func_units), len(self.methods)))

        # data to be stored
        (self.rev_activity_dict, self.rev_product_dict, self.rev_biosphere_dict) = self.lca.reverse_dict()

        # Scaling
        self.scaling_factors = dict()

        # Technosphere product flows for a given reference flow
        self.technosphere_flows = dict()
        # Life cycle inventory (biosphere flows) by reference flow
        self.inventory = dict()
        # Inventory (biosphere flows) for specific reference flow (e.g. 2000x15000) and impact category.
        self.inventories = dict()
        # Inventory multiplied by scaling (relative impact on environment) per impact category.
        self.characterized_inventories = dict()

        # Summarized contributions for EF and processes.
        self.elementary_flow_contributions = np.zeros(
            (len(self.func_units), len(self.methods), self.lca.biosphere_matrix.shape[0]))
        self.process_contributions = np.zeros(
            (len(self.func_units), len(self.methods), self.lca.technosphere_matrix.shape[0]))

        # TODO: get rid of the below
        self.func_unit_translation_dict = {
            str(bw.get_activity(list(func_unit.keys())[0])): func_unit for func_unit in self.func_units
        }
        if len(self.func_unit_translation_dict) != len(self.func_units):
            self.func_unit_translation_dict = {}
            for fu in self.func_units:
                act = bw.get_activity(next(iter(fu)))
                self.func_unit_translation_dict["{} {}".format(act, act[0])] = fu
        self.func_key_dict = {m: i for i, m in enumerate(self.func_unit_translation_dict.keys())}
        self.func_key_list = list(self.func_key_dict.keys())

    def _construct_lca(self):
        return bw.LCA(demand=self.func_units_dict, method=self.methods[0])

    def _perform_calculations(self):
        """ Isolates the code which performs calculations to allow subclasses
        to either alter the code or redo calculations after matrix substitution.
        """
        for row, func_unit in enumerate(self.func_units):
            # Do the LCA for the current reference flow
            self.lca.redo_lci(func_unit)

            # Now update the:
            # - Scaling factors
            # - Technosphere flows
            # - Life cycle inventory
            # - Life-cycle inventory (disaggregated by contributing process)
            # for current reference flow
            self.scaling_factors.update({
                str(func_unit): self.lca.supply_array
            })
            self.technosphere_flows.update({
                str(func_unit): np.multiply(self.lca.supply_array, self.lca.technosphere_matrix.diagonal())
            })
            self.inventory.update({
                str(func_unit): np.array(self.lca.inventory.sum(axis=1)).ravel()
            })
            self.inventories.update({
                str(func_unit): self.lca.inventory
            })

            # Now, for each method, take the current reference flow and do inventory analysis
            for col, cf_matrix in enumerate(self.method_matrices):
                self.lca.characterization_matrix = cf_matrix
                self.lca.lcia_calculation()
                self.lca_scores[row, col] = self.lca.score
                self.characterized_inventories[row, col] = self.lca.characterized_inventory.copy()
                self.elementary_flow_contributions[row, col] = np.array(
                    self.lca.characterized_inventory.sum(axis=1)).ravel()
                self.process_contributions[row, col] = self.lca.characterized_inventory.sum(axis=0)

    def calculate(self):
        self._perform_calculations()

    @property
    def func_units_dict(self) -> dict:
        """Return a dictionary of reference flow (key, demand)."""
        return {key: 1 for func_unit in self.func_units for key in func_unit}

    @property
    def all_databases(self) -> set:
        """ Get all databases linked to the reference flows.
        """
        def get_dependents(dbs: set, dependents: list) -> set:
            for dep in (bw.databases[db].get('depends', []) for db in dependents):
                if not dbs.issuperset(dep):
                    dbs = get_dependents(dbs.union(dep), dep)
            return dbs

        databases = set(f[0] for f in self.fu_activity_keys)
        databases = get_dependents(databases, list(databases))
        # In rare cases, the default biosphere is not found as a dependency, see:
        # https://github.com/LCA-ActivityBrowser/activity-browser/issues/298
        # Always include it.
        databases.add(bw.config.biosphere)
        return databases

    def get_results_for_method(self, index: int = 0) -> pd.DataFrame:
        data = self.lca_scores[:, index]
        return pd.DataFrame(data, index=self.fu_activity_keys)

    @property
    def lca_scores_normalized(self) -> np.ndarray:
        """Normalize LCA scores by impact assessment method.
        """
        return self.lca_scores / self.lca_scores.max(axis=0)

    def get_normalized_scores_df(self) -> pd.DataFrame:
        """ To be used for the currently inactive CorrelationPlot.
        """
        labels = [str(x + 1) for x in range(len(self.func_units))]
        return pd.DataFrame(data=self.lca_scores_normalized.T, columns=labels)

    def lca_scores_to_dataframe(self) -> pd.DataFrame:
        """Returns a dataframe of LCA scores using FU labels as index and
        methods as columns.
        """
        return pd.DataFrame(
            data=self.lca_scores,
            index=pd.Index(self.fu_activity_keys),
            columns=pd.Index(self.methods),
        )

    def get_all_metadata(self) -> None:
        """Populate AB_metadata with relevant database values.

        Set metadata in form of a Pandas DataFrame for biosphere and
        technosphere databases for tables and additional aggregation.
        """
        AB_metadata.add_metadata(self.all_databases)


class Contributions(object):
    """Contribution Analysis built on top of the Multi-LCA class.

    This class requires instantiated MLCA and MetaDataStore objects.

    Parameters
    ----------
    mlca : `MLCA`
        An instantiated MLCA object

    Attributes
    ----------
    DEFAULT_ACT_FIELDS : list
        Default activity/reference flow column names
    DEFAULT_EF_FIELDS : list
        Default environmental flow column names
    mlca: `MLCA`
        Linked `MLCA` instance used for contribution calculations
    act_fields: list
        technosphere-specific metadata column names
    ef_fields: list
        biosphere-specific metadata column names

    Raises
    ------
    ValueError
        If the given `mlca` object is not an instance of `MLCA`

    """
    ACT = "process"
    EF = "elementary_flow"
    TECH = "technosphere"
    BIOS = "biosphere"

    DEFAULT_ACT_FIELDS = ['reference product', 'name', 'location', 'unit', 'database']
    DEFAULT_EF_FIELDS = ['name', 'categories', 'type', 'unit', 'database']

    DEFAULT_ACT_AGGREGATES = ['none'] + DEFAULT_ACT_FIELDS
    DEFAULT_EF_AGGREGATES = ['none'] + DEFAULT_EF_FIELDS

    def __init__(self, mlca):
        if not isinstance(mlca, MLCA):
            raise ValueError('Must pass an MLCA object. Passed:', type(mlca))
        self.mlca = mlca
        # Ensure MetaDataStore is updated.
        self.mlca.get_all_metadata()

        # Set default metadata keys (those not in the dataframe will be eliminated)
        self.act_fields = AB_metadata.get_existing_fields(self.DEFAULT_ACT_FIELDS)
        self.ef_fields = AB_metadata.get_existing_fields(self.DEFAULT_EF_FIELDS)

        # Specific datastructures for retrieving relevant MLCA data
        # inventory: inventory, reverse index, metadata keys, metadata fields
        self.inventory_data = {
            "biosphere": (self.mlca.inventory, self.mlca.rev_biosphere_dict,
                          self.mlca.fu_activity_keys, self.ef_fields),
            "technosphere": (self.mlca.technosphere_flows, self.mlca.rev_activity_dict,
                             self.mlca.fu_activity_keys, self.act_fields),
        }
        # aggregation: reverse index, metadata keys, metadata fields
        self.aggregate_data = {
            "biosphere": (self.mlca.rev_biosphere_dict, self.mlca.lca.biosphere_dict, self.ef_fields),
            "technosphere": (self.mlca.rev_activity_dict, self.mlca.lca.activity_dict, self.act_fields),
        }

    def normalize(self, contribution_array):
        """Normalise the contribution array.

        Parameters
        ----------
        contribution_array : `numpy.ndarray`
            A 2-dimensional contribution array

        Returns
        -------
        `numpy.ndarray`
            2-dimensional array of same shape, with scores normalized.

        """
        scores = abs(contribution_array).sum(axis=1, keepdims=True)
        return contribution_array / scores

    def _build_dict(self, C, FU_M_index, rev_dict, limit, limit_type):
        """Sort the given contribution array on method or reference flow column.

        Parameters
        ----------
        C : `numpy.ndarray`
            A 2-dimensional contribution array
        FU_M_index : dict
            Dictionary which maps the reference flows or methods to their
            matching columns
        rev_dict : dict
            'reverse' dictionary used to map correct activity/method to
            its value
        limit : int
            Number of top-contributing items to include
        limit_type : str
            Either "number" or "percent", ContributionAnalysis.sort_array
            for complete explanation

        Returns
        -------
        dict
            Top-contributing flows per method or activity

        """
        topcontribution_dict = dict()
        for fu_or_method, col in FU_M_index.items():
            top_contribution = ca.sort_array(C[col, :], limit=limit, limit_type=limit_type)
            cont_per = dict()
            cont_per.update({
                ('Total', ''): C[col, :].sum(),
                ('Rest', ''): C[col, :].sum() - top_contribution[:, 0].sum(),
                })
            for value, index in top_contribution:
                cont_per.update({rev_dict[index]: value})
            topcontribution_dict.update({fu_or_method: cont_per})
        return topcontribution_dict


    @staticmethod
    def get_labels(key_list, fields=None, separator=' | ',
                   max_length=False, mask=None):
        """Generate labels from metadata information.

        Setting max_length will wrap the label into a multi-line string if
        size is larger than max_length.

        Parameters
        ----------
        key_list : `pandas.MultiIndex`
            An index containing 'keys' to be retrieved from the MetaDataStore
        fields : list
            List of column-names to be included from the MetaDataStore
        separator : str
            Specific separator to use when joining strings together
        max_length : int
            Allowed character length before string is wrapped over multiple
            lines
        mask : list
            Instead of the metadata, this list is used to check keys against.
            Use if data is aggregated or keys do not exist in MetaDataStore

        Returns
        -------
        list
            Translated and/or joined (and wrapped) labels matching the keys

        """
        fields = fields if fields else ['name', 'reference product', 'location', 'database']
        keys = (k for k in key_list)  # need to do this as the keys come from a pd.Multiindex
        translated_keys = []
        for k in keys:
            if mask and k in mask:
                translated_keys.append(k)
            elif isinstance(k, str):
                translated_keys.append(k)
            elif k in AB_metadata.index:
                translated_keys.append(separator.join([str(l) for l in list(AB_metadata.get_metadata(k, fields))]))
            else:
                translated_keys.append(separator.join([i for i in k if i != '']))
        if max_length:
            translated_keys = [wrap_text(k, max_length=max_length) for k in translated_keys]
        return translated_keys

    @classmethod
    def join_df_with_metadata(cls, df, x_fields=None, y_fields=None,
                              special_keys=None):
        """Join a dataframe that has keys on the index with metadata.

        Metadata fields are defined in x_fields.
        If columns are also keys (and not, e.g. method names), they can also
        be replaced with metadata, if y_fields are provided.

        Parameters
        ----------
        df : `pandas.DataFrame`
            Simple DataFrame containing processed data
        x_fields : list
            List of additional columns to add from the MetaDataStore
        y_fields : list
            List of column keys for the data in the df dataframe
        special_keys : list
            List of specific items to place at the top of the dataframe

        Returns
        -------
        `pandas.DataFrame`
            Expanded and metadata-annotated dataframe

        """

        # replace column keys with labels
        df.columns = cls.get_labels(df.columns, fields=y_fields)#, separator='\n')
        # Coerce index to MultiIndex if it currently isn't
        if not isinstance(df.index, pd.MultiIndex):
            df.index = pd.MultiIndex.from_tuples(df.index)

        # get metadata for rows
        keys = [k for k in df.index if k in AB_metadata.index]
        metadata = AB_metadata.get_metadata(keys, x_fields)

        # join data with metadata
        joined = metadata.join(df, how='outer')

        if special_keys:
            # replace index keys with labels
            try:  # first put Total and Rest to the first two positions in the dataframe
                complete_index = special_keys + keys
                joined = joined.reindex(complete_index, axis="index", fill_value=0.)
            except:
                print('Could not put Total and Rest on positions 0 and 1 in the dataframe.')
        joined.index = cls.get_labels(joined.index, fields=x_fields)
        return joined

    def get_labelled_contribution_dict(self, cont_dict, x_fields=None,
                                       y_fields=None, mask=None):
        """Annotate the contribution dict with metadata.

        Parameters
        ----------
        cont_dict : dict
            Holds the contribution data connected to the functions of methods
        x_fields : list
            X-axis fieldnames, these are usually the indexes/keys of specific
            processes
        y_fields : list
            Column names specific to the cont_dict to be labelled
        mask : list
            Used in case of aggregation or special cases where the usual
            way of using the metadata cannot be used

        Returns
        -------
        `pandas.DataFrame`
            Annotated contribution dict inside a pandas dataframe

        """
        dfs = (
            pd.DataFrame(v.values(), index=list(v.keys()), columns=[k])
            for k, v in cont_dict.items()
        )
        df = pd.concat(dfs, sort=False, axis=1)
        # If the cont_dict has tuples for keys, coerce df.columns into MultiIndex
        if all(isinstance(k, tuple) for k in cont_dict.keys()):
            df.columns = pd.MultiIndex.from_tuples(df.columns)
        special_keys = [('Total', ''), ('Rest', '')]

        # replace all 0 values with NaN and drop all rows with only NaNs
        df = df.replace(0, np.nan).dropna(how='all')

        if not mask:
            joined = self.join_df_with_metadata(
                df, x_fields=x_fields, y_fields=y_fields,
                special_keys=special_keys
            )
        else:
            df.columns = self.get_labels(df.columns, fields=y_fields)
            keys = [k for k in df.index if k in mask]
            combined_keys = special_keys + keys
            # Reindex the combined_keys to ensure they always exist in the dataframe,
            # this avoids keys with 0 values not existing due to the 'dropna' action above.
            df = df.reindex(combined_keys, axis="index", fill_value=0.0)
            df.index = self.get_labels(df.index, mask=mask)
            joined = df

        return joined.reset_index(drop=False)

    @staticmethod
    def adjust_table_unit(df: pd.DataFrame, method: Optional[tuple]) -> pd.DataFrame:
        """Given a dataframe, adjust the unit of the table to either match the
        given method, or not exist.
        """
        if "unit" not in df.columns:
            return df
        keys = df.index[~df["index"].isin({"Total", "Rest"})]
        unit = bw.Method(method).metadata.get("unit") if method else "unit"
        df.loc[keys, "unit"] = unit
        return df

    @staticmethod
    def _build_inventory(inventory: dict, indices: dict, columns: list,
                         fields: list) -> pd.DataFrame:
        df = pd.DataFrame(inventory)
        df.index = pd.MultiIndex.from_tuples(indices.values())
        df.columns = Contributions.get_labels(columns, max_length=30)
        metadata = AB_metadata.get_metadata(list(indices.values()), fields)
        joined = metadata.join(df)
        joined.reset_index(inplace=True, drop=True)
        return joined

    def inventory_df(self, inventory_type: str, columns: set = {'name', 'database', 'code'}):
        """Returns an inventory dataframe with metadata of the given type.
        """
        try:
            data = self.inventory_data[inventory_type]
            appending = columns.difference(set(data[3]))
            for clmn in appending:
                data[3].append(clmn)
        except KeyError:
            raise ValueError(
                "Type must be either 'biosphere' or 'technosphere', "
                "'{}' given.".format(inventory_type)
            )
        return self._build_inventory(*data)

    def _build_lca_scores_df(self, scores: np.ndarray) -> pd.DataFrame:
        df = pd.DataFrame(
            scores,
            index=pd.MultiIndex.from_tuples(self.mlca.fu_activity_keys),
            columns=self.mlca.methods
        )
        # Add amounts column.
        df["amount"] = [next(iter(fu.values()), 1.0) for fu in self.mlca.func_units]
        joined = Contributions.join_df_with_metadata(
            df, x_fields=self.act_fields, y_fields=None
        )
        # Precisely order the columns that are shown in the LCA Results overview
        # tab: “X kg of product Y from activity Z in location L, and database D”
        col_order = pd.Index([
            "amount", "unit", "reference product", "name", "location", "database",
        ])
        methods = joined.columns.difference(col_order, sort=False)
        joined = joined.loc[:, col_order.append(methods)]
        return joined.reset_index(drop=False)

    def lca_scores_df(self, normalized=False) -> pd.DataFrame:
        """Returns a metadata-annotated DataFrame of the LCA scores.
        """
        scores = self.mlca.lca_scores if not normalized else self.mlca.lca_scores_normalized
        return self._build_lca_scores_df(scores)

    @staticmethod
    def _build_contributions(data: np.ndarray, index: int, axis: int) -> np.ndarray:
        return data.take(index, axis=axis)

    def get_contributions(self, contribution, functional_unit=None,
                          method=None) -> np.ndarray:
        """Return a contribution matrix given the type and fu / method
        """
        if all([functional_unit, method]) or not any([functional_unit, method]):
            raise ValueError(
                "It must be either by reference flow or by impact category. Provided:"
                "\n Reference flow: {} \n Impact Category: {}".format(functional_unit, method)
            )
        dataset = {
            'process': self.mlca.process_contributions,
            'elementary_flow': self.mlca.elementary_flow_contributions,
        }
        if method:
            return self._build_contributions(
                dataset[contribution], self.mlca.method_index[method], 1
            )
        elif functional_unit:
            return self._build_contributions(
                dataset[contribution], self.mlca.func_key_dict[functional_unit], 0
            )

    def aggregate_by_parameters(self, C: np.ndarray, inventory: str,
                                parameters: Union[str, list] = None):
        """Perform aggregation of the contribution data given parameters

        Parameters
        ----------
        C : `numpy.ndarray`
            2-dimensional contribution array
        inventory: str
            Either 'biosphere' or 'technosphere', used to determine which
            inventory to use
        parameters : str or list
            One or more parameters by which to aggregate the given contribution
            array.

        Returns
        -------
        `numpy.ndarray`
            The aggregated 2-dimensional contribution array
        mask_index : dict
            Contains all of the values of the aggregation mask, linked to
            their indexes
        mask : list or dictview or None
            An optional list or dictview of the mask_index values

        -------

        """
        rev_index, keys, fields = self.aggregate_data[inventory]
        if not parameters:
            return C, rev_index, None

        df = pd.DataFrame(C).T
        columns = list(range(C.shape[0]))
        df.index = pd.MultiIndex.from_tuples(rev_index.values())
        metadata = AB_metadata.get_metadata(list(keys), fields)

        joined = metadata.join(df)
        joined.reset_index(inplace=True, drop=True)
        grouped = joined.groupby(parameters)
        aggregated = grouped[columns].sum()
        mask_index = {i: m for i, m in enumerate(aggregated.index)}

        return aggregated.T.values, mask_index, mask_index.values()

    def _contribution_rows(self, contribution: str, aggregator=None):
        if aggregator is None:
            return self.act_fields if contribution == self.ACT else self.ef_fields
        return aggregator if isinstance(aggregator, list) else [aggregator]

    def _correct_method_index(self, mthd_indx):
        """ A method for amending the tuples for impact method labels so
        that all tuples are fully printed.

        NOTE THE AMENDED TUPLES ARE COPIED, THIS SHOULD NOT BE USED TO
        ASSIGN OR MODIFY THE UNDERLYING DATA STRUCTURES!

        mthd_indx: a list of tuples for the impact method names
        """
        method_tuple_length = max([len(k) for k in mthd_indx])
        conv_dict = dict()
        for v, mthd in enumerate(mthd_indx):
            if len(mthd) < method_tuple_length:
                _l = list(mthd)
                for i in range(len(mthd), method_tuple_length):
                    _l.append('')
                mthd = tuple(_l)
            conv_dict[mthd] = v
        return conv_dict

    def _contribution_index_cols(self, **kwargs) -> (dict, Optional[Iterable]):
        if kwargs.get("method") is not None:
            return self.mlca.fu_index, self.act_fields
        return self._correct_method_index(self.mlca.methods), None

    def top_elementary_flow_contributions(self, functional_unit=None, method=None,
                                          aggregator=None, limit=5, normalize=False,
                                          limit_type="number", **kwargs):
        """Return top EF contributions for either functional_unit or method.

        * If functional_unit: Compare the unit against all considered impact
        assessment methods.
        * If method: Compare the method against all involved processes.

        Parameters
        ----------
        functional_unit : tuple, optional
            The reference flow to compare all considered impact categories against
        method : tuple, optional
            The method to compare all considered reference flows against
        aggregator : str or list, optional
            Used to aggregate EF contributions over certain columns
        limit : int
            The number of top contributions to consider
        normalize : bool
            Determines whether or not to normalize the contribution values
        limit_type : str
            The type of limit, either 'number' or 'percent'


        Returns
        -------
        `pandas.DataFrame`
            Annotated top-contribution dataframe

        """
        C = self.get_contributions(self.EF, functional_unit, method)

        x_fields = self._contribution_rows(self.EF, aggregator)
        index, y_fields = self._contribution_index_cols(
            functional_unit=functional_unit, method=method
        )
        C, rev_index, mask = self.aggregate_by_parameters(C, self.BIOS, aggregator)

        # Normalise if required
        if normalize:
            C = self.normalize(C)

        top_cont_dict = self._build_dict(C, index, rev_index, limit, limit_type)
        labelled_df = self.get_labelled_contribution_dict(
            top_cont_dict, x_fields=x_fields, y_fields=y_fields, mask=mask
        )
        self.adjust_table_unit(labelled_df, method)
        return labelled_df

    def top_process_contributions(self, functional_unit=None, method=None,
                                  aggregator=None, limit=5, normalize=False,
                                  limit_type="number", **kwargs):
        """Return top process contributions for functional_unit or method

        * If functional_unit: Compare the process against all considered impact
        assessment methods.
        * If method: Compare the method against all involved processes.

        Parameters
        ----------
        functional_unit : tuple, optional
            The reference flow to compare all considered methods against
        method : tuple, optional
            The method to compare all considered reference flows against
        aggregator : str or list, optional
            Used to aggregate PC contributions over certain columns
        limit : int
            The number of top contributions to consider
        normalize : bool
            Determines whether or not to normalize the contribution values
        limit_type : str
            The type of limit, either 'number' or 'percent'

        Returns
        -------
        `pandas.DataFrame`
            Annotated top-contribution dataframe

        """
        C = self.get_contributions(self.ACT, functional_unit, method)

        x_fields = self._contribution_rows(self.ACT, aggregator)
        index, y_fields = self._contribution_index_cols(
            functional_unit=functional_unit, method=method
        )
        C, rev_index, mask = self.aggregate_by_parameters(C, self.TECH, aggregator)

        # Normalise if required
        if normalize:
            C = self.normalize(C)

        top_cont_dict = self._build_dict(C, index, rev_index, limit, limit_type)
        labelled_df = self.get_labelled_contribution_dict(
            top_cont_dict, x_fields=x_fields, y_fields=y_fields, mask=mask
        )
        self.adjust_table_unit(labelled_df, method)
        return labelled_df

