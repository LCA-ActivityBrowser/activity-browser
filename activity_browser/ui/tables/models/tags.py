from typing import Any

import dateutil.parser
import pandas as pd

from activity_browser.ui.tables.models import EditablePandasModel


class TagsModel(EditablePandasModel):
    HEADERS = ["Name", "Value", "Type"]

    @classmethod
    def map_value_type(self, value):
        """
        Map a value to a type supported by tags
        """
        if isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            try:
                dateutil.parser.parse(value)
                return "date"
            except ValueError:
                pass

            return "str"
        else:
            return "str"

    @classmethod
    def dataframe_from_tags(cls, tags: dict) -> "pd.DataFrame":
        return pd.DataFrame(
            [(key, value, cls.map_value_type(value)) for key, value in tags.items()],
            columns=cls.HEADERS,
        )

    def has_duplicate_key(self) -> bool:
        """
        Check if there are any duplicate specified for tags
        """
        return self._dataframe["Name"].duplicated().any()

    def sync(self, tags: dict[str, Any]) -> None:
        self._dataframe = self.dataframe_from_tags(tags)
        self.updated.emit()

    def add_new_tag(self):
        self.insertRows(self.rowCount())
        self._dataframe.loc[self.rowCount() - 1] = ["", "", "str"]
        self.updated.emit()

    def remove_tag(self, index: int) -> None:
        self.removeRow(index)
        self.updated.emit()

    def get_tags(self) -> dict[str, Any]:
        """
        Get the current tag dictionary
        """
        return dict(zip(self._dataframe["Name"], self._dataframe["Value"]))
