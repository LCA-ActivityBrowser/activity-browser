"""Pedigree recipe: infer basic uncertainty and resolve what to persist on a flow."""
import math

import pytest
import stats_arrays as sa

from activity_browser.bwutils.pedigree import (
    PedigreeEditSession,
    infer_basic_uncertainty,
    resolve_pedigree_edit,
)
from activity_browser.bwutils.uncertainty import EMPTY_UNCERTAINTY


def test_infer_basic_uncertainty_all_perfect_scores():
    """All scores 1 contribute no extra spread; basic = exp(2 * scale)."""
    recipe = {
        "reliability": 1,
        "completeness": 1,
        "temporal correlation": 1,
        "geographical correlation": 1,
        "further technological correlation": 1,
    }
    assert infer_basic_uncertainty(recipe, scale=0.2) == pytest.approx(math.exp(0.4))


def test_infer_basic_uncertainty_none_when_scale_tighter_than_scores():
    recipe = {
        "reliability": 5,
        "completeness": 5,
        "temporal correlation": 5,
        "geographical correlation": 5,
        "further technological correlation": 5,
    }
    assert infer_basic_uncertainty(recipe, scale=0.001) is None


def test_incomplete_recipe_is_not_usable():
    from activity_browser.bwutils.pedigree import recipe_is_usable

    assert not recipe_is_usable({"reliability": 2})
    assert not recipe_is_usable(None)


def _perfect_recipe():
    return {
        "reliability": 1,
        "completeness": 1,
        "temporal correlation": 1,
        "geographical correlation": 1,
        "further technological correlation": 1,
    }


def _lognormal(loc=1.0, scale=0.2):
    return {
        **EMPTY_UNCERTAINTY,
        "uncertainty type": sa.LognormalUncertainty.id,
        "loc": loc,
        "scale": scale,
    }


def test_resolve_not_applying_untouched_does_not_write_pedigree():
    stored = _perfect_recipe()
    outcome = {
        "uncertainty": _lognormal(loc=1.1, scale=0.2),
        "pedigree_applying": False,
        "recipe_cleared": False,
        "recipe": {**stored, "basic uncertainty": math.exp(0.4)},
    }
    result = resolve_pedigree_edit(stored, outcome)
    assert "pedigree" not in result.write
    assert result.delete == ()
    assert result.write["loc"] == 1.1


def test_resolve_not_applying_never_writes_pedigree():
    stored = _perfect_recipe()
    recipe = {**stored, "reliability": 3, "basic uncertainty": 1.05}
    outcome = {
        "uncertainty": _lognormal(),
        "pedigree_applying": False,
        "recipe_cleared": False,
        "recipe": recipe,
    }
    result = resolve_pedigree_edit(stored, outcome)
    assert "pedigree" not in result.write
    assert result.delete == ()


def test_resolve_applying_keeps_imported_sample_size():
    stored = {**_perfect_recipe(), "sample size": 1}
    recipe = {**_perfect_recipe(), "reliability": 3, "basic uncertainty": 1.0}
    outcome = {
        "uncertainty": _lognormal(),
        "pedigree_applying": True,
        "recipe_cleared": False,
        "recipe": recipe,
    }
    result = resolve_pedigree_edit(stored, outcome)
    assert result.write["pedigree"]["sample size"] == 1
    assert result.write["pedigree"]["reliability"] == 3


def test_resolve_applying_sets_lognormal_scale_from_recipe():
    recipe = {**_perfect_recipe(), "reliability": 2, "basic uncertainty": 1.0}
    outcome = {
        "uncertainty": _lognormal(loc=0.5, scale=9.0),
        "pedigree_applying": True,
        "recipe_cleared": False,
        "recipe": recipe,
    }
    result = resolve_pedigree_edit(_perfect_recipe(), outcome)
    assert result.write["uncertainty type"] == sa.LognormalUncertainty.id
    assert result.write["loc"] == 0.5
    assert result.write["scale"] == pytest.approx(math.log(1.54) / 2)
    assert result.write["pedigree"]["reliability"] == 2
    assert result.write["pedigree"]["basic uncertainty"] == pytest.approx(1.0)


def test_pedigree_factors_tuple_omits_basic_uncertainty():
    from activity_browser.bwutils.pedigree import PedigreeMatrix

    matrix = PedigreeMatrix.from_dict({**_perfect_recipe(), "basic uncertainty": 1.5})
    assert 1.5 not in matrix.factors_as_tuple()
    assert matrix.factors_as_tuple()[:5] == (1, 1, 1, 1, 1)


def test_resolve_cleared_deletes_pedigree_and_keeps_sampled_uncertainty():
    outcome = {
        "uncertainty": _lognormal(loc=0.3, scale=0.1),
        "pedigree_applying": False,
        "recipe_cleared": True,
        "recipe": None,
    }
    result = resolve_pedigree_edit(_perfect_recipe(), outcome)
    assert result.delete == ("pedigree",)
    assert "pedigree" not in result.write
    assert result.write["loc"] == 0.3


def test_resolve_applying_without_recipe_is_invalid():
    outcome = {
        "uncertainty": _lognormal(),
        "pedigree_applying": True,
        "recipe_cleared": False,
        "recipe": None,
    }
    with pytest.raises(ValueError):
        resolve_pedigree_edit(None, outcome)


def test_from_dict_ignores_basic_uncertainty_key():
    from activity_browser.bwutils.pedigree import PedigreeMatrix

    matrix = PedigreeMatrix.from_dict({**_perfect_recipe(), "basic uncertainty": 1.5})
    assert "basic uncertainty" not in matrix.factors


def test_uncertainty_cell_includes_pedigree_scores_not_basic():
    from activity_browser.bwutils.uncertainty import uncertainty_cell_summary

    sampled = _lognormal(loc=0.0, scale=0.2)
    recipe = {**_perfect_recipe(), "reliability": 2, "basic uncertainty": 1.5}
    text = uncertainty_cell_summary(sampled, pedigree=recipe)
    assert text.startswith("Lognormal")
    assert "pedigree: 2, 1, 1, 1, 1" in text
    assert "1.5" not in text


def test_uncertainty_cell_shows_pedigree_when_distribution_is_not_lognormal():
    from activity_browser.bwutils.uncertainty import uncertainty_cell_summary

    sampled = {
        **EMPTY_UNCERTAINTY,
        "uncertainty type": sa.UniformUncertainty.id,
        "minimum": 0.0,
        "maximum": 1.0,
    }
    text = uncertainty_cell_summary(sampled, pedigree=_perfect_recipe())
    assert "Uniform" in text
    assert "pedigree: 1, 1, 1, 1, 1" in text


def test_display_basic_uncertainty_stored_wins_over_infer():
    from activity_browser.bwutils.pedigree import display_basic_uncertainty

    recipe = {**_perfect_recipe(), "basic uncertainty": 1.2}
    assert display_basic_uncertainty(
        recipe, scale=0.2, uncertainty_type=sa.LognormalUncertainty.id
    ) == pytest.approx(1.2)


def test_display_basic_uncertainty_infers_when_unset():
    from activity_browser.bwutils.pedigree import display_basic_uncertainty

    assert display_basic_uncertainty(
        _perfect_recipe(), scale=0.2, uncertainty_type=sa.LognormalUncertainty.id
    ) == pytest.approx(math.exp(0.4))


def _uniform():
    return {
        **EMPTY_UNCERTAINTY,
        "uncertainty type": sa.UniformUncertainty.id,
        "minimum": 0.0,
        "maximum": 1.0,
    }


def test_session_opens_not_using_pedigree():
    stored = _perfect_recipe()
    session = PedigreeEditSession(_uniform(), stored)
    assert session.use_pedigree is False
    assert session.recipe_cleared is False
    assert session.sampled["uncertainty type"] == sa.UniformUncertainty.id
    outcome = session.outcome()
    assert outcome["pedigree_applying"] is False
    assert outcome["recipe_cleared"] is False


def test_session_check_forces_lognormal_scale_from_recipe():
    stored = {**_perfect_recipe(), "reliability": 2}
    session = PedigreeEditSession(_uniform(), stored)
    session.check_use()
    assert session.use_pedigree is True
    assert session.sampled["uncertainty type"] == sa.LognormalUncertainty.id
    assert session.sampled["scale"] == pytest.approx(math.log(1.54) / 2)
    assert session.sampled["minimum"] == 0.0
    outcome = session.outcome()
    assert outcome["pedigree_applying"] is True
    assert outcome["recipe"]["reliability"] == 2


def test_session_uncheck_restores_negative_flag():
    sampled = {
        **EMPTY_UNCERTAINTY,
        "uncertainty type": sa.GammaUncertainty.id,
        "shape": 2.0,
        "scale": 1.0,
        "loc": 0.0,
        "negative": True,
    }
    session = PedigreeEditSession(sampled, _perfect_recipe())
    session.check_use()
    session.uncheck_use()
    assert session.sampled["negative"] is True
    assert session.sampled["uncertainty type"] == sa.GammaUncertainty.id


def test_session_uncheck_restores_pre_check_sampled_fields():
    session = PedigreeEditSession(_uniform(), _perfect_recipe())
    session.check_use()
    session.uncheck_use()
    assert session.use_pedigree is False
    assert session.sampled["uncertainty type"] == sa.UniformUncertainty.id
    assert session.sampled["minimum"] == 0.0
    assert session.sampled["maximum"] == 1.0


def test_session_uncheck_discards_score_edits():
    stored = {**_perfect_recipe(), "reliability": 2}
    session = PedigreeEditSession(_uniform(), stored)
    session.check_use()
    session.edit_recipe({**session.recipe, "reliability": 5})
    session.uncheck_use()
    session.check_use()
    assert session.recipe["reliability"] == 2


def test_session_distribution_change_keeps_new_type():
    session = PedigreeEditSession(_lognormal(), _perfect_recipe())
    session.check_use()
    session.set_sampled(_uniform())
    session.stop_using_keep_sampled()
    assert session.use_pedigree is False
    assert session.sampled["uncertainty type"] == sa.UniformUncertainty.id
    assert session.sampled["minimum"] == 0.0
    assert session.outcome()["recipe_cleared"] is False


def test_session_scale_edit_keeps_new_scale():
    session = PedigreeEditSession(_lognormal(loc=0.5, scale=0.2), _perfect_recipe())
    session.check_use()
    session.set_sampled(_lognormal(loc=0.5, scale=0.9))
    session.stop_using_keep_sampled()
    assert session.use_pedigree is False
    assert session.sampled["scale"] == pytest.approx(0.9)
    assert session.sampled["loc"] == pytest.approx(0.5)


def test_session_clear_restores_and_marks_delete():
    session = PedigreeEditSession(_uniform(), _perfect_recipe())
    session.check_use()
    session.clear()
    assert session.use_pedigree is False
    assert session.recipe_cleared is True
    assert session.sampled["uncertainty type"] == sa.UniformUncertainty.id
    outcome = session.outcome()
    assert outcome["recipe_cleared"] is True
    assert outcome["pedigree_applying"] is False
    assert outcome["recipe"] is None


def test_session_check_after_clear_restores_stored_recipe():
    stored = {**_perfect_recipe(), "reliability": 4}
    session = PedigreeEditSession(_uniform(), stored)
    session.check_use()
    session.clear()
    session.check_use()
    assert session.recipe_cleared is False
    assert session.recipe["reliability"] == 4
    assert session.use_pedigree is True


def test_session_no_stored_recipe_defaults_scores_and_basic_to_one():
    session = PedigreeEditSession(_uniform(), None)
    session.check_use()
    assert session.recipe["reliability"] == 1
    assert session.recipe["completeness"] == 1
    assert session.recipe["basic uncertainty"] == pytest.approx(1.0)
    assert session.sampled["scale"] == pytest.approx(0.0)


def test_session_malformed_stored_recipe_uses_defaults():
    session = PedigreeEditSession(_uniform(), {"reliability": 2})
    session.check_use()
    assert session.recipe["reliability"] == 1
    assert session.recipe["basic uncertainty"] == pytest.approx(1.0)


def test_session_loc_edit_while_using_does_not_stop():
    session = PedigreeEditSession(_lognormal(loc=0.5, scale=0.2), _perfect_recipe())
    session.check_use()
    session.set_sampled({**session.sampled, "loc": 1.2})
    assert session.use_pedigree is True
    assert session.sampled["loc"] == pytest.approx(1.2)


def test_session_stored_basic_used_when_checking():
    stored = {**_perfect_recipe(), "basic uncertainty": 1.2}
    session = PedigreeEditSession(_lognormal(), stored)
    session.check_use()
    assert session.recipe["basic uncertainty"] == pytest.approx(1.2)


def test_session_infers_basic_when_checking_lognormal_without_stored_basic():
    stored = _perfect_recipe()
    session = PedigreeEditSession(_lognormal(loc=1.0, scale=0.2), stored)
    session.check_use()
    assert session.recipe["basic uncertainty"] == pytest.approx(math.exp(0.4))
    assert session.sampled["scale"] == pytest.approx(0.2)


def test_session_check_outcome_resolver_writes_recipe():
    stored = {**_perfect_recipe(), "reliability": 2}
    session = PedigreeEditSession(_uniform(), stored)
    session.check_use()
    result = resolve_pedigree_edit(stored, session.outcome())
    assert result.write["uncertainty type"] == sa.LognormalUncertainty.id
    assert result.write["pedigree"]["reliability"] == 2
    assert result.delete == ()


def test_session_uncheck_outcome_resolver_does_not_write_pedigree():
    stored = _perfect_recipe()
    session = PedigreeEditSession(_uniform(), stored)
    session.check_use()
    session.uncheck_use()
    result = resolve_pedigree_edit(stored, session.outcome())
    assert "pedigree" not in result.write
    assert result.delete == ()
    assert result.write["uncertainty type"] == sa.UniformUncertainty.id
