from bw2io.importers.ecospold2_biosphere import *
import pyprind
import logging


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
