import os
from zipfile import ZipFile
from logging import getLogger

from bw2io.importers import Ecospold2BiosphereImporter
from bw2io.importers.ecospold2_biosphere import EMISSIONS_CATEGORIES
from lxml import objectify

from activity_browser.mod import bw2data as bd

from ...info import __ei_versions__
from ...utils import sort_semantic_versions

log = getLogger(__name__)


def create_default_biosphere3(version) -> None:
    """Reimplementation of bw.create_default_biosphere3 to allow import from older biosphere versions."""
    # format version number to only Major/Minor
    version = version[:3]

    if version == sort_semantic_versions(__ei_versions__)[0][:3]:
        log.debug(f"Installing biosphere version >{version}<")
        # most recent version
        eb = Ecospold2BiosphereImporter()
    else:
        log.debug(f"Installing legacy biosphere version >{version}<")
        # not most recent version, import legacy biosphere from AB
        eb = ABEcospold2BiosphereImporter(version=version)
    eb.apply_strategies()
    eb.write_database()


class ABEcospold2BiosphereImporter(Ecospold2BiosphereImporter):
    """Reimplementation of bw2io.importers Ecospold2BiosphereImporter to import legacy biosphere from AB data"""

    def extract(self, version, filepath=None):
        def extract_flow_data(o):
            ds = {
                "categories": (
                    o.compartment.compartment.text,
                    o.compartment.subcompartment.text,
                ),
                "code": o.get("id"),
                "CAS number": o.get("casNumber"),
                "name": o.name.text,
                "database": self.db_name,
                "exchanges": [],
                "unit": o.unitName.text,
            }
            ds["type"] = EMISSIONS_CATEGORIES.get(
                ds["categories"][0], ds["categories"][0]
            )
            return ds

        lci_dirpath = os.path.join(os.path.dirname(__file__), "legacy_biosphere")

        # find the most recent legacy biosphere that is equal to or older than chosen version
        for ei_version in sort_semantic_versions(__ei_versions__):
            use_version = ei_version
            fp = os.path.join(
                lci_dirpath, f"ecoinvent elementary flows {use_version}.xml.zip"
            )
            if sort_semantic_versions([version, ei_version])[
                0
            ] == version and os.path.isfile(fp):
                # this version is equal/lower and available
                break

        # extract the xml from the zip
        with ZipFile(fp) as zipped_file:
            with zipped_file.open(
                f"ecoinvent elementary flows {use_version}.xml"
            ) as file:
                root = objectify.parse(file).getroot()

        log.debug(f"Installing biosphere {use_version} for chosen version {version}")
        flow_data = bd.utils.recursive_str_to_unicode(
            [extract_flow_data(ds) for ds in root.iterchildren()]
        )

        return flow_data
