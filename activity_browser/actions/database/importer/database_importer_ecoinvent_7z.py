import sys
import os
import tqdm
import multiprocessing

import py7zr
from PySide2 import QtWidgets
from bw2io.importers.ecospold2 import *
from bw2io.extractors.ecospold2 import Ecospold2DataExtractor, getattr2, ACTIVITY_TYPES
from lxml import objectify

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.ui.wizards.db_import_wizard import DatabaseImportWizard


class DatabaseImporterEcoinvent7z(ABAction):
    """ABAction to open the DatabaseImportWizard"""

    icon = qicons.import_db
    text = "Import database from ecoinvent .7z file"
    tool_tip = "Import database from ecoinvent .7z file"

    @staticmethod
    @exception_dialogs
    def run():
        # get the path from the user
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=application.main_window,
            caption='Choose project file to import',
            filter='7z archive (*.7z);; All files (*.*)'
        )
        if not path:
            return

        importer = Ecoinvent7zImporter(
            path,
            "Test",
            "biosphere3",
        )

        importer.apply_strategies()
        importer.write_database()


class Ecoinvent7zExtractor(Ecospold2DataExtractor):
    @classmethod
    def extract(cls, dirpath, db_name, use_mp=True):
        assert os.path.isfile(dirpath)
        with py7zr.SevenZipFile(dirpath, mode='r') as archive:
            # List the contents of the archive
            file_list = [file.filename for file in archive.list()
                         if file.filename.startswith("datasets")
                         and file.filename.endswith(".spold")]
            extracted_data = archive.read(file_list)

        with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
            print("Extracting XML data from {} datasets".format(len(extracted_data)))
            results = [
                pool.apply_async(
                    cls.extract_activity,
                    args=(x, "test_db"),
                )
                for x in extracted_data.values()
            ]
            data = [p.get() for p in results]

        return data

    @classmethod
    def extract_activity_from_raw(cls, xml_bytes, db_name):
        root = objectify.parse(xml_bytes).getroot()
        if hasattr(root, "activityDataset"):
            stem = root.activityDataset
        else:
            stem = root.childActivityDataset

        comments = [
            cls.condense_multiline_comment(
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
                cls.condense_multiline_comment(
                    getattr2(stem.activityDescription.geography, "comment")
                ),
            ),
            (
                "Technology: ",
                cls.condense_multiline_comment(
                    getattr2(stem.activityDescription.technology, "comment")
                ),
            ),
            (
                "Time period: ",
                cls.condense_multiline_comment(
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
            'activity':  stem.activityDescription.activity.get('id'),
            'database': db_name,
            "exchanges": [
                cls.extract_exchange(exc)
                for exc in stem.flowData.iterchildren()
                if "parameter" not in exc.tag
            ],
            #'filename':  os.path.basename(filename),
            'location':  stem.activityDescription.geography.shortname.text,
            'name':      stem.activityDescription.activity.activityName.text,
            'synonyms': [s.text for s in getattr(stem.activityDescription.activity, 'synonym', [])],
            "parameters": dict(
                [
                    cls.extract_parameter(exc)
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


class Ecoinvent7zImporter(SingleOutputEcospold2Importer):
    def __init__(
            self,
            filepath: str,
            db_name: str,
            biosphere_database_name: str | None = None,
            extractor: Any = Ecoinvent7zExtractor,
            use_mp: bool = USE_MP,
            signal: Any = None,
            reparametrize_lognormals: bool = False,
    ):

        """
        Initializes the SingleOutputEcospold2Importer class instance.

        Parameters
        ----------
        dirpath : str
            Path to the directory containing the ecospold2 file.
        db_name : str
            Name of the LCI database.
        biosphere_database_name : str | None
            Name of biosphere database to link to. Uses `config.biosphere` if not provided.
        extractor : class
            Class for extracting data from the ecospold2 file, by default Ecospold2DataExtractor.
        use_mp : bool
            Flag to indicate whether to use multiprocessing, by default True.
        signal : object
            Object to indicate the status of the import process, by default None.
        reparametrize_lognormals: bool
            Flag to indicate if lognormal distributions for exchanges should be reparametrized
            such that the mean value of the resulting distribution meets the amount
            defined for the exchange.
        """
        self.db_name = db_name
        self.signal = signal
        self.strategies = [
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
            partial(link_biosphere_by_flow_uuid, biosphere=biosphere_database_name or config.biosphere),
            link_internal_technosphere_by_composite_code,
            delete_exchanges_missing_activity,
            delete_ghost_exchanges,
            remove_uncertainty_from_negative_loss_exchanges,
            fix_unreasonably_high_lognormal_uncertainties,
            convert_activity_parameters_to_list,
            add_cpc_classification_from_single_reference_product,
            delete_none_synonyms,
            partial(update_social_flows_in_older_consequential,
                    biosphere_db=Database(biosphere_database_name or config.biosphere)),
        ]

        if reparametrize_lognormals:
            self.strategies.append(reparametrize_lognormal_to_agree_with_static_amount)
        else:
            self.strategies.append(set_lognormal_loc_value)

        start = time()
        try:
            self.data = extractor.extract(filepath, db_name, use_mp=use_mp)
        except RuntimeError as e:
            raise MultiprocessingError(
                "Multiprocessing error; re-run using `use_mp=False`"
            ).with_traceback(e.__traceback__)
        print(
            u"Extracted {} datasets in {:.2f} seconds".format(
                len(self.data), time() - start
            )
        )


