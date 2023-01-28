# -*- coding: utf-8 -*-
import functools
from pathlib import Path
import warnings

import brightway2 as bw
from bw2io import ExcelImporter, CSVImporter
from bw2io.errors import InvalidPackage, StrategyError
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

from .errors import LinkingFailed
from .strategies import (
    relink_exchanges_bw2package, alter_database_name, hash_parameter_group,
    relink_exchanges_with_db, link_exchanges_without_db, rename_db_bw2package,
    csv_rewrite_product_key,
)


class ABExcelImporter(ExcelImporter):
    """Customized Excel importer for the AB."""

    def write_database(self, **kwargs):
        """Go to the parent of the ExcelImporter class, not the ExcelImporter itself.

        This is important because we want to return a Database instance
        """
        kwargs['activate_parameters'] = kwargs.get('activate_parameters', True)
        return super(ExcelImporter, self).write_database(**kwargs)

    @classmethod
    def simple_automated_import(cls, filepath, db_name: str, relink: dict = None) -> list:
        """Handle a lot of the customizable things that can happen
        when doing an import in a script or notebook.
        """

        obj = cls(filepath)
        obj.strategies = [
            functools.partial(
                alter_database_name,
                old=obj.db_name,
                new=db_name
            ),
            csv_restore_tuples,
            csv_restore_booleans,
            csv_numerize,
            csv_drop_unknown,
            csv_add_missing_exchanges_section,
            csv_rewrite_product_key,
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
            link_technosphere_by_activity_hash,
            drop_falsey_uncertainty_fields_but_keep_zeros,
            convert_uncertainty_types_to_integers,
            hash_parameter_group,
            convert_activity_parameters_to_list,
        ]
        obj.db_name = db_name

        # Test if the import contains any parameters.
        has_params = any([
            obj.project_parameters, obj.database_parameters,
            any("parameters" in ds for ds in obj.data)
        ])
        obj.apply_strategies()
        if any(obj.unlinked) and relink:
            for db, new_db in relink.items():
                if db == "(name missing)":
                    obj.apply_strategy(functools.partial(
                        link_exchanges_without_db, db=new_db
                    ))
                else:
                    obj.apply_strategy(functools.partial(
                        relink_exchanges_with_db, old=db, new=new_db
                    ))
            # Relinking failed (some exchanges still unlinked)
            if any(obj.unlinked):
                # Raise a different exception.
                excs = [exc for exc in obj.unlinked][:10]
                databases = {exc.get("database", "(name missing)") for exc in obj.unlinked}
                raise LinkingFailed(excs, databases)
        if any(obj.unlinked):
            # Still have unlinked fields? Raise exception.
            excs = [exc for exc in obj.unlinked][:10]
            databases = {exc.get("database", "(name missing)") for exc in obj.unlinked}
            raise StrategyError(excs, databases)
        if obj.project_parameters:
            obj.write_project_parameters(delete_existing=False)
        db = obj.write_database(delete_existing=True, activate_parameters=True)
        if has_params:
            bw.parameters.recalculate()
        return [db]

class ABPackage(bw.BW2Package):
    """ Inherits from brightway2 `BW2Package` and handles importing BW2Packages.

    This implementation is done to raise exceptions and show errors on imports
    much faster.
    """
    @classmethod
    def unrestricted_export(cls, obj, path: Path) -> Path:
        """Export a BW2Package outside the project folder."""
        cls._write_file(path, [cls._prepare_obj(obj, False)])
        return path

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
    def load_file(cls, filepath, whitelist=True, **kwargs):
        """Similar to how the base class loads the data, but also perform
        a number of evaluations on the metadata.

        Also, if given a 'relink' dictionary, perform relinking of exchanges.
        """
        relink = kwargs.get("relink", None)
        db_name = kwargs.get("rename", None)
        data = super().load_file(filepath, whitelist)
        relinking = set(relink.keys()) if relink else set([])
        if isinstance(data, dict):
            if "metadata" in data:
                cls.evaluate_metadata(data["metadata"], relinking)
            if db_name and "name" in data and data["name"] != db_name:
                old_name = data.pop("name")
                data["name"] = db_name
                data["data"] = rename_db_bw2package(data["data"], old_name, db_name)
            if relink:
                data["data"] = relink_exchanges_bw2package(data["data"], relink)
        else:
            for obj in data:
                if "metadata" in obj:
                    cls.evaluate_metadata(obj["metadata"], relinking)
                if db_name and "name" in obj and obj["name"] != db_name:
                    old_name = obj.pop("name")
                    obj["name"] = db_name
                    obj["data"] = rename_db_bw2package(obj["data"], old_name, db_name)
                if relink:
                    obj["data"] = relink_exchanges_bw2package(obj["data"], relink)
        return data

    @classmethod
    def import_file(cls, filepath, whitelist=True, **kwargs):
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
        loaded = cls.load_file(filepath, whitelist, **kwargs)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if isinstance(loaded, dict):
                return cls._create_obj(loaded)
            else:
                return [cls._create_obj(o) for o in loaded]
