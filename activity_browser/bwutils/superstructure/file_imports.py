import ast
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union
from logging import getLogger

import pandas as pd

from ..errors import *

log = getLogger(__name__)


class ABFileImporter(ABC):
    """
    Activity Browser abstract base class for scenario file imports

    Contains a set of static methods for checking the file contents
    to conform to the desired standard. These include:
    - correct spelling of key and database names (checking they match)
    - correct spelling of databases (if few instances are found)
    - that all production exchanges do not have a value of 0
    - that NAs are properly interpreted
    """

    ABStandardProcessColumns = {
        "from activity name",
        "from reference product",
        "to reference product",
        "to location",
        "from location",
        "to activity name",
        "from key",
        "flow type",
        "from database",
        "to database",
        "to key",
        "from unit",
        "to unit",
    }

    ABScenarioColumnsErrorIfNA = {"from key", "flow type", "to key"}
    ABStandardBiosphereColumns = {"from categories", "to categories"}

    def __init__(self):
        pass

    @abstractmethod
    def read_file(self, path: Optional[Union[str, Path]], **kwargs):
        """Abstract method must be implemented in child classes."""
        return NotImplemented

    @staticmethod
    def database_and_key_check(data: pd.DataFrame) -> None:
        """Will check the values in the 'xxxx database' and the 'xxxx key' fields.
        If the database names are incongruent an IncompatibleDatabaseNamingError is raised.
        The source and destination keys are provided for the first exchange where
        this error occurs.
        """
        try:
            for ds in zip(
                data["from database"],
                data["from key"],
                data["to database"],
                data["to key"],
                data["from activity name"],
                data["to activity name"],
            ):
                if (
                    ds[0] != ds[1].split(",")[0][2:-1]
                    or ds[2] != ds[3].split(",")[0][2:-1]
                ):
                    msg = "Error in importing file with activity {} and {}".format(
                        ds[4], ds[5]
                    )
                    raise IncompatibleDatabaseNamingError()
        except IncompatibleDatabaseNamingError as e:
            log.error(msg)
            raise e

    @staticmethod
    def production_process_check(data: pd.DataFrame, scenario_names: list) -> None:
        """Runs a check on a dataframe over the scenario names (provided by the second argument)
        If for a production exchange a value of 0 is observed for one of the scenarios an
        ActivityProductionValueError is thrown with the source and destination activity names of the
        exchanges being provided
        """
        failed = pd.DataFrame({})
        try:
            for scenario in scenario_names:
                failed = pd.concat(
                    [
                        data.loc[
                            (data.loc[:, "flow type"] == "production")
                            & (data.loc[:, scenario] == 0.0)
                        ],
                        failed,
                    ]
                )
            if not failed.empty:
                msg = "Error with the production value in the exchange between activity {} and {}".format(
                    failed["from activity name"], failed["to activity name"]
                )
                raise ActivityProductionValueError()
        except ActivityProductionValueError as e:
            log.error(msg)
            raise e

    @staticmethod
    def na_value_check(data: pd.DataFrame, fields: list) -> None:
        """Runs checks on the dataframe to ensure that those fields specified by the field argument do not
        contain NaNs.
        If an NaN is discovered an InvalidSDFEntryValue Error is thrown that contains two lists:
        The first contains the list of the source activity names, the second the destination activity names
        of the exchange
        """
        hasNA = pd.DataFrame({})
        try:
            for field in fields:
                hasNA = pd.concat([data.loc[data[field].isna()], hasNA])
            if not hasNA.empty:
                msg = (
                    "Error with NA's in the exchange between activity {} and {}".format(
                        hasNA["from activity name"], hasNA["to activity name"]
                    )
                )
                raise InvalidSDFEntryValue()
        except InvalidSDFEntryValue as e:
            log.error(msg)
            raise e

    @staticmethod
    def check_for_calculation_errors(data: pd.DataFrame) -> None:
        """
        Will check for calculation errors in the scenario exchanges columns indicate the first elements in the
        scenario difference file that contain an ERROR value (only deals with divide by zero and NaN manipulations).
        """
        scen_cols = set(data.columns).difference(
            ABFileImporter.ABStandardProcessColumns.union(
                ABFileImporter.ABStandardBiosphereColumns
            )
        )
        for scen in scen_cols:
            error = data.loc[(data[scen] == "#DIV/0!") | (data[scen] == "#VALUE!")]
            if not error.empty:
                msg = "Error with values for the exchanges between {} and {}".format(
                    data.loc[0, "from activity name"], data.loc[0, "to activity name"]
                )
                raise ExchangeErrorValues(msg)

    @staticmethod
    def fill_nas(data: pd.DataFrame) -> pd.DataFrame:
        """Will replace NaNs in the dataframe with a string holding "NA" for the following subsection of columns:
        'from activity name', 'from reference product', 'to reference product', 'to location',
        'from location', 'to activity name', 'from database', 'to database', 'from unit', 'to unit',
        'from categories' and 'to categories'

        Note: How NaNs are treated depends on the 'flow type'
        """
        not_bio_cols = ABFileImporter.ABStandardProcessColumns.difference(
            ABFileImporter.ABScenarioColumnsErrorIfNA
        )
        bio_cols = ABFileImporter.ABStandardProcessColumns.union(
            ABFileImporter.ABStandardBiosphereColumns
        ).difference(ABFileImporter.ABScenarioColumnsErrorIfNA)
        non_bio = data.loc[data.loc[:, "flow type"] != "biosphere"].fillna(
            dict.fromkeys(not_bio_cols, "NA")
        )
        bio = data.loc[data.loc[:, "flow type"] == "biosphere"].fillna(
            dict.fromkeys(bio_cols, "NA")
        )
        return pd.concat([non_bio, bio])

    @staticmethod
    def all_checks(
        data: pd.DataFrame, fields: set = None, scenario_names: list = None
    ) -> None:
        if fields == None:
            fields = ABFeatherImporter.ABScenarioColumnsErrorIfNA
        if scenario_names == None:
            scenario_names = ABFeatherImporter.scenario_names(data)
        ABFileImporter.fill_nas(data)
        ABFileImporter.database_and_key_check(data)
        # Check all following uses of fields has the same requirements
        ABFileImporter.na_value_check(data, list(fields) + scenario_names)
        ABFileImporter.production_process_check(data, scenario_names)
        ABFileImporter.check_for_calculation_errors(data)

    @staticmethod
    def scenario_names(data: pd.DataFrame) -> list:
        return list(
            set(data.columns).difference(
                ABFileImporter.ABStandardProcessColumns.union(
                    ABFileImporter.ABStandardBiosphereColumns
                )
            )
        )


class ABFeatherImporter(ABFileImporter):
    def __init__(self):
        super(ABFeatherImporter, self).__init__(self)

    @staticmethod
    def read_file(path: Optional[Union[str, Path]], **kwargs):
        df = pd.read_feather(path)
        # ... execute code
        df.loc[:, "from key"] = df.loc[:, "from key"].apply(tuple)
        df.loc[:, "to key"] = df.loc[:, "to key"].apply(tuple)
        return df


class ABCSVImporter(ABFileImporter):
    def __init__(self):
        super(ABCSVImporter, self).__init__(self)

    @staticmethod
    def read_file(path: Optional[Union[str, Path]], **kwargs):
        if "separator" in kwargs:
            separator = kwargs["separator"]
        else:
            separator = ";"
        df = pd.read_csv(
            path,
            compression="infer",
            sep=separator,
            index_col=False,
            converters={"from key": ast.literal_eval, "to key": ast.literal_eval},
        )
        # ... execute code
        return df
