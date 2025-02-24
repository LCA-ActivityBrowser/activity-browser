from qtpy import QtWidgets

import pandas as pd
import bw2data as bd

from activity_browser.bwutils import refresh_node, AB_metadata

from .views import ExchangesView
from .models import ExchangesModel


class ExchangesTab(QtWidgets.QWidget):
    def __init__(self, activity: tuple | int | bd.Node, parent=None):
        super().__init__(parent)

        self.activity = refresh_node(activity)

        # Output Table
        self.output_view = ExchangesView(self)
        self.output_model = ExchangesModel(self)
        self.output_view.setModel(self.output_model)

        # Input Table
        self.input_view = ExchangesView(self)
        self.input_model = ExchangesModel(self)
        self.input_view.setModel(self.input_model)

        self.build_layout()

    def build_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 10, 0, 1)

        layout.addWidget(QtWidgets.QLabel("<b>⠀Output:</b>"))
        layout.addWidget(self.output_view)
        layout.addWidget(QtWidgets.QLabel("<b>⠀Input:</b>"))
        layout.addWidget(self.input_view)

        self.setLayout(layout)

    def sync(self) -> None:
        """Populate the various tables and boxes within the Activity Detail tab"""
        self.activity = refresh_node(self.activity)

        # fill in the values of the ActivityTab widgets, excluding the ActivityDataGrid which is populated separately
        production = self.activity.production()
        technosphere = self.activity.technosphere()
        biosphere = self.activity.biosphere()

        inputs = ([x for x in production if x["amount"] < 0] +
                  [x for x in technosphere if x["amount"] >= 0] +
                  [x for x in biosphere if (x.input["type"] != "emission" and x["amount"] >= 0) or (x.input["type"] == "emission" and x["amount"] < 0)])

        outputs = ([x for x in production if x["amount"] >= 0] +
                   [x for x in technosphere if x["amount"] < 0] +
                   [x for x in biosphere if (x.input["type"] == "emission" and x["amount"] >= 0) or (x.input["type"] != "emission" and x["amount"] < 0)])

        self.output_model.setDataFrame(self.build_df(outputs))
        self.input_model.setDataFrame(self.build_df(inputs))

    def build_df(self, exchanges) -> pd.DataFrame:
        cols = ["key", "unit", "name", "location", "substitute", "substitution_factor", "allocation_factor",
                "properties", "processor"]
        exc_df = pd.DataFrame(exchanges, columns=["amount", "input", "formula", "uncertainty type",])
        act_df = AB_metadata.get_metadata(exc_df["input"].unique(), cols)

        df = exc_df.merge(
            act_df,
            left_on="input",
            right_on="key"
        ).drop(columns=["key"])

        if not df["substitute"].isna().all():
            df = df.merge(
                AB_metadata.dataframe[["key", "name"]].rename({"name": "substitute_name"}, axis="columns"),
                left_on="substitute",
                right_on="key",
                how="left",
            ).drop(columns=["key"])
        else:
            df.drop(columns=["substitute", "substitution_factor"], inplace=True)

        if not act_df.properties.isna().all():
            props_df = act_df[act_df.properties.notna()]
            props_df = pd.DataFrame(list(props_df.get("properties")), index=props_df.key)
            props_df.rename(lambda col: f"property_{col}", axis="columns", inplace=True)

            df = df.merge(
                props_df,
                left_on="input",
                right_index=True,
                how="left",
            )

        df["_allocate_by"] = self.activity.get("allocation")
        df["_activity_type"] = self.activity.get("type")
        df["_exchange"] = exchanges

        df.drop(columns=["properties"], inplace=True)
        df.rename({"input": "_input_key", "substitute": "_substitute_key", "processor": "_processor_key",
                   "uncertainty type": "uncertainty"},
            axis="columns", inplace=True)

        cols = ["amount", "unit", "name", "location"]
        cols += ["substitute_name", "substitution_factor"] if "substitute_name" in df.columns else []
        cols += ["allocation_factor"]
        cols += [col for col in df.columns if col.startswith("property")]
        cols += ["formula", "uncertainty"]
        cols += [col for col in df.columns if col.startswith("_")]

        return df[cols]

