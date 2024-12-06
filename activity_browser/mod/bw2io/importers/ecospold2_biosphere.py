from zipfile import ZipFile

from bw2io.importers.ecospold2_biosphere import *
import pyprind
import logging
import os

from activity_browser.info import __ei_versions__
from activity_browser.utils import sort_semantic_versions


class ABEcospold2BiosphereImporter(Ecospold2BiosphereImporter):

    def extract(self, version: str | None, filepath: Path | None):
        """
        Extract elementary flows from the xml file.

        Parameters
        ----------
        version
            Version of the database if using default data.
        filepath
            File path of user-specified data file

        Returns
        -------
        list
            Extracted data from the xml file.
        """

        def extract_flow_data(o):
            ds = {
                "categories": (
                    o.compartment.compartment.text,
                    o.compartment.subcompartment.text,
                ),
                "code": o.get("id"),
                "CAS number": o.get("casNumber"),
                "synonyms": [
                    elem.text.strip()
                    for elem in o.iterchildren()
                    if elem.tag == "{http://www.EcoInvent.org/EcoSpold02}synonym"
                    and elem.text  # 3.7.1 has blank elements
                    and elem.text.strip()
                ],
                "name": o.name.text,
                "database": self.db_name,
                "exchanges": [],
                "unit": o.unitName.text,
            }
            ds["type"] = EMISSIONS_CATEGORIES.get(
                ds["categories"][0], ds["categories"][0]
            )
            return ds

        if version != '3.9' and not filepath:
            import activity_browser.bwutils as mod
            lci_dirpath = os.path.join(os.path.dirname(mod.__file__), "ecoinvent_biosphere_versions", "legacy_biosphere")

            # find the most recent legacy biosphere that is equal to or older than chosen version
            for ei_version in sort_semantic_versions(__ei_versions__):
                use_version = ei_version
                zip_fp = os.path.join(
                    lci_dirpath, f"ecoinvent elementary flows {use_version}.xml.zip"
                )
                if sort_semantic_versions([version, ei_version])[
                    0
                ] == version and os.path.isfile(zip_fp):
                    # this version is equal/lower and available
                    break

            # extract the xml from the zip
            with ZipFile(zip_fp) as zipped_file:
                with zipped_file.open(
                        f"ecoinvent elementary flows {use_version}.xml"
                ) as file:
                    root = objectify.parse(file).getroot()
        else:
            if not filepath:
                import bw2io.importers.ecospold2_biosphere as mod
                filepath = (
                    Path(mod.__file__).parent.parent.resolve()
                    / "data"
                    / "lci"
                    / f"ecoinvent elementary flows {version}.xml"
                )

            root = objectify.parse(open(filepath, encoding="utf-8")).getroot()

        flow_data = []

        # AB implementation: added prog_bar here
        for ds in pyprind.prog_bar(list(root.iterchildren()), title="Extracting biosphere data"):
            flow_data.append(extract_flow_data(ds))
        return flow_data

    def apply_strategies(self, strategies=None, verbose=True):
        """Apply a list of strategies.

        Uses the default list ``self.strategies`` if ``strategies`` is ``None``.

        Args:
            *strategies* (list, optional): List of strategies to apply. Defaults to ``self.strategies``.

        Returns:
            Nothings, but modifies ``self.data``, and adds each strategy to ``self.applied_strategies``.

        """
        func_list = self.strategies if strategies is None else strategies
        for func in pyprind.prog_bar(func_list, title="Applying strategies"):
            self.apply_strategy(func, verbose)

    def write_database(self, *args, **kwargs):
        logging.getLogger(__name__).info("Writing Biosphere database")
        super().write_database(*args, **kwargs)
