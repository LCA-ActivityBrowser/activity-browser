"""Resolve and copy impact-category interchange templates."""
from __future__ import annotations

import shutil
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates" / "impact-categories"

# kind -> files relative to TEMPLATES_DIR (csv kinds are pairs)
TEMPLATE_FILES = {
    "ab-xlsx": ("ab-lcia.xlsx",),
    "ab-csv": ("ab-lcia.cfs.csv", "ab-lcia.metadata.csv"),
    "bw2io-xlsx": ("bw2io-lcia.xlsx",),
    "bw2io-csv": ("bw2io-lcia.csv", "bw2io-lcia.metadata.csv"),
}

TEMPLATE_LABELS = {
    "ab-xlsx": "AB impact-category file (Excel) — multi–IC; recommended",
    "ab-csv": "AB impact-category file (CSV pair) — multi–IC",
    "bw2io-xlsx": "bw2io impact-category file (Excel) — one IC per file",
    "bw2io-csv": "bw2io impact-category file (CSV) — one IC per file + metadata sidecar",
}


def template_paths(kind: str) -> list[Path]:
    if kind not in TEMPLATE_FILES:
        raise ValueError(f"Unknown impact-category template kind: {kind}")
    paths = [TEMPLATES_DIR / name for name in TEMPLATE_FILES[kind]]
    missing = [p for p in paths if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"Template file(s) not found: {missing}")
    return paths


def copy_impact_category_template(kind: str, destination: Path) -> list[Path]:
    """
    Copy template file(s) for ``kind`` to ``destination``.

    For single-file kinds, ``destination`` is the target file path.
    For CSV pairs, ``destination`` is a directory or a base stem path; both
    siblings are written beside/into it.
    """
    sources = template_paths(kind)
    destination = Path(destination)
    written: list[Path] = []

    if len(sources) == 1:
        dest = destination
        if dest.is_dir():
            dest = dest / sources[0].name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sources[0], dest)
        written.append(dest)
        return written

    # CSV pair
    if destination.suffix:
        # treat as stem path (possibly with .csv)
        directory = destination.parent
        stem = destination.name
        for suffix in (".cfs.csv", ".metadata.csv", ".impact-categories.csv", ".csv"):
            if stem.lower().endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        else:
            stem = destination.stem
    else:
        directory = destination if destination.suffix == "" else destination.parent
        if destination.exists() and destination.is_dir():
            directory = destination
            stem = sources[0].name.split(".")[0]
        else:
            directory = destination.parent
            stem = destination.name or sources[0].name.split(".")[0]

    directory.mkdir(parents=True, exist_ok=True)
    for source in sources:
        # preserve meaningful suffixes after the shared stem prefix of the packaged name
        # e.g. ab-lcia.cfs.csv -> {stem}.cfs.csv
        name = source.name
        packaged_stem = name.split(".")[0]
        remainder = name[len(packaged_stem) :]  # includes leading dots/suffixes
        dest = directory / f"{stem}{remainder}"
        shutil.copy2(source, dest)
        written.append(dest)
    return written
