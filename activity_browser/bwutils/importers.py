# -*- coding: utf-8 -*-
import functools
import warnings
from pathlib import Path

import tqdm
from bw2io import BW2Package, ExcelImporter
from bw2io.errors import InvalidPackage, StrategyError
from bw2io.strategies import (convert_activity_parameters_to_list,
                              convert_uncertainty_types_to_integers,
                              csv_add_missing_exchanges_section,
                              csv_drop_unknown, csv_numerize,
                              csv_restore_booleans, csv_restore_tuples,
                              drop_falsey_uncertainty_fields_but_keep_zeros,
                              link_iterable_by_fields,
                              link_technosphere_by_activity_hash,
                              normalize_biosphere_categories,
                              normalize_biosphere_names, normalize_units,
                              set_code_by_activity_hash,
                              strip_biosphere_exc_locations)
import bw2data as bd
from bw2data.serialization import JsonSanitizer, JsonWrapper

from .errors import LinkingFailed
from .strategies import (alter_database_name, csv_rewrite_product_key,
                         hash_parameter_group, link_exchanges_without_db,
                         link_functional_processors, relink_exchanges_bw2package,
                         relink_exchanges_with_db, rename_db_bw2package,
                         parse_JSON_fields, metadatastore_link,
                         alter_exchange_database_name)


_EXCEL_PREP = (
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
    drop_falsey_uncertainty_fields_but_keep_zeros,
    convert_uncertainty_types_to_integers,
    hash_parameter_group,
    convert_activity_parameters_to_list,
    parse_JSON_fields,
)


def _excel_link_strategies(relink: dict | None = None):
    strategies = [
        functools.partial(
            link_iterable_by_fields,
            other=bd.Database(bd.config.biosphere),
            kind="biosphere",
        ),
        link_technosphere_by_activity_hash,
    ]
    if relink is not None:
        strategies.extend([
            functools.partial(alter_exchange_database_name, linking_dict=relink),
            metadatastore_link,
        ])
    strategies.append(link_functional_processors)
    return strategies


class ABExcelImporter(ExcelImporter):
    """Customized Excel importer for the AB."""

    def database_class(self, db_name: str, requested_backend: str = "sqlite") -> bd.ProcessedDataStore:
        try:
            from bw_functional import FunctionalSQLiteDatabase

            if self.needs_multifunctional_database:
                return FunctionalSQLiteDatabase(db_name)
            else:
                return bd.Database(db_name, backend=requested_backend)

        except ImportError:
            return bd.Database(db_name, backend=requested_backend)

    @property
    def needs_multifunctional_database(self) -> bool:
        return any(ds.get("processor") for ds in self.data)

    def write_database(self, **kwargs):
        """Go to the parent of the ExcelImporter class, not the ExcelImporter itself.

        This is important because we want to return a Database instance
        """
        kwargs["activate_parameters"] = kwargs.get("activate_parameters", True)
        db = super(ExcelImporter, self).write_database(**kwargs)
        # bw2io writes with signal=False when projects.dataset.is_sourced is False.
        from bw2data import signals
        signals.on_database_write.send(name=db.name)
        return db

    @classmethod
    def simple_automated_import(
        cls, filepath, db_name: str, relink: dict = None
    ) -> list:
        """Handle a lot of the customizable things that can happen
        when doing an import in a script or notebook.
        """

        obj = cls(filepath)
        return obj.automated_import(db_name, relink)

    def automated_import(self, db_name: str, relink: dict = None) -> list:
        self.strategies = [
            _EXCEL_PREP[0],
            functools.partial(alter_database_name, old=self.db_name, new=db_name),
            *_EXCEL_PREP[1:],
            *_excel_link_strategies(),
        ]
        self.db_name = db_name

        has_params = any([
            self.project_parameters,
            self.database_parameters,
            any("parameters" in ds for ds in self.data),
        ])
        self.apply_strategies()
        if any(self.unlinked) and relink:
            for db, new_db in relink.items():
                if db == "(name missing)":
                    self.apply_strategy(
                        functools.partial(link_exchanges_without_db, db=new_db)
                    )
                else:
                    self.apply_strategy(
                        functools.partial(relink_exchanges_with_db, old=db, new=new_db)
                    )
            # Relinking failed (some exchanges still unlinked)
            if any(self.unlinked):
                # Raise a different exception.
                excs = [exc for exc in self.unlinked][:10]
                databases = {
                    exc.get("database", "(name missing)") for exc in self.unlinked
                }
                raise LinkingFailed(excs, databases)
        if any(self.unlinked):
            # Still have unlinked fields? Raise exception.
            excs = [exc for exc in self.unlinked][:10]
            databases = {exc.get("database", "(name missing)") for exc in self.unlinked}
            raise StrategyError(excs, databases)

        if self.project_parameters:
            self.write_project_parameters(delete_existing=False)
        db = self.write_database(delete_existing=True, activate_parameters=True)
        if has_params:
            bd.parameters.recalculate()
        return [db]

    def apply_basic_strategies(self):
        self.apply_strategies(_EXCEL_PREP)

    def apply_db_name(self, db_name: str):
        """Apply a database name change strategy."""
        self.apply_strategy(
            functools.partial(alter_database_name, old=self.db_name, new=db_name)
        )
        self.db_name = db_name

    def apply_linking(self, relink: dict):
        self.apply_strategies(_excel_link_strategies(relink))


    def apply_strategies(self, strategies=None, verbose=False):
        strategies = strategies or self.strategies
        for strategy in tqdm.tqdm(strategies, desc="Applying strategies", total=len(strategies)):
            self.apply_strategy(strategy, verbose)



class ABPackage(BW2Package):
    """Inherits from brightway2 `BW2Package` and handles importing BW2Packages.

    This implementation is done to raise exceptions and show errors on imports
    much faster.
    """
    APPROVED = {
        "bw2calc",
        "bw2data",
        "bw2io",
        "bw2regional",
        "bw2temporalis",
        "bw_functional",
    }

    @classmethod
    def unrestricted_export(cls, obj, path: Path) -> Path:
        """Export a BW2Package outside the project folder."""
        cls._write_file(path, [cls._prepare_obj(obj, False)])
        return path

    @classmethod
    def _read_package_objects(cls, filepath):
        """Load bw2package JSON without resolving stored class names."""
        raw_data = JsonSanitizer.load(JsonWrapper.load_bz2(filepath))
        if isinstance(raw_data, dict):
            return [raw_data]
        return list(raw_data)

    @classmethod
    def missing_dependencies(cls, filepath) -> set[str]:
        """Return dependency database names from the package that are not in the project."""
        missing = set()
        for obj in cls._read_package_objects(filepath):
            depends = obj.get("metadata", {}).get("depends", [])
            missing.update(set(depends).difference(bd.databases))
        return missing

    @classmethod
    def evaluate_metadata(cls, metadata: dict, ignore_dbs: set):
        """Take the given metadata dictionary and test it against realities
        of the current brightway project.
        """
        if "depends" in metadata:
            missing = set(metadata["depends"]).difference(bd.databases)
            # Remove any databases present in ignore_dbs (these will be relinked)
            missing = missing.difference(ignore_dbs)
            if missing:
                raise InvalidPackage(
                    "Package data links to database names that do not exist: {}".format(
                        missing
                    ),
                    missing,
                )

    @classmethod
    def _apply_package_options(cls, obj: dict, db_name: str | None, relink: dict | None) -> dict:
        ignore = set(relink or {})
        if "metadata" in obj:
            cls.evaluate_metadata(obj["metadata"], ignore)
        if db_name and obj.get("name") != db_name:
            old = obj.pop("name")
            obj["name"] = db_name
            obj["data"] = rename_db_bw2package(obj["data"], old, db_name)
        if relink:
            obj["data"] = relink_exchanges_bw2package(obj["data"], relink)
        return obj

    @classmethod
    def load_file(cls, filepath, whitelist=True, **kwargs):
        relink = kwargs.get("relink")
        db_name = kwargs.get("rename")
        data = [
            cls._load_obj(obj, whitelist)
            for obj in cls._read_package_objects(filepath)
        ]
        if len(data) == 1:
            data = cls._apply_package_options(data[0], db_name, relink)
        else:
            data = [cls._apply_package_options(obj, db_name, relink) for obj in data]
        return data

    @classmethod
    def _create_obj(cls, data):
        instance = data["class"](data["name"])

        if data["name"] not in instance._metadata:
            instance.register(**data["metadata"])
        else:
            instance.backup()
            instance.metadata = data["metadata"]

        instance.write(data["data"], signal=True)
        return instance

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
