"""Distribution layout contract: conda recipe under packaging."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONDA_META = REPO_ROOT / "packaging" / "conda" / "meta.yaml"
ROOT_RECIPE = REPO_ROOT / "recipe"


def _source_path_from_meta(meta: Path) -> Path:
    """Read source.path from conda meta.yaml without a YAML dependency."""
    in_source = False
    for line in meta.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("{%"):
            continue
        if stripped.startswith("source:"):
            in_source = True
            continue
        if in_source:
            if stripped and not line[:1].isspace() and not stripped.startswith("#"):
                break
            if stripped.startswith("path:"):
                return Path(stripped.split(":", 1)[1].strip().split()[0])
    raise AssertionError(f"source.path not found in {meta}")


def test_conda_recipe_lives_under_packaging_not_root():
    """In-repo conda install-channel recipe is packaging/conda (hard-move)."""
    assert CONDA_META.is_file()
    assert not ROOT_RECIPE.exists()


def test_conda_recipe_source_path_points_at_repo_root():
    """conda-build source.path must resolve to the repository root."""
    source_path = _source_path_from_meta(CONDA_META)
    resolved = (CONDA_META.parent / source_path).resolve()
    assert resolved == REPO_ROOT.resolve()
