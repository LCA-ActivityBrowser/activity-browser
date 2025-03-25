from qtpy import QtWidgets

import pandas as pd
import bw2data as bd
import bw_functional as bf

from activity_browser import actions, bwutils
from activity_browser.ui import widgets, icons, tables

from .base import BaseLCATab


class InventoryTab(BaseLCATab):
    """Class for the 'Inventory' sub-tab.

    This tab allows for investigation of the inventories of the calculation.

    Shows:
        Option to choose between 'Biosphere flows' and 'Technosphere flows'
        Inventory table for either 'Biosphere flows' or 'Technosphere flows'
        Export options
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.df_biosphere = None
        self.df_technosphere = None

        self.layout().addWidget(QtWidgets.QLabel("Inventory"))

        self.bio_tech_button_group = QtWidgets.QButtonGroup()
        self.bio_categorisation_factor_group = QtWidgets.QComboBox()
        # buttons
        button_layout = QtWidgets.QHBoxLayout()
        self.radio_button_biosphere = QtWidgets.QRadioButton("Biosphere flows")
        self.radio_button_biosphere.setChecked(True)

        self.radio_button_technosphere = QtWidgets.QRadioButton("Technosphere flows")
        self.remove_zeros_checkbox = QtWidgets.QCheckBox("Remove '0' values")
        self.remove_zero_state = False

        self.categorisation_factor_filters = [
            "No filtering with categorisation factors",
            "Flows without categorisation factors",
            "Flows with categorisation factors",
        ]
        self.categorisation_factor_state = None
        self.old_categorisation_factor_state = self.categorisation_factor_state

        self.last_remove_zero_state = self.remove_zero_state
        self.remove_zeros_checkbox.setChecked(self.remove_zero_state)
        self.remove_zeros_checkbox.setToolTip(
            "Choose whether to show '0' values or not.\n"
            "When selected, '0' values are not shown.\n"
            "Rows are only removed when all reference flows are '0'."
        )
        self.scenario_label = QtWidgets.QLabel("Scenario:")

        # Group the radio buttons into the appropriate groups for the window
        self.update_combobox(
            self.bio_categorisation_factor_group, self.categorisation_factor_filters
        )
        self.bio_categorisation_factor_group.setMaximumWidth(300)
        self.bio_categorisation_factor_group.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToContentsOnFirstShow
        )

        # Setup the Qt environment for the buttons, including the arrangement
        self.categorisation_filter_layout = QtWidgets.QVBoxLayout()
        self.categorisation_filter_layout.addWidget(QtWidgets.QLabel("Filter flows:"))
        self.categorisation_filter_layout.addWidget(
            self.bio_categorisation_factor_group
        )
        self.categorisation_filter_box = QtWidgets.QWidget()
        self.categorisation_filter_box.setLayout(self.categorisation_filter_layout)
        self.categorisation_filter_box.setVisible(True)
        self.categorisation_filter_with_flows = None

        button_layout.addWidget(self.radio_button_biosphere)
        button_layout.addWidget(self.radio_button_technosphere)
        button_layout.addWidget(self.scenario_label)
        button_layout.addWidget(self.scenario_box)
        button_layout.addStretch(1)
        button_layout.addWidget(self.remove_zeros_checkbox)
        self.layout().addLayout(button_layout)
        self.layout().addWidget(self.categorisation_filter_box)
        # table
        self.table = tables.InventoryTable(self.parent())
        self.table.table_name = "Inventory_" + self.parent().cs_name
        self.layout().addWidget(self.table)

        self.layout().addLayout(self.build_export(has_plot=False, has_table=True))
        self.connect_signals()

    def connect_signals(self):
        self.radio_button_biosphere.toggled.connect(self.button_clicked)
        self.remove_zeros_checkbox.toggled.connect(self.remove_zeros_checked)
        self.bio_tech_button_group.buttonClicked.connect(
            self.toggle_categorisation_factor_filter_buttons
        )
        self.bio_categorisation_factor_group.activated.connect(
            self.add_categorisation_factor_filter
        )
        if self.has_scenarios:
            self.scenario_box.currentIndexChanged.connect(
                self.parent().update_scenario_data
            )
            self.parent().update_scenario_box_index.connect(
                lambda index: self.set_combobox_index(self.scenario_box, index)
            )

    def add_categorisation_factor_filter(self, index: int):
        if (
            self.bio_categorisation_factor_group.currentText()
            == "Flows without categorisation factors"
        ):
            self.categorisation_filter_with_flows = False
            self.categorisation_factor_state = False
        elif (
            self.bio_categorisation_factor_group.currentText()
            == "Flows with categorisation factors"
        ):
            self.categorisation_filter_with_flows = True
            self.categorisation_factor_state = True
        else:
            self.categorisation_filter_with_flows = None
            self.categorisation_factor_state = None
        self.update_table()
        self.old_categorisation_factor_state = self.categorisation_factor_state

    def toggle_categorisation_factor_filter_buttons(self, bttn: QtWidgets.QRadioButton):
        if bttn.text() == "Biosphere flows":
            self.categorisation_filter_box.setVisible(True)
        else:
            self.categorisation_filter_box.setVisible(False)
            self.categorisation_factor_state = None

    def remove_zeros_checked(self, toggled: bool):
        """Update table according to remove-zero selected."""
        self.remove_zero_state = toggled
        self.update_table()
        self.last_remove_zero_state = self.remove_zero_state

    def button_clicked(self, toggled: bool):
        """Update table according to radiobutton selected."""
        ext = "_Inventory" if toggled else "_Inventory_technosphere"
        self.table.table_name = "{}{}".format(self.parent().cs_name, ext)
        self.update_table()

    def configure_scenario(self):
        """Allow scenarios options to be visible when used."""
        super().configure_scenario()
        self.scenario_label.setVisible(self.has_scenarios)

    def update_tab(self):
        """Update the tab."""
        self.clear_tables()
        super().update_tab()

    def elementary_flows_contributing_to_IA_methods(
        self, contributary: bool = True, bios: pd.DataFrame = None
    ) -> pd.DataFrame:
        """Returns a biosphere dataframe filtered for the presence in the impact assessment methods
        Requires a boolean argument for whether those flows included in the impact assessment method
        should be returned (True), or not (False)
        """
        incl_flows = {
            self.parent().contributions.inventory_data["biosphere"][1][k]
            for mthd in self.parent().mlca.method_matrices
            for k in mthd.indices
        }
        data = bios if bios is not None else self.df_biosphere
        if contributary:
            flows = incl_flows
        else:
            flows = (
                set(self.parent().contributions.inventory_data["biosphere"][1].values())
            ).difference(incl_flows)
        new_flows = [flow[1] for flow in flows]

        return data.loc[data["code"].isin(new_flows)]

    def update_table(self):
        """Update the table."""
        inventory = (
            "biosphere" if self.radio_button_biosphere.isChecked() else "technosphere"
        )
        self.table.showing = inventory
        # We handle both 'df_biosphere' and 'df_technosphere' variables here.
        attr_name = "df_{}".format(inventory)
        if (
            getattr(self, attr_name) is None
            or self.remove_zero_state != self.last_remove_zero_state
            or self.old_categorisation_factor_state != self.categorisation_factor_state
        ):
            setattr(
                self,
                attr_name,
                self.parent().contributions.inventory_df(inventory_type=inventory),
            )

        # filter the biosphere flows for the relevance to the CFs
        if (
            self.categorisation_filter_with_flows is not None
            and inventory == "biosphere"
        ):
            self.df_biosphere = self.elementary_flows_contributing_to_IA_methods(
                self.categorisation_filter_with_flows, self.df_biosphere
            )

        # filter the flows to remove those that have relevant exchanges
        def filter_zeroes(df):
            filter_on = [x for x in df.columns.tolist() if "|" in x]
            return df[df[filter_on].sum(axis=1) != 0].reset_index(drop=True)

        if self.remove_zero_state and getattr(self, "df_biosphere") is not None:
            self.df_biosphere = filter_zeroes(self.df_biosphere)
        if self.remove_zero_state and getattr(self, "df_technosphere") is not None:
            self.df_technosphere = filter_zeroes(self.df_technosphere)

        self._update_table(getattr(self, attr_name))

    def clear_tables(self) -> None:
        """Set the biosphere and technosphere to None."""
        self.df_biosphere, self.df_technosphere = None, None

    def _update_table(self, table: pd.DataFrame, drop: str = "code"):
        """Update the table."""
        self.table.model.sync((table.drop(drop, axis=1)).reset_index(drop=True))
