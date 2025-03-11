from qtpy.QtCore import Signal, SignalInstance

from activity_browser.ui import widgets
from activity_browser.ui.composites import RadioButtonCollapseComposite, DatabaseNameComposite, HorizontalButtonsComposite


class EcoinventSetupComposite(DatabaseNameComposite):
    rejected: SignalInstance = Signal()
    accepted: SignalInstance = Signal()

    def __init__(self):
        # initialize superclass with an ecoinvent focus
        super().__init__(
            label="Set ecoinvent database name"
        )
        # validate when the database name is changed by the user
        self.database_name.textChanged.connect(self.validate)

        # setup the biosphere choice section
        self.biosphere_choice = RadioButtonCollapseComposite()

        # add option to connect to an existing biosphere database
        self.biosphere_choice.add_option(
            name="existing",
            label="Link to an existing biosphere",
            view=widgets.ABComboBox.get_database_combobox()
        )
        self.biosphere_choice.button("existing").clicked.connect(self.validate)

        # add option to install the supplied biosphere database
        self.biosphere_choice.add_option(
            name="import",
            label="Import included biosphere",
            view=DatabaseNameComposite(label=None, database_placeholder="Set biosphere name")
        )
        self.biosphere_choice.button("import").clicked.connect(self.validate)
        self.biosphere_choice.view("import").database_name.textChanged.connect(self.validate)

        # set up the buttons at the bottom of the layout and connect the signals
        self.buttons = HorizontalButtonsComposite("Cancel", "*~Import")
        self.buttons["Cancel"].clicked.connect(self.rejected.emit)
        self.buttons["Import"].clicked.connect(self.accepted.emit)

        # finalize the layout
        self.layout().addWidget(self.biosphere_choice)
        self.layout().addWidget(self.buttons)

        self.validate()

    def get_database_name(self) -> str:
        return self.database_name.text()

    def get_biosphere_choice(self) -> None | str:
        return self.biosphere_choice.current_option()

    def get_biosphere_name(self) -> None | str:
        choice = self.get_biosphere_choice()
        if choice == "existing":
            return self.biosphere_choice.view(choice).currentText()
        if choice == "import":
            return self.biosphere_choice.view(choice).database_name.text()
        else:
            return None

    def validate(self):
        valid = (
            bool(self.get_database_name())
            and (
                self.get_biosphere_choice() == "existing"
                or (
                    self.get_biosphere_choice() == "import"
                    and bool(self.get_biosphere_name())
                )
            )
        )
        self.buttons["Import"].setEnabled(valid)