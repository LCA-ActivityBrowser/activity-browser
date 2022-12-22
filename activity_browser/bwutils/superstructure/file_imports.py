from pathlib import Path
from abc import ABC, abstractmethod
import pandas as pd
from .utils import _time_it_
from typing import Optional, Union
from ..errors import (
    ImportCanceledError, ActivityProductionValueError, IncompatibleDatabaseNamingError,
    InvalidSDFEntryValue
)


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
    ABStandardProcessColumns = {'from activity name', 'from reference product', 'to reference product', 'to location',
                                'from location', 'to activity name', 'from key', 'flow type', 'from database',
                                'to database', 'to key', 'from unit', 'to unit'}

    ABScenarioColumnsErrorIfNA = {'from key', 'flow type', 'to key'}
    ABStandardBiosphereColumns = {'from categories', 'to categories'}

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
        for ds in zip(data['from database'], data['from key'], data['to database'], data['to key'], data['from activity name'], data['to activity name']):
            if ds[0] != ds[1].split(',')[0][2:-1] or ds[2] != ds[3].split(',')[0][2:-1]:
                raise IncompatibleDatabaseNamingError(
                    "Error in importing file with activity {} and {}".format(ds[4], ds[5]))

    @staticmethod
    def production_process_check(data: pd.DataFrame, scenario_names: list) -> None:
        """ Runs a check on a dataframe over the scenario names (provided by the second argument)
        If for a production exchange a value of 0 is observed for one of the scenarios an
        ActivityProductionValueError is thrown with the source and destination activity names of the
        exchanges being provided
        """
        failed = pd.DataFrame({})
        for scenario in scenario_names:
            failed = pd.concat([data.loc[(data.loc[:, 'flow type'] == 'production') & (data.loc[:, scenario] == 0.0)], failed])
        if not failed.empty:
            raise ActivityProductionValueError("Error with the production value in the exchange between activity {} and {}".format(failed['from activity name'], failed['to activity name']))

    @staticmethod
    def na_value_check(data: pd.DataFrame, fields: list) -> None:
        """ Runs checks on the dataframe to ensure that those fields specified by the field argument do not
        contain NaNs.
        If an NaN is discovered an InvalidSDFEntryValue Error is thrown that contains two lists:
        The first contains the list of the source activity names, the second the destination activity names
        of the exchange
        """
        hasNA = pd.DataFrame({})
        for field in fields:
            hasNA = pd.concat([data.loc[data[field].isna()], hasNA])
        if not hasNA.empty:
            raise InvalidSDFEntryValue("Error with NA's in the exchange between activity {} and {}".format(hasNA['from activity name'], hasNA['to activity name']))

    @staticmethod
    def fill_nas(data: pd.DataFrame):
        """ Will replace NaNs in the dataframe with a string holding "NA" for the following subsection of columns:
            'from activity name', 'from reference product', 'to reference product', 'to location',
            'from location', 'to activity name', 'from database', 'to database', 'from unit', 'to unit',
            'from categories' and 'to categories'

            Note: How NaNs are treated depends on the 'flow type'
        """
        not_bio_cols = ABFileImporter.ABStandardProcessColumns.difference(ABFileImporter.ABScenarioColumnsErrorIfNA)
        bio_cols = ABFileImporter.ABStandardProcessColumns.union(ABFileImporter.ABStandardBiosphereColumns).difference(ABFileImporter.ABScenarioColumnsErrorIfNA)
        non_bio = data.loc[data.loc[:, 'flow type'] != 'biosphere'].fillna(dict.fromkeys(not_bio_cols, 'NA'))
        bio = data.loc[data.loc[:, 'flow type'] == 'biosphere'].fillna(dict.fromkeys(bio_cols, 'NA'))
        return pd.concat([non_bio, bio])

    @staticmethod
    def all_checks(data: pd.DataFrame, fields: set, scenario_names: list) -> None:
        ABFileImporter.fill_nas(data)
        ABFileImporter.database_and_key_check(data)
        # Check all following uses of fields has the same requirements
        ABFileImporter.na_value_check(data, list(fields) + scenario_names)
        ABFileImporter.production_process_check(data, scenario_names)

    @staticmethod
    def scenario_names(data: pd.DataFrame) -> list:
        return list(set(data.columns).difference(ABFileImporter.ABStandardProcessColumns.union(ABFileImporter.ABStandardBiosphereColumns)))

class ABPickleImporter(ABFileImporter):
    def __init__(self):
        super(ABPickleImporter, self).__init__(self)

    @staticmethod
    def read_file(path: Optional[Union[str, Path]], **kwargs):
        if kwargs['compression'] != '-':
            df = pd.read_pickle(path, compresion=kwargs['compression'])
        else:
            df = pd.read_pickle(path)
        # ... execute code
        ABPickleImporter.all_checks(df, ABPickleImporter.ABScenarioColumnsErrorIfNA, ABPickleImporter.scenario_names(df))
        return df


class ABFeatherImporter(ABFileImporter):
    def __init__(self):
        super(ABFeatherImporter, self).__init__(self)

    @staticmethod
    def read_file(path: Optional[Union[str, Path]], **kwargs):
        df = pd.read_feather(path)
        # ... execute code
        ABPickleImporter.all_checks(df, ABPickleImporter.ABScenarioColumnsErrorIfNA, ABPickleImporter.scenario_names(df))
        return df


class ABCSVImporter(ABFileImporter):
    def __init__(self):
        super(ABCSVImporter, self).__init__(self)

    @staticmethod
    def read_file(path: Optional[Union[str, Path]], **kwargs):
        if kwargs['compression'] != '-':
            compression = kwargs['compression']
        else:
            compression = 'infer'
        if 'sep' in kwargs:
            separator = kwargs['sep']
        else:
            separator = ";"
        df = pd.read_csv(path, compression=compression, sep=separator, index_col=0)
        # ... execute code
        ABPickleImporter.all_checks(df, ABPickleImporter.ABScenarioColumnsErrorIfNA, ABPickleImporter.scenario_names(df))
        return df


class FileImports(object):
    def __init__(self):
        pass

    @staticmethod
    @_time_it_
    def pickle(file: Optional[Union[str, Path]]) -> pd.DataFrame:
        return pd.read_pickle(file)

    @staticmethod
    @_time_it_
    def hd5(file: Optional[Union[str, Path]], key: Optional[Union[str, None]]) -> pd.DataFrame:
        return pd.read_hdf(file, key=key)

    @staticmethod
    @_time_it_
    def csv_zipped(file: Optional[Union[str, Path]], sep: str = ';') -> pd.DataFrame:
        return pd.read_csv(file, sep=sep)

    @staticmethod
    @_time_it_
    def feather(file: Optional[Union[str, Path]], compression: str = None) -> pd.DataFrame:
        if not compression:
            return pd.read_feather(file)
        return pd.read_feather(file, compression=compression)
