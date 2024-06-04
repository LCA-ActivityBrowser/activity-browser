from bw2io.importers.ecospold2_biosphere import *


class ABEcospold2BiosphereImporter(Ecospold2BiosphereImporter):

    def __init__(
        self,
        name: str = "biosphere3",
        version: str = "3.9",
        filepath: Path | None = None,
        progress_slot=lambda progress, message: None
    ):
        self.progress_slot = progress_slot
        super().__init__(name, version, filepath)

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
        no_children = len(root.getchildren())
        flow_data = []

        for i, ds in enumerate(root.iterchildren()):
            self.progress_slot(int(i / no_children * 100), "Extracting biosphere data")
            flow_data.append(extract_flow_data(ds))
        self.progress_slot(100, "Extracting biosphere data finished")
        return flow_data
