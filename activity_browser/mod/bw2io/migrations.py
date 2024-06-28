from bw2io.migrations import *

from pyprind import ProgBar

def ab_create_core_migrations():
    """Activity Browser version of bw2io.migrations.create_core_migrations that employs a progress slot"""
    bar = ProgBar(12, title="Creating migrations")

    bar.title = "Creating migration: biosphere-2-3-categories"
    bar.update(0)
    Migration("biosphere-2-3-categories").write(
        get_biosphere_2_3_category_migration_data(),
        "Change biosphere category and subcategory labels to ecoinvent version 3",
    )

    bar.title = "Creating migration: biosphere-2-3-names"
    bar.update()
    Migration("biosphere-2-3-names").write(
        get_biosphere_2_3_name_migration_data(),
        "Change biosphere flow names to ecoinvent version 3",
    )

    bar.title = "Creating migration: simapro-ecoinvent-3.1"
    bar.update()
    Migration("simapro-ecoinvent-3.1").write(
        get_simapro_ecoinvent_3_migration_data("3.1"),
        "Change SimaPro names from ecoinvent 3.1 to ecoinvent names",
    )

    bar.title = "Creating migration: simapro-ecoinvent-3.2"
    bar.update()
    Migration("simapro-ecoinvent-3.2").write(
        get_simapro_ecoinvent_3_migration_data("3.2"),
        "Change SimaPro names from ecoinvent 3.2 to ecoinvent names",
    )

    bar.title = "Creating migration: simapro-ecoinvent-3.3"
    bar.update()
    Migration("simapro-ecoinvent-3.3").write(
        get_simapro_ecoinvent_3_migration_data("3.3"),
        "Change SimaPro names from ecoinvent 3.3 to ecoinvent names",
    )

    bar.title = "Creating migration: simapro-ecoinvent-3.4"
    bar.update()
    Migration("simapro-ecoinvent-3.4").write(
        get_simapro_ecoinvent_3_migration_data("3.4"),
        "Change SimaPro names from ecoinvent 3.4 to ecoinvent names",
    )

    bar.title = "Creating migration: simapro-water"
    bar.update()
    Migration("simapro-water").write(
        get_simapro_water_migration_data(),
        "Change SimaPro water flows to more standard names",
    )

    bar.title = "Creating migration: us-lci"
    bar.update()
    Migration("us-lci").write(
        get_us_lci_migration_data(), "Fix names in US LCI database"
    )

    bar.title = "Creating migration: default-units"
    bar.update()
    Migration("default-units").write(
        get_default_units_migration_data(), "Convert to default units"
    )

    bar.title = "Creating migration: unusual-units"
    bar.update()
    Migration("unusual-units").write(
        get_unusual_units_migration_data(), "Convert non-Ecoinvent units"
    )

    bar.title = "Creating migration: exiobase-biosphere"
    bar.update()
    Migration("exiobase-biosphere").write(
        get_exiobase_biosphere_migration_data(),
        "Change biosphere flow names to ecoinvent version 3",
    )

    bar.title = "Creating migration: fix-ecoinvent-flows-pre-35"
    bar.update()
    Migration("fix-ecoinvent-flows-pre-35").write(
        get_ecoinvent_pre35_migration_data(),
        "Update new biosphere UUIDs in Consequential 3.4",
    )
    bar.update()
