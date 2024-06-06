from bw2io import *


def ab_bw2setup():
    from activity_browser.mod.bw2io.importers.ecospold2_biosphere import ABEcospold2BiosphereImporter
    from .migrations import ab_create_core_migrations

    bio_import = ABEcospold2BiosphereImporter()
    bio_import.apply_strategies()
    bio_import.write_database()

    ab_create_core_migrations()

    ab_create_default_lcia_methods()


def ab_create_default_lcia_methods(progress_slot=lambda progress, message: None):
    import zipfile
    import json
    import bw2io
    from pathlib import Path
    from bw2io.importers.base_lcia import LCIAImporter

    fp = Path(bw2io.__file__).parent.resolve() / "data" / "lcia" / "lcia_39_ecoinvent.zip"

    with zipfile.ZipFile(fp, mode="r") as archive:
        data = json.load(archive.open("data.json"))

    for method in data:
        method['name'] = tuple(method['name'])
        for obj in method['exchanges']:
            obj['input'] = tuple(obj['input'])

    ei = LCIAImporter("lcia_39_ecoinvent.zip")
    ei.data = data
    ei.write_methods()

