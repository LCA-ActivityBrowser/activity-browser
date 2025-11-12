from loguru import logger

from bw2io import *

import bw2io.remote as remote







def ab_bw2setup(version):

    raise Exception("This function is deprecated.")

    import bw2io as bi
    from activity_browser.mod.bw2io.importers.ecospold2_biosphere import ABEcospold2BiosphereImporter
    from activity_browser.info import __ei_versions__
    from .migrations import ab_create_core_migrations

    ab_create_core_migrations()

    version = version[:3]

    if version == __ei_versions__[0][:3]:
        logger.info(f"Installing biosphere version >{version}<")
        # most recent version
        bio_import = ABEcospold2BiosphereImporter()
    else:
        logger.info(f"Installing legacy biosphere version >{version}<")
        # not most recent version, import legacy biosphere from AB
        bio_import = ABEcospold2BiosphereImporter(version=version)
    bio_import.apply_strategies()
    logger.info("Writing biosphere database")
    bio_import.write_database()

    logger.info("Writing LCIA methods")
    create_default_lcia_methods()

    # patching biosphere
    sorted_versions = sort_semantic_versions(
        __ei_versions__, highest_to_lowest=False
    )
    ei_versions = sorted_versions[: sorted_versions.index(version) + 1]

    patches = [
        patch
        for patch in dir(bi.data)
        if patch.startswith("add_ecoinvent")
        and patch.endswith("biosphere_flows")
        and any(version.replace(".", "") in patch for version in ei_versions)
    ]

    for patch in patches:
        logger.info(f"Applying biosphere patch: {patch}")
        update_bio = getattr(bi.data, patch)
        update_bio()

