from uuid import uuid4

from qtpy import QtWidgets

import bw2data as bd

from bw_functional import Process

from activity_browser import application, bwutils
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons


class ActivityNewProduct(ABAction):
    """
    ABAction to create a new product for an activity.

    This action prompts the user to supply a name, unit, and location for the new product.
    If the user cancels or does not provide a name, the action is aborted.
    Otherwise, it creates a new product associated with the given activity.

    Attributes:
        icon (QIcon): The icon representing this action.
        text (str): The display text for this action.
    """

    icon = qicons.add
    text = "Create product"

    @staticmethod
    @exception_dialogs
    def run(activities: list[tuple | int | bd.Node]):
        """
        Execute the action to create a new product.

        This method iterates over the provided activities, ensuring each is a `Process`.
        It prompts the user to input details for the new product. If valid details are provided,
        a new product is created and saved.

        Args:
            activities (list[tuple | int | bd.Node]): A list of activities to process.

        Raises:
            AssertionError: If an activity is not of type `Process`.
        """
        activities = [bwutils.refresh_node(activity) for activity in activities]

        for act in activities:
            assert isinstance(act, Process), "Cannot create new product for non-process type"
            # Ask the user to provide a name for the new product
            dialog = NewProductDialog(act, application.main_window)
            # If the user cancels, skip to the next activity
            if dialog.exec_() != QtWidgets.QDialog.Accepted:
                continue
            name, unit, location = dialog.get_new_process_data()
            # If no name is provided, skip to the next activity
            if not name:
                continue

            # Create the new product
            new_prod_data = {
                "name": name,
                "unit": unit,
                "location": location,
                "type": "product",
            }
            new_product = act.new_product(code=uuid4().hex, **new_prod_data)
            new_product.save()


class NewProductDialog(QtWidgets.QDialog):
    """
    A dialog for gathering parameters to create a new product.

    This dialog allows the user to input the product name, unit, and location.
    It validates the input and provides options to either create the product or cancel the operation.
    """

    def __init__(self, activity: bd.Node, parent: QtWidgets.QWidget = None):
        """
        Initialize the NewProductDialog.

        Args:
            activity (bd.Node): The activity for which the product is being created.
                             Used to prefill the location field and set the dialog title.
            parent (QtWidgets.QWidget, optional): The parent widget for the dialog. Defaults to None.
        """
        super().__init__(parent)

        # Set the dialog window title
        self.setWindowTitle(f"Create product for {activity['name']}")

        # Input fields for product details
        self.name_edit = QtWidgets.QLineEdit()
        self.unit_edit = QtWidgets.QLineEdit("kilogram")  # Default unit is "kilogram"
        self.location_edit = QtWidgets.QLineEdit(activity.get("location", ""))  # Prefill location if available

        # Buttons for user actions
        self.ok_button = QtWidgets.QPushButton("Create")
        self.ok_button.clicked.connect(self.accept)  # Connect the "Create" button to accept the dialog
        self.ok_button.setEnabled(False)  # Initially disable the button until a name is entered

        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)  # Connect the "Cancel" button to reject the dialog

        # Set up signals and layout
        self.connect_signals()
        self.build_layout()

    def connect_signals(self):
        """
        Connect signals to their respective handlers.

        - Enables the "Create" button only when the name field is not empty.
        """
        self.name_edit.textChanged.connect(lambda x: self.ok_button.setEnabled(bool(x)))

    def build_layout(self):
        """
        Build and set the layout for the dialog.

        The layout includes labels and input fields for product name, unit, and location,
        as well as "Create" and "Cancel" buttons.
        """
        layout = QtWidgets.QGridLayout()
        layout.addWidget(QtWidgets.QLabel("Product name"), 0, 0)
        layout.addWidget(self.name_edit, 0, 1)

        layout.addWidget(QtWidgets.QLabel("Unit"), 1, 0)
        layout.addWidget(self.unit_edit, 1, 1)

        layout.addWidget(QtWidgets.QLabel("Location"), 2, 0)
        layout.addWidget(self.location_edit, 2, 1)

        layout.addWidget(self.ok_button, 3, 0)
        layout.addWidget(self.cancel_button, 3, 1)

        self.setLayout(layout)

    def get_new_process_data(self) -> tuple[str, str, str]:
        """
        Retrieve the parameters entered by the user.

        Returns:
            tuple[str, str, str]: A tuple containing the product name, unit, and location.
        """
        return (
            self.name_edit.text(),
            self.unit_edit.text(),
            self.location_edit.text()
        )
