# -*- coding: utf-8 -*
"""
Code in `pedigree.py` is taken wholesale from the https://bitbucket.org/cmutel/pedigree-matrix/src repository,
which is published by Chris Mutel under an MIT license (2012).

FUTURE WORK?
'The application of the pedigree approach to the distributions foreseen in ecoinvent v3'
(doi: 10.1007/s11367-014-0759-5) reveals the formulas used to convert the calculated sigma
(+ geometric standard deviation) into the coefficient of variation ('CV').
In turn, this CV can then be used to generate required values for a number of other uncertainty distributions.

Any additions made should improve the transition of the calculated sigma (or Geometric Standard Deviation/GSD)
smoothly into the related uncertainty distributions.
"""
import math
from typing import NamedTuple
from pprint import pformat

from bw2data.parameters import ParameterBase
from bw2data.proxies import ExchangeProxyBase

VERSION_2 = {
    "reliability": (1.0, 1.54, 1.61, 1.69, 1.69),
    "completeness": (1.0, 1.03, 1.04, 1.08, 1.08),
    "temporal correlation": (1.0, 1.03, 1.1, 1.19, 1.29),
    "geographical correlation": (1.0, 1.04, 1.08, 1.11, 1.11),
    "further technological correlation": (1.0, 1.18, 1.65, 2.08, 2.8),
    "sample size": (1.0, 1.0, 1.0, 1.0, 1.0),
}


class PedigreeMatrix(object):
    __slots__ = ["factors"]
    labels = (
        "reliability",
        "completeness",
        "temporal correlation",
        "geographical correlation",
        "further technological correlation",
        "sample size",
    )

    def __init__(self):
        self.factors = {}

    @classmethod
    def from_numbers(cls, data: tuple) -> "PedigreeMatrix":
        """Takes a tuple of integers and construct a PedigreeMatrix."""
        assert len(data) in (5, 6), "Must provide either 5 or 6 factors"
        if len(data) == 5:
            data = data + (1,)
        matrix = cls()
        for index, factor in enumerate(data):
            matrix.factors[cls.labels[index]] = factor
        return matrix

    @classmethod
    def from_dict(cls, data: dict) -> "PedigreeMatrix":
        return cls.from_numbers(tuple(data.get(k) for k in cls.labels if k in data))

    @classmethod
    def from_bw_object(cls, obj) -> "PedigreeMatrix":
        if isinstance(obj, ExchangeProxyBase):
            return cls.from_dict(obj.get("pedigree", {}))
        elif isinstance(obj, ParameterBase) and "pedigree" in obj.data:
            return cls.from_dict(obj.data.get("pedigree", {}))
        else:
            raise AssertionError("Could not find pedigree in object")

    def calculate(
        self, basic_uncertainty: float = 1.0, as_geometric_sigma: bool = False
    ) -> float:
        """Calculates the sigma or geometric standard deviation from the factors."""
        values = [basic_uncertainty] + self.get_values()
        sigma = math.sqrt(sum([math.log(x) ** 2 for x in values])) / 2
        return sigma if not as_geometric_sigma else math.exp(2 * sigma)

    def get_values(self) -> list:
        assert self.factors, "Must provide Pedigree Matrix factors"
        return [VERSION_2[key][index - 1] for key, index in self.factors.items()]

    def factors_as_tuple(self):
        return tuple(self.factors[k] for k in self.labels if k in self.factors)

    def __repr__(self) -> str:
        return "Empty Pedigree Matrix" if not self.factors else pformat(self.factors)


SCORE_KEYS = (
    "reliability",
    "completeness",
    "temporal correlation",
    "geographical correlation",
    "further technological correlation",
)
BASIC_UNCERTAINTY_KEY = "basic uncertainty"


def infer_basic_uncertainty(recipe: dict, scale: float) -> float | None:
    """Recover basic uncertainty from a lognormal scale and pedigree scores.

    Inverse of ``PedigreeMatrix.calculate``. Returns ``None`` when scores are
    unusable or the scale is tighter than the scores alone allow.
    """
    try:
        scores = {key: recipe[key] for key in SCORE_KEYS if key in recipe}
        matrix = PedigreeMatrix.from_dict(scores)
        pedigree_ssq = sum(math.log(x) ** 2 for x in matrix.get_values())
    except (AssertionError, KeyError, TypeError, ValueError):
        return None
    residual = (2.0 * float(scale)) ** 2 - pedigree_ssq
    if residual < 0 or math.isnan(residual):
        return None
    return math.exp(math.sqrt(residual))


def _scores_only(recipe: dict | None) -> dict:
    if not recipe:
        return {}
    return {key: int(recipe[key]) for key in SCORE_KEYS if key in recipe}


def recipe_is_usable(recipe: dict | None) -> bool:
    if not recipe:
        return False
    scores = _scores_only(recipe)
    if set(scores) != set(SCORE_KEYS):
        return False
    return all(1 <= scores[key] <= 5 for key in SCORE_KEYS)


def recipe_for_storage(recipe: dict, stored: dict | None = None) -> dict:
    out = _scores_only(recipe)
    basic = recipe.get(BASIC_UNCERTAINTY_KEY, 1.0)
    out[BASIC_UNCERTAINTY_KEY] = 1.0 if basic is None else float(basic)
    if stored and "sample size" in stored:
        out["sample size"] = stored["sample size"]
    return out


def pedigree_scores_suffix(recipe: dict | None) -> str:
    """Cell text for stored scores (not basic uncertainty). Empty if unusable."""
    if not recipe_is_usable(recipe):
        return ""
    scores = _scores_only(recipe)
    joined = ", ".join(str(scores[key]) for key in SCORE_KEYS)
    return f"pedigree: {joined}"


def display_basic_uncertainty(
    recipe: dict | None, *, scale: float, uncertainty_type: int
) -> float:
    """Basic uncertainty to show in the dialog: stored, else inferred, else 1."""
    if recipe:
        stored = recipe.get(BASIC_UNCERTAINTY_KEY)
        if stored is not None:
            try:
                value = float(stored)
                if math.isfinite(value) and value > 0:
                    return value
            except (TypeError, ValueError):
                pass
        try:
            from stats_arrays.distributions import LognormalUncertainty

            is_lognormal = int(uncertainty_type) == LognormalUncertainty.id
        except Exception:
            is_lognormal = int(uncertainty_type) == 2
        if is_lognormal:
            inferred = infer_basic_uncertainty(recipe, scale)
            if inferred is not None:
                return inferred
    return 1.0


def _copy_sampled(sampled: dict) -> dict:
    return {key: value for key, value in sampled.items() if key != "pedigree"}


def _default_editor_recipe() -> dict:
    return {key: 1 for key in SCORE_KEYS} | {BASIC_UNCERTAINTY_KEY: 1.0}


def _editor_recipe_from_stored(stored: dict | None, sampled: dict) -> dict:
    if not recipe_is_usable(stored):
        return _default_editor_recipe()
    try:
        scale = float(sampled.get("scale", float("nan")))
        uncertainty_type = int(sampled.get("uncertainty type") or 0)
    except (TypeError, ValueError):
        scale, uncertainty_type = float("nan"), 0
    basic = display_basic_uncertainty(
        stored, scale=scale, uncertainty_type=uncertainty_type
    )
    return {**_scores_only(stored), BASIC_UNCERTAINTY_KEY: basic}


def _scale_from_recipe(recipe: dict) -> float:
    matrix = PedigreeMatrix.from_dict(_scores_only(recipe))
    basic = recipe.get(BASIC_UNCERTAINTY_KEY, 1.0)
    return matrix.calculate(1.0 if basic is None else float(basic))


class PedigreeEditSession:
    """In-dialog pedigree mode: check/uncheck/clear without Qt."""

    def __init__(self, sampled: dict, stored: dict | None):
        self.stored = stored if isinstance(stored, dict) else None
        self.sampled = _copy_sampled(sampled)
        self.use_pedigree = False
        self.recipe_cleared = False
        self.snapshot = None
        self.recipe = _editor_recipe_from_stored(self.stored, self.sampled)

    def check_use(self) -> None:
        if self.use_pedigree:
            return
        self.recipe_cleared = False
        self.recipe = _editor_recipe_from_stored(self.stored, self.sampled)
        self.snapshot = _copy_sampled(self.sampled)
        self.use_pedigree = True
        self._apply_recipe_to_sampled()

    def uncheck_use(self) -> None:
        self._leave_use(restore=True, cleared=False)

    def stop_using_keep_sampled(self) -> None:
        self._leave_use(restore=False, cleared=False)

    def clear(self) -> None:
        self._leave_use(restore=True, cleared=True)

    def edit_recipe(self, recipe: dict) -> None:
        if not self.use_pedigree:
            return
        self.recipe = dict(recipe)
        self._apply_recipe_to_sampled()

    def set_sampled(self, sampled: dict) -> None:
        self.sampled = _copy_sampled(sampled)

    def outcome(self) -> dict:
        return {
            "uncertainty": _copy_sampled(self.sampled),
            "pedigree_applying": bool(self.use_pedigree),
            "recipe_cleared": bool(self.recipe_cleared),
            "recipe": None if self.recipe_cleared else dict(self.recipe),
        }

    def _leave_use(self, *, restore: bool, cleared: bool) -> None:
        if not self.use_pedigree:
            return
        if restore and self.snapshot is not None:
            self.sampled = _copy_sampled(self.snapshot)
        self.snapshot = None
        self.use_pedigree = False
        self.recipe_cleared = cleared
        self.recipe = _editor_recipe_from_stored(self.stored, self.sampled)

    def _apply_recipe_to_sampled(self) -> None:
        from stats_arrays.distributions import LognormalUncertainty

        self.sampled["uncertainty type"] = LognormalUncertainty.id
        self.sampled["scale"] = _scale_from_recipe(self.recipe)


class PedigreeEditResult(NamedTuple):
    write: dict
    delete: tuple[str, ...] = ()


def resolve_pedigree_edit(stored: dict | None, outcome: dict) -> PedigreeEditResult:
    """Decide sampled-uncertainty writes and pedigree deletes from a dialog outcome."""
    write = {
        key: value
        for key, value in (outcome.get("uncertainty") or {}).items()
        if key != "pedigree"
    }
    if outcome.get("recipe_cleared"):
        return PedigreeEditResult(write=write, delete=("pedigree",))
    recipe = outcome.get("recipe")
    if not outcome.get("pedigree_applying"):
        return PedigreeEditResult(write=write)
    if not recipe_is_usable(recipe):
        raise ValueError("Cannot apply pedigree without a usable recipe")
    from stats_arrays.distributions import LognormalUncertainty

    write["uncertainty type"] = LognormalUncertainty.id
    write["scale"] = _scale_from_recipe(recipe)
    write["pedigree"] = recipe_for_storage(recipe, stored)
    return PedigreeEditResult(write=write)
