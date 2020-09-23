# -*- coding: utf-8 -*-
import functools
from time import time
import warnings

import brightway2 as bw
from bw2io import ExcelImporter
from bw2io.errors import InvalidPackage, StrategyError
from bw2io.importers.excel import valid_first_cell
from bw2io.strategies import (
    csv_restore_tuples, csv_restore_booleans, csv_numerize,
    csv_drop_unknown, csv_add_missing_exchanges_section,
    normalize_units, normalize_biosphere_categories,
    normalize_biosphere_names, strip_biosphere_exc_locations,
    set_code_by_activity_hash, link_iterable_by_fields,
    assign_only_product_as_production,
    link_technosphere_by_activity_hash,
    drop_falsey_uncertainty_fields_but_keep_zeros,
    convert_uncertainty_types_to_integers,
    convert_activity_parameters_to_list
)

from .strategies import relink_exchanges_bw2package


INNER_FIELDS = ("name", "unit", "database", "location")
LINK_FIELDS = ("name", "unit", "location")


class ABExcelImporter(ExcelImporter):
    """Customized Excel importer for the AB."""

    def __init__(self, filepath):
        self.strategies = [
            csv_restore_tuples,
            csv_restore_booleans,
            csv_numerize,
            csv_drop_unknown,
            csv_add_missing_exchanges_section,
            normalize_units,
            normalize_biosphere_categories,
            normalize_biosphere_names,
            strip_biosphere_exc_locations,
            set_code_by_activity_hash,
            functools.partial(
                link_iterable_by_fields,
                other=bw.Database(bw.config.biosphere),
                kind='biosphere'
            ),
            assign_only_product_as_production,
            functools.partial(
                link_technosphere_by_activity_hash,
                fields=INNER_FIELDS
            ),
            drop_falsey_uncertainty_fields_but_keep_zeros,
            convert_uncertainty_types_to_integers,
            convert_activity_parameters_to_list,
        ]
        start = time()
        data = self.extractor.extract(filepath)
        data = [(x, y) for x, y in data if valid_first_cell(x, y)]
        print("Extracted {} worksheets in {:.2f} seconds".format(
              len(data), time() - start))
        if data and any(line for line in data):
            self.db_name, self.metadata = self.get_database(data)
            self.project_parameters = self.get_project_parameters(data)
            self.database_parameters = self.get_database_parameters(data)
            self.data = self.process_activities(data)
        else:
            warnings.warn("No data in workbook found")

    def write_database(self, **kwargs):
        """Go to the parent of the ExcelImporter class, not the ExcelImporter itself.

        This is important because we want to return a Database instance
        """
        kwargs['activate_parameters'] = kwargs.get('activate_parameters', True)
        return super(ExcelImporter, self).write_database(**kwargs)

    @classmethod
    def simple_automated_import(cls, filepath, overwrite: bool = True, purge: bool = False,
                                linker: str = None, **kwargs) -> list:
        """Handle a lot of the customizable things that can happen
        when doing an import in a script or notebook.
        """
        obj = cls(filepath)
        if obj.project_parameters:
            obj.write_project_parameters(delete_existing=purge)
        obj.apply_strategies()
        if any(obj.unlinked) and linker:
            # First try and match on the database field as well.
            obj.link_to_technosphere(linker, fields=INNER_FIELDS)
            # If there are still unlinked, use a rougher link.
            if any(obj.unlinked):
                obj.link_to_technosphere(linker)
        if any(obj.unlinked):
            # Still have unlinked fields? Raise exception.
            raise StrategyError([exc for exc in obj.unlinked])
        db = obj.write_database(delete_existing=overwrite, activate_parameters=True)
        return [db]

    def link_to_technosphere(self, db_name: str, fields: tuple = None) -> None:
        """Apply the 'link to technosphere' strategy with some flexibility."""
        fields = fields or LINK_FIELDS
        self.apply_strategy(functools.partial(
            link_technosphere_by_activity_hash,
            external_db_name=db_name, fields=fields
        ))


class ABPackage(bw.BW2Package):
    """ Inherits from brightway2 `BW2Package` and handles importing BW2Packages.

    This implementation is done to raise exceptions and show errors on imports
    much faster.
    """
    @classmethod
    def evaluate_metadata(cls, metadata: dict, ignore_dbs: set):
        """ Take the given metadata dictionary and test it against realities
        of the current brightway project.
        """
        if "depends" in metadata:
            missing = set(metadata["depends"]).difference(bw.databases)
            # Remove any databases present in ignore_dbs (these will be relinked)
            missing = missing.difference(ignore_dbs)
            if missing:
                raise InvalidPackage(
                    "Package data links to database names that do not exist: {}".format(missing),
                    missing
                )

    @classmethod
    def load_file(cls, filepath, whitelist=True, relink: dict = None):
        """Similar to how the base class loads the data, but also perform
        a number of evaluations on the metadata.

        Also, if given a 'relink' dictionary, perform relinking of exchanges.
        """
        data = super().load_file(filepath, whitelist)
        relinking = set(relink.keys()) if relink else set([])
        if isinstance(data, dict):
            if "metadata" in data:
                cls.evaluate_metadata(data["metadata"], relinking)
            if relink:
                data["data"] = relink_exchanges_bw2package(data["data"], relink)
        else:
            for obj in data:
                if "metadata" in obj:
                    cls.evaluate_metadata(obj["metadata"], relinking)
                if relink:
                    obj["data"] = relink_exchanges_bw2package(obj["data"], relink)
        return data

    @classmethod
    def import_file(cls, filepath, whitelist=True, relink: dict = None):
        """Import bw2package file, and create the loaded objects, including registering, writing, and processing the created objects.

        Args:
            * *filepath* (str): Path of file to import
            * *whitelist* (bool): Apply whitelist to allowed types. Default is ``True``.
        Kwargs:
            * *relink* (dict): A dictionary of keys with which to relink exchanges
              within the imported package file.

        Returns:
            Created object or list of created objects.

        """
        loaded = cls.load_file(filepath, whitelist, relink)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if isinstance(loaded, dict):
                return cls._create_obj(loaded)
            else:
                return [cls._create_obj(o) for o in loaded]
