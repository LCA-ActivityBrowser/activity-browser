from logging import getLogger

from bw2io.ecoinvent import *

import pyprind

from activity_browser.mod.ecoinvent_interface.release import ABEcoinventRelease
from activity_browser.mod.bw2io.importers.ecospold2_biosphere import ABEcospold2BiosphereImporter

log = getLogger(__name__)


def ab_import_ecoinvent_release(version, system_model):
    """Activity Browser version of bw2io.ecoinvent.import_ecoinvent_release that employs a progress slot"""
    from bw2io import migrations
    from .migrations import ab_create_core_migrations

    if not len(migrations):
        ab_create_core_migrations()

    # downloading a release through a AB version of ecoinvent_interface that implements a progress_slot
    release = ABEcoinventRelease(ei.Settings())

    lci_path = release.get_release(
        version=version,
        system_model=system_model,
        release_type=ei.ReleaseType.ecospold,
    )

    # importing biosphere through a biosphere importer that implements a progress_slot
    bio_import = ABEcospold2BiosphereImporter(
        name="biosphere3",
        filepath=lci_path / "MasterData" / "ElementaryExchanges.xml",
    )
    log.info("Applying strategies")
    bio_import.apply_strategies()
    log.info("Writing biosphere database")
    bio_import.write_database()
    bd.preferences["biosphere_database"] = "biosphere3"

    # importing ecoinvent through a ecospold2 importer that implements a progress_slot
    log.info("Importing ecoinvent")
    db_name = f"ecoinvent-{version}-{system_model}"
    ei_import = SingleOutputEcospold2Importer(
        dirpath=str(lci_path / "datasets"),
        db_name=db_name,
        biosphere_database_name="biosphere3",
    )
    log.info("Applying strategies")
    ei_import.apply_strategies()
    log.info("Writing ecoinvent database")
    ei_import.write_database()

    # importing all LCIA methods
    log.info("Gathering LCIA methods")
    lcia_file = ei.get_excel_lcia_file_for_version(release=release, version=version)
    sheet_names = get_excel_sheet_names(lcia_file)

    if "units" in sheet_names:
        units_sheetname = "units"
    elif "Indicators" in sheet_names:
        units_sheetname = "Indicators"
    else:
        raise ValueError(
            f"Can't find worksheet for impact category units in {sheet_names}"
        )

    if "CFs" not in sheet_names:
        raise ValueError(
            f"Can't find worksheet for characterization factors; expected `CFs`, found {sheet_names}"
        )
    log.info("Extracting LCIA methods")
    data = dict(ExcelExtractor.extract(lcia_file))
    units = header_dict(data[units_sheetname])

    log.info("Mapping LCIA methods")
    cfs = header_dict(data["CFs"])

    CF_COLUMN_LABELS = {
        "3.4": "cf 3.4",
        "3.5": "cf 3.5",
        "3.6": "cf 3.6",
    }
    cf_col_label = CF_COLUMN_LABELS.get(version, "cf")
    units_col_label = pick_a_unit_label_already(units[0])
    units_mapping = {
        (row["method"], row["category"], row["indicator"]): row[units_col_label]
        for row in units
    }

    biosphere_mapping = {}
    for flow in bd.Database("biosphere3"):
        biosphere_mapping[(flow["name"],) + tuple(flow["categories"])] = flow.key
        if flow["name"].startswith("[Deleted]"):
            biosphere_mapping[
                (flow["name"].replace("[Deleted]", ""),) + tuple(flow["categories"])
                ] = flow.key

    lcia_data_as_dict = defaultdict(list)

    unmatched = set()
    substituted = set()

    for row in cfs:
        impact_category = (row["method"], row["category"], row["indicator"])
        if row[cf_col_label] is None:
            continue
        try:
            lcia_data_as_dict[impact_category].append(
                (
                    biosphere_mapping[
                        drop_unspecified(
                            row["name"], row["compartment"], row["subcompartment"]
                        )
                    ],
                    float(row[cf_col_label]),
                )
            )
        except KeyError:
            # How is this possible? We are matching ecoinvent data against
            # ecoinvent data from the same release! And yet it moves...
            category = (
                (row["compartment"], row["subcompartment"])
                if row["subcompartment"].lower() != "unspecified"
                else (row["compartment"],)
            )
            same_context = {
                k[0]: v for k, v in biosphere_mapping.items() if k[1:] == category
            }
            candidates = sorted(
                [
                    (damerau_levenshtein(name, row["name"]), name)
                    for name in same_context
                ]
            )
            if (
                    candidates[0][0] < 3
                    and candidates[0][0] != candidates[1][0]
                    and candidates[0][1][0].lower() == row["name"][0].lower()
            ):
                new_name = candidates[0][1]
                pair = (new_name, row["name"])
                if pair not in substituted:
                    print(f"Substituting {new_name} for {row['name']}")
                    substituted.add(pair)
                lcia_data_as_dict[impact_category].append(
                    (
                        same_context[new_name],
                        float(row[cf_col_label]),
                    )
                )
            else:
                if row["name"] not in unmatched:
                    print(
                        "Skipping unmatched flow {}:({}, {})".format(
                            row["name"], row["compartment"], row["subcompartment"]
                        )
                    )
                    unmatched.add(row["name"])

    from activity_browser import signals
    from bw2data import methods
    signals.meta.blockSignals(True)
    signals.method.blockSignals(True)
    old = methods.data.copy()

    for key in pyprind.prog_bar(lcia_data_as_dict, title="Writing LCIA methods"):
        method = bd.Method(key)
        method.register(
            unit=units_mapping.get(key, "Unknown"),
            filepath=str(lcia_file),
            ecoinvent_version=version,
            database="biosphere3",
        )
        method.write(lcia_data_as_dict[key])

    signals.meta.blockSignals(False)
    signals.method.blockSignals(False)
    signals.meta.methods_changed.emit(old, methods.data)
