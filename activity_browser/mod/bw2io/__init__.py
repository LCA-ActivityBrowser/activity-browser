from bw2io import *

from activity_browser import log


def ab_bw2setup():
    from activity_browser.mod.bw2io.importers.ecospold2_biosphere import ABEcospold2BiosphereImporter
    from .migrations import ab_create_core_migrations

    ab_create_core_migrations()

    bio_import = ABEcospold2BiosphereImporter()
    bio_import.apply_strategies()
    log.info("Writing biosphere database")
    bio_import.write_database()
    log.info("Writing LCIA methods")
    create_default_lcia_methods()
