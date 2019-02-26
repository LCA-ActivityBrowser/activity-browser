# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets
import pandas as pd
from brightway2 import get_activity
from operator import itemgetter

from .dataframe_table import ABDataFrameTable

from ...bwutils import commontasks as bc


def inventory_labels(length, mlca, labellength):
    labels = [str(get_activity(mlca.rev_activity_dict[i])) for i in range(length)]
    shortlabels = [((i[:labellength-2] + '..') if len(i) > labellength else i) for i in labels]
    return shortlabels


class LCAResultsTable(ABDataFrameTable):
    @ABDataFrameTable.decorated_sync
    def sync(self, mlca, relative=False):
        if relative:
            data = mlca.results_normalized
        else:
            data = mlca.results
        col_labels = [" | ".join(x) for x in mlca.methods]
        row_labels = [str(get_activity(list(func_unit.keys())[0])) for func_unit in mlca.func_units]
        self.dataframe = pd.DataFrame(data, index=row_labels, columns=col_labels)
        # self.dataframe = pd.DataFrame(data, columns=col_labels)
        # self.dataframe.insert(loc=0, column="Name", value=row_labels)


class ProcessContributionsTable(ABDataFrameTable):
    def __init__(self, parent):
        super(ProcessContributionsTable, self).__init__(parent)
        self.parent = parent

    @ABDataFrameTable.decorated_sync
    def sync(self, dummy):
        self.dataframe = self.parent.plot.df_tc


class InventoryCharacterisationTable(ABDataFrameTable):
    def __init__(self, parent):
        super(InventoryCharacterisationTable, self).__init__(parent)
        self.parent = parent

    @ABDataFrameTable.decorated_sync
    def sync(self, dummy):
        self.dataframe = self.parent.plot.df_tc


class InventoryTable(ABDataFrameTable):
    def __init__(self, parent, **kwargs):
        super(InventoryTable, self).__init__(parent, **kwargs)
        self.biosphere_df = None
        self.technosphere_df = None

    @ABDataFrameTable.decorated_sync
    def sync(self, mlca, type="biosphere"):
        if type == "biosphere":
            if self.biosphere_df is None:
                # biosphere flows description
                fields = ["name", "categories", "unit", "database"]
                data_description = bc.get_activity_data_as_lists(act_keys=mlca.rev_biosphere_dict.values(),
                                                         keys=fields)
                df_description = pd.DataFrame(data_description)
                df_description = df_description.astype(str)
                # biosphere flows
                FU_names = [bc.format_activity_label(key, style="pnl_") for key in mlca.fu_activity_keys]
                df_inventory = pd.DataFrame(mlca.inventory)
                df_inventory.columns = FU_names
                self.dataframe = df_description.join(df_inventory)
                self.biosphere_df = self.dataframe
            else:
                self.dataframe = self.biosphere_df
        elif type == "technosphere":
            if self.technosphere_df is None:
                # technosphere flows description
                fields = ["reference product", "name", "location", "database"]
                description = bc.get_activity_data_as_lists(act_keys=mlca.rev_activity_dict.values(),
                                                            keys=fields)
                df_description = pd.DataFrame(description)
                df_description = df_description.astype(str)
                # technosphere flows
                FU_names = [bc.format_activity_label(key, style="pnl_") for key in mlca.fu_activity_keys]
                df_contribution = pd.DataFrame(mlca.technosphere_flows)
                df_contribution.columns = FU_names
                self.dataframe = df_description.join(df_contribution)
                self.technosphere_df = self.dataframe
            else:
                self.dataframe = self.technosphere_df

        # sort ignoring case sensitivity
        self.dataframe = self.dataframe.iloc[self.dataframe["name"].str.lower().argsort()]
        self.dataframe.reset_index(inplace=True, drop=True)

class ContributionTable(ABDataFrameTable):
    def __init__(self, parent, **kwargs):
        super(ContributionTable, self).__init__(parent, **kwargs)

    @ABDataFrameTable.decorated_sync
    def sync(self, mlca, type="elementary"):
        if type == "elementary":
            description = bc.get_activity_data_as_lists(act_keys=mlca.rev_biosphere_dict.values(),
                                                        keys=["name", "categories", "unit"])
            df_description = pd.DataFrame(description)
            df_description = df_description.astype(str)
            FU_names = [bc.format_activity_label(key, style="pnl_") for key in mlca.fu_activity_keys]
            df_contribution = pd.DataFrame(mlca.elementary_flow_contributions[:, 0]).T
            df_contribution.columns = FU_names
            print(df_contribution.head())
            # df_inventory = pd.DataFrame(mlca.inventory)
            # df_inventory.columns = FU_names
            self.dataframe = df_description.join(df_contribution)

        elif type == "process":
            # process description
            description = bc.get_activity_data_as_lists(act_keys=mlca.rev_activity_dict.values(),
                                                        keys=["reference product", "name", "location", "database"])
            df_description = pd.DataFrame(description)
            df_description = df_description.astype(str)
            FU_names = [bc.format_activity_label(key, style="pnl_") for key in mlca.fu_activity_keys]
            df_contribution = pd.DataFrame(mlca.process_contributions[:, 0]).T
            df_contribution.columns = FU_names
            self.dataframe = df_description.join(df_contribution)

        # sort ignoring case sensitivity
        self.dataframe = self.dataframe.iloc[self.dataframe["name"].str.lower().argsort()]
        # self.dataframe.sort_values(by="name", ascending=True, inplace=True)
        self.dataframe.reset_index(inplace=True, drop=True)


class BiosphereTable(QtWidgets.QTableView):
    def __init__(self, parent):
        super(BiosphereTable, self).__init__(parent)

    def sync(self, mlca, method=None, limit=20):

        if method not in mlca.technosphere_flows.keys():
            method = mlca.func_unit_translation_dict[str(method)]

        matrix = mlca.inventories[str(method)]
        matrix = matrix[:limit, :limit]

        table = QtWidgets.QTableWidget(self)
        #matrix = csr_matrix([[1,2,3],[5,6,7], [0,9,8], [1,2,3]])

        matrix = matrix.toarray()
        table.setRowCount(matrix.shape[1])
        table.setColumnCount(matrix.shape[0])
        for ni, i in enumerate(matrix):
            for nj, j in enumerate(i):
                table.setItem(nj, ni, QtWidgets.QTableWidgetItem(str(j)))
        length = limit
        shortlabels = inventory_labels(length, mlca, 50)
        table.setVerticalHeaderLabels(shortlabels)
        table.setVerticalScrollMode(1)
        table.setHorizontalScrollMode(1)
        table.setMinimumWidth(700)

        return table






