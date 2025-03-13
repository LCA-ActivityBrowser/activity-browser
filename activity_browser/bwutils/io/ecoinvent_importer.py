import py7zr
import multiprocessing
import tempfile
import os
from io import BytesIO
from lxml import objectify
from functools import partial
from logging import getLogger

import tqdm
import bw2data as bd
from bw2io.extractors.ecospold2 import getattr2, ACTIVITY_TYPES, Ecospold2DataExtractor
from bw2io.importers.ecospold2_biosphere import Ecospold2BiosphereImporter
from bw2io.strategies import (
    add_cpc_classification_from_single_reference_product,
    assign_single_product_as_activity,
    convert_activity_parameters_to_list,
    create_composite_code,
    delete_exchanges_missing_activity,
    delete_ghost_exchanges,
    delete_none_synonyms,
    drop_temporary_outdated_biosphere_flows,
    drop_unspecified_subcategories,
    es2_assign_only_product_with_amount_as_reference_product,
    fix_ecoinvent_flows_pre35,
    fix_unreasonably_high_lognormal_uncertainties,
    link_biosphere_by_flow_uuid,
    link_internal_technosphere_by_composite_code,
    normalize_units,
    remove_uncertainty_from_negative_loss_exchanges,
    remove_unnamed_parameters,
    remove_zero_amount_coproducts,
    remove_zero_amount_inputs_with_no_activity,
    update_ecoinvent_locations,
    update_social_flows_in_older_consequential,
)

log = getLogger(__name__)


class Ecoinvent7zImporter:

    def __init__(self, archive_path: str) -> None:
        self.archive_path = archive_path

    def install_biosphere(self, biosphere_name: str = "biosphere3") -> None:
        """
        Installs the biosphere that is bundled in the ecoinvent .7z. Simple extraction and installing through the
        standard bw2io importer is quick enough because we're talking about a single file.
        """
        # extract the elementary exchanges to a temporary location
        with py7zr.SevenZipFile(self.archive_path, mode='r') as archive:
            temp = tempfile.gettempdir()
            archive.extract(temp, ["MasterData/ElementaryExchanges.xml"])
            bio_file = os.path.join(temp, "MasterData/ElementaryExchanges.xml")

        # initiate the importer with the elementary exchanges file
        importer = Ecospold2BiosphereImporter(biosphere_name, None, bio_file)

        # install the biosphere
        importer.apply_strategies()
        importer.write_database(searchable=False)

    def install_ecoinvent(self, db_name, biosphere_name: str = "biosphere3"):
        """
        Runs the importer by reading the .7z archive into memory and multiprocessing it from there. This is faster than
        the usual method which is very much IO-bound.
        """
        # if the db already exists, warn the user of the impending overwriting and delete the existing database
        if db_name in bd.databases:
            log.warning(f"Database already exists, overwriting {db_name}")
            bd.Database(db_name).delete(warn=False)

        # load the spold files into memory
        spold_bytes = self.read_archive_to_bytes()

        # process the in-memory data to a dict format and applying strategies
        db_data = self.process_bytes(spold_bytes, db_name)
        db_data = self.apply_strategies(db_data, biosphere_name)

        # rewrite into an ingestible format
        db_data = {(ds["database"], ds["code"]): ds for ds in db_data}

        # creating the actual database
        db = bd.Database(db_name)
        db.write(db_data, searchable=False)

    def apply_strategies(self, db_data, biosphere_name):
        strategies = [
            normalize_units,
            update_ecoinvent_locations,
            remove_zero_amount_coproducts,
            remove_zero_amount_inputs_with_no_activity,
            remove_unnamed_parameters,
            es2_assign_only_product_with_amount_as_reference_product,
            assign_single_product_as_activity,
            create_composite_code,
            drop_unspecified_subcategories,
            fix_ecoinvent_flows_pre35,
            drop_temporary_outdated_biosphere_flows,
            partial(link_biosphere_by_flow_uuid, biosphere=biosphere_name),
            link_internal_technosphere_by_composite_code,
            delete_exchanges_missing_activity,
            delete_ghost_exchanges,
            remove_uncertainty_from_negative_loss_exchanges,
            fix_unreasonably_high_lognormal_uncertainties,
            convert_activity_parameters_to_list,
            add_cpc_classification_from_single_reference_product,
            delete_none_synonyms,
            partial(update_social_flows_in_older_consequential, biosphere_db=bd.Database(biosphere_name)),
        ]
        for strategy in tqdm.tqdm(strategies, desc="Applying strategies", total=len(strategies)):
            db_data = strategy(db_data)
        return db_data

    def read_archive_to_bytes(self) -> {str: BytesIO}:
        log.info("Extracting .7z archive to memory")
        with py7zr.SevenZipFile(self.archive_path, mode='r') as archive:
            # Find all .spold dataset files
            file_list = [
                file.filename for file in archive.list()
                if file.filename.startswith("datasets")
                and file.filename.endswith(".spold")
            ]

            extracted_data = archive.read(file_list)

        return extracted_data

    def process_bytes(self, spold_bytes: {str: BytesIO}, db_name: str) -> list:
        with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
            log.info(f"Extracting XML data from {len(spold_bytes)} datasets")
            results = [
                pool.apply_async(
                    self.extract_activity,
                    args=(x, db_name),
                )
                for x in spold_bytes.values()
            ]

            data = []
            for result in tqdm.tqdm(results, desc="Processing datasets", total=len(results)):
                data.append(result.get())

        return data

    @staticmethod
    def extract_activity(xml_bytes, db_name):
        root = objectify.parse(xml_bytes).getroot()
        if hasattr(root, "activityDataset"):
            stem = root.activityDataset
        else:
            stem = root.childActivityDataset

        comments = [
            Ecospold2DataExtractor.condense_multiline_comment(
                getattr2(stem.activityDescription.activity, "generalComment")
            ),
            (
                "Included activities start: ",
                getattr2(
                    stem.activityDescription.activity, "includedActivitiesStart"
                ).get("text"),
            ),
            (
                "Included activities end: ",
                getattr2(
                    stem.activityDescription.activity, "includedActivitiesEnd"
                ).get("text"),
            ),
            (
                "Geography: ",
                Ecospold2DataExtractor.condense_multiline_comment(
                    getattr2(stem.activityDescription.geography, "comment")
                ),
            ),
            (
                "Technology: ",
                Ecospold2DataExtractor.condense_multiline_comment(
                    getattr2(stem.activityDescription.technology, "comment")
                ),
            ),
            (
                "Time period: ",
                Ecospold2DataExtractor.condense_multiline_comment(
                    getattr2(stem.activityDescription.timePeriod, "comment")
                ),
            ),
        ]
        comment = "\n".join(
            [
                (" ".join(x) if isinstance(x, tuple) else x)
                for x in comments
                if (x[1] if isinstance(x, tuple) else x)
            ]
        )

        classifications = [
            (el.classificationSystem.text, el.classificationValue.text)
            for el in stem.activityDescription.iterchildren()
            if el.tag == u"{http://www.EcoInvent.org/EcoSpold02}classification"
        ]

        data = {
            "comment": comment,
            "classifications": classifications,
            "activity type": ACTIVITY_TYPES[
                int(stem.activityDescription.activity.get("specialActivityType") or 0)
            ],
            'activity': stem.activityDescription.activity.get('id'),
            'database': db_name,
            "exchanges": [
                Ecospold2DataExtractor.extract_exchange(exc)
                for exc in stem.flowData.iterchildren()
                if "parameter" not in exc.tag
            ],
            # 'filename':  os.path.basename(filename),
            'location': stem.activityDescription.geography.shortname.text,
            'name': stem.activityDescription.activity.activityName.text,
            'synonyms': [s.text for s in getattr(stem.activityDescription.activity, 'synonym', [])],
            "parameters": dict(
                [
                    Ecospold2DataExtractor.extract_parameter(exc)
                    for exc in stem.flowData.iterchildren()
                    if "parameter" in exc.tag
                ]
            ),
            "authors": {
                "data entry": {
                    "name": stem.administrativeInformation.dataEntryBy.get(
                        "personName"
                    ),
                    "email": stem.administrativeInformation.dataEntryBy.get(
                        "personEmail"
                    ),
                },
                "data generator": {
                    "name": stem.administrativeInformation.dataGeneratorAndPublication.get(
                        "personName"
                    ),
                    "email": stem.administrativeInformation.dataGeneratorAndPublication.get(
                        "personEmail"
                    ),
                },
            },
            "type": "process",
        }
        return data

