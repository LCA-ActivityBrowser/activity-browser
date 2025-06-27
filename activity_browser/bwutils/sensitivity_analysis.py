# -*- coding: utf-8 -*-

# =============================================================================
# Global Sensitivity Analysis (GSA) functions and class for the Delta
# Moment-Independent measure based on Monte Carlo simulation LCA results.
# see: https://salib.readthedocs.io/en/latest/api.html#delta-moment-independent-measure
# =============================================================================
import os
import traceback
from time import time
from logging import getLogger

import bw2calc as bc
import numpy as np
import pandas as pd
from SALib.analyze import delta

from activity_browser.mod import bw2data as bd

from ..settings import ab_settings
from .montecarlo import MonteCarloLCA, perform_MonteCarlo_LCA

try:
    # attempt bw25 import
    from bw_graph_tools.graph_traversal import NewNodeEachVisitGraphTraversal
except ImportError:
    # standard import on failure
    from bw2calc import GraphTraversal


log = getLogger(__name__)


def get_lca(fu, method):
    """Calculates a non-stochastic LCA and returns a the LCA object."""
    lca = bc.LCA(fu, method=method)
    lca.lci()
    lca.lcia()
    log.info(f"Non-stochastic LCA score: {lca.score}")

    # add reverse dictionaries
    lca.activity_dict_rev, lca.product_dict_rev, lca.biosphere_dict_rev = (
        lca.reverse_dict()
    )

    return lca


def filter_technosphere_exchanges(fu, method, cutoff=0.05, max_calc=1000):
    """Use brightway's GraphTraversal to identify the relevant
    technosphere exchanges in a non-stochastic LCA."""
    start = time()
    res = NewNodeEachVisitGraphTraversal.calculate(fu, method, cutoff=cutoff, max_calc=int(max_calc))

    # get all edges
    technosphere_exchange_indices = []
    for e in res["edges"]:
        if e["to"] != -1:  # filter out head introduced in graph traversal
            technosphere_exchange_indices.append((e["from"], e["to"]))
    log.info(
        "TECHNOSPHERE {} filtering resulted in {} of {} exchanges and took {} iterations in {} seconds.".format(
            res["lca"].technosphere_matrix.shape,
            len(technosphere_exchange_indices),
            res["lca"].technosphere_matrix.getnnz(),
            res["counter"],
            np.round(time() - start, 2),
        )
    )
    return technosphere_exchange_indices


def filter_biosphere_exchanges(lca, cutoff=0.005):
    """Reduce biosphere exchanges to those that matter for a given impact
    category in a non-stochastic LCA."""
    start = time()

    inv = lca.characterized_inventory
    finv = inv.multiply(abs(inv) > abs(lca.score / (1 / cutoff)))
    biosphere_exchange_indices = list(zip(*finv.nonzero()))
    explained_fraction = finv.sum() / lca.score
    log.info(
        "BIOSPHERE {} filtering resulted in {} of {} exchanges ({}% of total impact) and took {} seconds.".format(
            inv.shape,
            finv.nnz,
            inv.nnz,
            np.round(explained_fraction * 100, 2),
            np.round(time() - start, 2),
        )
    )
    return biosphere_exchange_indices


def get_exchanges(lca, indices, biosphere=False, only_uncertain=True):
    """Get actual exchange objects from indices.
    By default get only exchanges that have uncertainties.

    Returns
    -------
    exchanges : list
        List of exchange objects
    indices : list of tuples
        List of indices
    """
    exchanges = list()
    for i in indices:
        if biosphere:
            from_act = bd.get_activity(lca.biosphere_dict_rev[i[0]])
        else:  # technosphere
            from_act = bd.get_activity(lca.activity_dict_rev[i[0]])
        to_act = bd.get_activity(lca.activity_dict_rev[i[1]])

        for exc in to_act.exchanges():
            if exc.input == from_act.key:
                exchanges.append(exc)
                # continue  # if there was always only one max exchange between two activities

    # in theory there should be as many exchanges as indices, but since
    # multiple exchanges are possible between two activities, the number of
    # exchanges must be at least equal or higher to the number of indices
    if len(exchanges) < len(
        indices
    ):  # must have at least as many exchanges as indices (assu)
        raise ValueError(
            "Error: mismatch between indices provided ({}) and Exchanges received ({}).".format(
                len(indices), len(exchanges)
            )
        )

    # by default drop exchanges and indices if the have no uncertainties
    if only_uncertain:
        exchanges, indices = drop_no_uncertainty_exchanges(exchanges, indices)

    return exchanges, indices


def drop_no_uncertainty_exchanges(excs, indices):
    excs_no = list()
    indices_no = list()
    for exc, ind in zip(excs, indices):
        if exc.get("uncertainty type") and exc.get("uncertainty type") >= 1:
            excs_no.append(exc)
            indices_no.append(ind)
    log.info(
        "Dropping {} exchanges of {} with no uncertainty. {} remaining.".format(
            len(excs) - len(excs_no), len(excs), len(excs_no)
        )
    )
    return excs_no, indices_no


def get_exchanges_dataframe(exchanges, indices, biosphere=False):
    """Returns a Dataframe from the exchange data and a bit of additional information."""

    for exc, i in zip(exchanges, indices):
        from_act = bd.get_activity(exc.get("input"))
        to_act = bd.get_activity(exc.get("output"))

        exc.update(
            {
                "index": i,
                "from name": from_act.get("name", np.nan),
                "from location": from_act.get("location", np.nan),
                "to name": to_act.get("name", np.nan),
                "to location": to_act.get("location", np.nan),
            }
        )

        # GSA name (needs to yield unique labels!)
        if biosphere:
            exc.update(
                {
                    "GSA name": "B: {} // {} ({}) [{}]".format(
                        from_act.get("name", ""),
                        to_act.get("name", ""),
                        to_act.get("reference product", ""),
                        to_act.get("location", ""),
                    )
                }
            )
        else:
            exc.update(
                {
                    "GSA name": "T: {} FROM {} [{}] TO {} ({}) [{}]".format(
                        from_act.get("reference product", ""),
                        from_act.get("name", ""),
                        from_act.get("location", ""),
                        to_act.get("name", ""),
                        to_act.get("reference product", ""),
                        to_act.get("location", ""),
                    )
                }
            )

    return pd.DataFrame(exchanges)


def get_CF_dataframe(lca, only_uncertain_CFs=True):
    """Returns a dataframe with the metadata for the characterization factors
    (in the biosphere matrix). Filters non-stochastic CFs if desired (default)."""
    data = dict()
    for params_index, row in enumerate(lca.cf_params):
        if only_uncertain_CFs and row["uncertainty_type"] <= 1:
            continue
        cf_index = row["row"]
        bio_act = bd.get_activity(lca.biosphere_dict_rev[cf_index])

        data.update({params_index: bio_act.as_dict()})

        for name in row.dtype.names:
            data[params_index][name] = row[name]

        data[params_index]["index"] = cf_index
        data[params_index]["GSA name"] = (
            "CF: " + bio_act["name"] + str(bio_act["categories"])
        )

    log.info(
        "CHARACTERIZATION FACTORS filtering resulted in including {} of {} characteriation factors.".format(
            len(data),
            len(lca.cf_params),
        )
    )
    df = pd.DataFrame(data).T
    df.rename(columns={"uncertainty_type": "uncertainty type"}, inplace=True)
    return df


def get_parameters_DF(mc):
    """Product to make parameters dataframe"""
    if bool(mc.parameter_data):  # returns False if dict is empty
        dfp = pd.DataFrame(mc.parameter_data).T
        dfp["GSA name"] = "P: " + dfp["name"]
        log.info(f"PARAMETERS: {len(dfp)}")
        return dfp
    else:
        log.info("PARAMETERS: None included.")
        return pd.DataFrame()  # return emtpy df


def get_exchange_values(matrix, indices):
    """Get technosphere exchanges values from a list of exchanges
    (row and column information)"""
    return [matrix[i] for i in indices]


def get_X(matrix_list, indices):
    """Get the input data to the GSA, i.e. A and B matrix values for each
    model run."""
    X = np.zeros((len(matrix_list), len(indices)))
    for row, M in enumerate(matrix_list):
        X[row, :] = get_exchange_values(M, indices)
    return X


def get_X_CF(mc, dfcf, method):
    """Get the characterization factors used for each model run. Only those CFs
    that are in the dfcf dataframe will be returned (i.e. by default only the
    CFs that have uncertainties."""
    # get all CF inputs
    CF_data = np.array(mc.CF_dict[method])  # has the same shape as the Xa and Xb below

    # reduce this to uncertain CFs only (if this was done for the dfcf)
    params_indices = dfcf.index.values

    # if params_indices:
    return CF_data[:, params_indices]


def get_X_P(dfp):
    """Get the parameter values for each model run"""
    lists = [d for d in dfp["values"]]
    return list(zip(*lists))


def get_problem(X, names):
    return {
        "num_vars": X.shape[1],
        "names": names,
        "bounds": list(zip(*(np.amin(X, axis=0), np.amax(X, axis=0)))),
    }


class GlobalSensitivityAnalysis(object):
    """Class for Global Sensitivity Analysis.
    For now Delta Moment Independent Measure based on:
    https://salib.readthedocs.io/en/latest/api.html#delta-moment-independent-measure
    Builds on top of Monte Carlo Simulation results.
    """

    def __init__(self, mc):
        self.update_mc(mc)
        self.act_number = int()
        self.method_number = int()
        self.cutoff_technosphere = float()
        self.cutoff_biosphere = float()

    def update_mc(self, mc):
        "Update the Monte Carlo Simulation object (and results)."
        try:
            assert isinstance(mc, MonteCarloLCA)
            self.mc = mc
        except AssertionError:
            raise AssertionError(
                "mc should be an instance of MonteCarloLCA, but instead it is a {}.".format(
                    type(mc)
                )
            )

    def perform_GSA(
        self,
        act_number=0,
        method_number=0,
        cutoff_technosphere=0.01,
        cutoff_biosphere=0.01,
    ):
        """Perform GSA for specific reference flow and impact category."""
        start = time()

        # set FU and method
        try:
            self.act_number = act_number
            self.method_number = method_number
            self.cutoff_technosphere = cutoff_technosphere
            self.cutoff_biosphere = cutoff_biosphere

            self.fu = self.mc.cs["inv"][act_number]
            self.activity = bd.get_activity(self.mc.rev_activity_index[act_number])
            self.method = self.mc.cs["ia"][method_number]

        except Exception as e:
            traceback.print_exc()
            # todo: QMessageBox.warning(self, 'Could not perform Delta analysis', str(e))
            log.error("Initializing the GSA failed.")
            return None

        log.info(
            f"-- GSA --\n Project: {bd.projects.current} CS: {self.mc.cs_name} "
            f"Activity: {self.activity} Method: {self.method}",
        )

        # get non-stochastic LCA object with reverse dictionaries
        self.lca = get_lca(self.fu, self.method)

        # =============================================================================
        #   Filter exchanges and get metadata DataFrames
        # =============================================================================
        dfs = []
        # technosphere
        if self.mc.include_technosphere:
            self.t_indices = filter_technosphere_exchanges(
                self.fu, self.method, cutoff=cutoff_technosphere, max_calc=1e4
            )
            self.t_exchanges, self.t_indices = get_exchanges(self.lca, self.t_indices)
            self.dft = get_exchanges_dataframe(self.t_exchanges, self.t_indices)
            if not self.dft.empty:
                dfs.append(self.dft)

        # biosphere
        if self.mc.include_biosphere:
            self.b_indices = filter_biosphere_exchanges(
                self.lca, cutoff=cutoff_biosphere
            )
            self.b_exchanges, self.b_indices = get_exchanges(
                self.lca, self.b_indices, biosphere=True
            )
            self.dfb = get_exchanges_dataframe(
                self.b_exchanges, self.b_indices, biosphere=True
            )
            if not self.dfb.empty:
                dfs.append(self.dfb)

        # characterization factors
        if self.mc.include_cfs:
            self.dfcf = get_CF_dataframe(
                self.lca, only_uncertain_CFs=True
            )  # None if no stochastic CFs
            if not self.dfcf.empty:
                dfs.append(self.dfcf)

        # parameters
        # todo: if parameters, include df, but remove exchanges from T and B (skipped for now)
        self.dfp = get_parameters_DF(self.mc)  # Empty df if no parameters
        if not self.dfp.empty:
            dfs.append(self.dfp)

        # Join dataframes to get metadata
        self.metadata = pd.concat(dfs, axis=0, ignore_index=True, sort=False)
        self.metadata.set_index("GSA name", inplace=True)

        # =============================================================================
        #     GSA
        # =============================================================================

        # Get X (Technosphere, Biosphere and CF values)
        X_list = list()
        if self.mc.include_technosphere and self.t_indices:
            self.Xa = get_X(self.mc.A_matrices, self.t_indices)
            X_list.append(self.Xa)
        if self.mc.include_biosphere and self.b_indices:
            self.Xb = get_X(self.mc.B_matrices, self.b_indices)
            X_list.append(self.Xb)
        if self.mc.include_cfs and not self.dfcf.empty:
            self.Xc = get_X_CF(self.mc, self.dfcf, self.method)
            X_list.append(self.Xc)
        if self.mc.include_parameters and not self.dfp.empty:
            self.Xp = get_X_P(self.dfp)
            X_list.append(self.Xp)

        self.X = np.concatenate(X_list, axis=1)
        # print('X', self.X.shape)

        # Get Y (LCA scores)
        self.Y = self.mc.get_results_dataframe(act_key=self.activity.key)[
            self.method
        ].to_numpy()

        # log-transformation. This makes it more robust for very uneven distributions of LCA results (e.g. toxicity related impacts).
        # Can only be applied if all Monte-Carlo LCA scores are either positive or negative.
        # Should not be used when LCA scores overlap zero (sometimes positive and sometimes negative)
        # if np.all(self.Y > 0) if self.Y[0] > 0 else np.all(self.Y < 0):  # check if all LCA scores are of the same sign
        #     self.Y = np.log(np.abs(self.Y))  # this makes it more robust for very uneven distributions of LCA results
        if np.all(self.Y > 0):  # all positive numbers
            self.Y = np.log(np.abs(self.Y))
            log.info("All positive LCA scores. Log-transformation performed.")
        elif np.all(self.Y < 0):  # all negative numbers
            self.Y = -np.log(np.abs(self.Y))
            log.info("All negative LCA scores. Log-transformation performed.")
        else:  # mixed positive and negative numbers
            log.warning(
                "Log-transformation cannot be applied as LCA scores overlap zero."
            )

        # print('Filtering took {} seconds'.format(np.round(time() - start, 2)))

        # define problem
        self.names = self.metadata.index  # ['GSA name']
        # print('Names:', len(self.names))
        self.problem = get_problem(self.X, self.names)

        # perform delta analysis
        time_delta = time()
        self.Si = delta.analyze(self.problem, self.X, self.Y, print_to_console=False)
        log.info(
            "Delta analysis took {} seconds".format(
                np.round(time() - time_delta, 2),
            )
        )

        # put GSA results in to dataframe
        self.dfgsa = pd.DataFrame(self.Si, index=self.names).sort_values(
            by="delta", ascending=False
        )
        self.dfgsa.index.names = ["GSA name"]

        # join with metadata
        self.df_final = self.dfgsa.join(self.metadata, on="GSA name")
        self.df_final.reset_index(inplace=True)
        self.df_final["pedigree"] = [str(x) for x in self.df_final["pedigree"]]

        log.info("GSA took {} seconds".format(np.round(time() - start, 2)))

    def get_save_name(self):
        save_name = (
            self.mc.cs_name
            + "_"
            + str(self.mc.iterations)
            + "_"
            + self.activity["name"]
            + "_"
            + str(self.method)
            + ".xlsx"
        )
        save_name = save_name.replace(",", "").replace("'", "").replace("/", "")
        return save_name

    def export_GSA_output(self):
        save_name = "gsa_output_" + self.get_save_name()
        self.df_final.to_excel(os.path.join(ab_settings.data_dir, save_name))

    def export_GSA_input(self):
        """Export the input data to the GSA with a human readible index"""
        X_with_index = pd.DataFrame(self.X.T, index=self.metadata.index)
        save_name = "gsa_input_" + self.get_save_name()
        X_with_index.to_excel(os.path.join(ab_settings.data_dir, save_name))


if __name__ == "__main__":
    mc = perform_MonteCarlo_LCA(project="ei34", cs_name="kraft paper", iterations=20)
    g = GlobalSensitivityAnalysis(mc)
    g.perform_GSA(
        act_number=0, method_number=1, cutoff_technosphere=0.01, cutoff_biosphere=0.01
    )
    g.export()
