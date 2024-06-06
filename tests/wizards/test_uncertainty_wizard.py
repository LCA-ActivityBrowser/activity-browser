# -*- coding: utf-8 -*-
import logging
import sys

from bw2data.parameters import ProjectParameter
import numpy as np
from PySide2.QtWidgets import QMessageBox, QWizard
import pytest
from stats_arrays.distributions import (
    LognormalUncertainty, UniformUncertainty, UndefinedUncertainty,
    TriangularUncertainty
)

from activity_browser.ui.wizards import UncertaintyWizard
from activity_browser.signals import qparameters

"""
Mess around with the uncertainty wizard.
"""


@pytest.mark.skipif(sys.platform=='darwin', reason="tests segfaults on osx")
def test_wizard_fail(ab_app, qtbot):
    """Can't create a wizard if no uncertainty interface exists."""
    mystery_box = ["Hello", "My", "Name", "Is", "Error"]  # Type is list.
    with pytest.raises(TypeError):
        UncertaintyWizard(mystery_box)


@pytest.mark.skipif(sys.platform=='darwin', reason="tests segfaults on osx")
def test_uncertainty_wizard_simple(ab_app, qtbot, caplog):
    """Use extremely simple text to open the wizard and go to all the pages."""
    caplog.set_level(logging.INFO)
    param = ProjectParameter.create(name="test1", amount=3)
    wizard = UncertaintyWizard(param, None)
    qtbot.addWidget(wizard)
    wizard.show()

    assert "uncertainty type" in wizard.uncertainty_info
    wizard.extract_uncertainty()
    wizard.extract_lognormal_loc()

    # Go to the pedigree page
    with qtbot.waitSignal(wizard.currentIdChanged, timeout=100):
        wizard.type.pedigree.click()

    # Pedigree is empty, so complaint is issued.
    captured = caplog.text
    assert "Could not extract pedigree data" in captured

    # Now go back for giggles.
    with qtbot.waitSignal(wizard.currentIdChanged, timeout=100):
        wizard.button(QWizard.BackButton).click()
    assert not wizard.using_pedigree


@pytest.mark.skipif(sys.platform=='darwin', reason="tests segfaults on osx")
def test_graph_rebuild(ab_app, qtbot):
    """Test that the graph is correctly built and rebuilt, ensure
    that the 'finish' button is enabled and disabled at the correct
    times.
    """
    param = ProjectParameter.create(name="test2", amount=3)
    wizard = UncertaintyWizard(param, None)
    qtbot.addWidget(wizard)
    wizard.show()

    # Check that the graph exists and distribution is 'unknown'
    assert wizard.type.plot.isVisible()
    assert wizard.type.distribution.currentIndex() == UndefinedUncertainty.id
    assert wizard.button(QWizard.FinishButton).isEnabled()
    # Select an uncertainty distribution, fill out numbers.
    with qtbot.waitSignal(wizard.type.distribution.currentIndexChanged, timeout=100):
        wizard.type.distribution.setCurrentIndex(UniformUncertainty.id)
    assert not wizard.type.complete  # Missing values for valid uncertainty.
    assert not wizard.button(QWizard.FinishButton).isEnabled()

    # When programmatically changing values, no textEdited signal is emitted.
    with qtbot.assertNotEmitted(wizard.type.minimum.textEdited):
        wizard.type.minimum.setText("1")
        wizard.type.generate_plot()
    assert not wizard.type.complete  # Still missing 'maximum'
    assert not wizard.button(QWizard.FinishButton).isEnabled()

    with qtbot.assertNotEmitted(wizard.type.minimum.textEdited):
        wizard.type.maximum.setText("5")
        wizard.type.generate_plot()
    assert wizard.type.complete
    assert wizard.button(QWizard.FinishButton).isEnabled()


@pytest.mark.skipif(sys.platform=='darwin', reason="tests segfaults on osx")
def test_update_uncertainty(ab_app, qtbot):
    """Using the signal/controller setup, update the uncertainty of a parameter"""
    param = ProjectParameter.create(name="uc1", amount=3)
    wizard = UncertaintyWizard(param, None)
    qtbot.addWidget(wizard)
    wizard.show()

    wizard.type.distribution.setCurrentIndex(TriangularUncertainty.id)
    wizard.type.minimum.setText("1")
    wizard.type.maximum.setText("5")
    wizard.type.generate_plot()
    assert wizard.type.complete

    # Now trigger a 'finish' action
    with qtbot.waitSignal(qparameters.parameters_changed, timeout=100):
        wizard.button(QWizard.FinishButton).click()

    # Reload param
    param = ProjectParameter.get(name="uc1")
    assert "loc" in param.data and param.data["loc"] == 3


@pytest.mark.skipif(sys.platform=='darwin', reason="tests segfaults on osx")
def test_update_alter_mean(qtbot, monkeypatch, ab_app):
    param = ProjectParameter.create(name="uc2", amount=1)
    wizard = UncertaintyWizard(param, None)
    qtbot.addWidget(wizard)
    wizard.show()

    # Select the lognormal distribution and set 'loc' and 'scale' fields.
    wizard.type.distribution.setCurrentIndex(LognormalUncertainty.id)
    wizard.type.loc.setText("1")
    wizard.type.scale.setText("0.3")
    wizard.type.generate_plot()
    assert wizard.type.complete

    # Now, monkeypatch Qt to ensure a 'yes' is selected for updating.
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *args: QMessageBox.Yes))
    # Now trigger a 'finish' action
    with qtbot.waitSignal(qparameters.parameters_changed, timeout=100):
        wizard.button(QWizard.FinishButton).click()

    # Reload param and check that the amount is changed.
    param = ProjectParameter.get(name="uc2")
    assert "loc" in param.data and param.amount != 1
    loc = param.data["loc"]
    assert loc == 1
    assert np.isclose(np.log(param.amount), loc)


@pytest.mark.skipif(sys.platform=='darwin', reason="tests segfaults on osx")
def test_lognormal_mean_balance(qtbot, bw2test, ab_app):
    uncertain = {
        "loc": 2,
        "scale": 0.2,
        "uncertainty type": 2,
    }
    param = ProjectParameter.create(name="uc1", amount=3, data=uncertain)
    wizard = UncertaintyWizard(param, None)
    qtbot.addWidget(wizard)
    wizard.show()

    # Compare loc with mean,
    loc, mean = float(wizard.type.loc.text()), float(wizard.type.mean.text())
    assert np.isclose(np.exp(loc), mean)
    wizard.type.check_negative()
    assert not wizard.field("negative")

    # Alter mean and loc fields in turn to show balancing methods
    with qtbot.assertNotEmitted(wizard.type.mean.textEdited):
        wizard.type.mean.setText("")
        wizard.type.balance_loc_with_mean()
        wizard.type.check_negative()
    assert wizard.type.loc.text() == "nan"
    # Setting the mean to a negative number will still return the same loc
    # value, but it will alter the 'negative' field.
    with qtbot.assertNotEmitted(wizard.type.mean.textEdited):
        wizard.type.mean.setText("-5")
        wizard.type.balance_loc_with_mean()
        wizard.type.check_negative()
    assert np.isclose(np.exp(float(wizard.type.loc.text())), 5)
    assert wizard.field("negative")


@pytest.mark.skipif(sys.platform=='darwin', reason="tests segfaults on osx")
def test_pedigree(qtbot, bw2test, ab_app):
    """Configure uncertainty using the pedigree page of the wizard."""
    uncertain = {
        "loc": 2,
        "scale": 0.2,
        "uncertainty type": 2,
        "pedigree": {
            "reliability": 1,
            "completeness": 2,
            "temporal correlation": 2,
            "geographical correlation": 2,
            "further technological correlation": 3
        },
    }
    param = ProjectParameter.create(name="uc1", amount=3, data=uncertain)
    wizard = UncertaintyWizard(param, None)
    qtbot.addWidget(wizard)
    wizard.show()

    # Uncertainty data has pedigree in it.
    assert "pedigree" in wizard.obj.uncertainty

    # Go to the pedigree page
    with qtbot.waitSignal(wizard.currentIdChanged, timeout=100):
        wizard.type.pedigree.click()
    assert wizard.using_pedigree  # Uncertainty/Pedigree data is valid

    loc, mean = float(wizard.pedigree.loc.text()), float(wizard.pedigree.mean.text())
    assert np.isclose(np.exp(loc), mean)
    # The uncertainty should be positive
    assert not wizard.field("negative")
    wizard.pedigree.check_negative()
    assert not wizard.field("negative")

    # Alter mean and loc fields in turn to show balancing methods
    with qtbot.assertNotEmitted(wizard.pedigree.mean.textEdited):
        wizard.pedigree.mean.setText("")
        wizard.pedigree.balance_loc_with_mean()
        wizard.pedigree.check_negative()
    assert wizard.pedigree.loc.text() == "nan"
    # Setting the mean to a negative number will still return the same loc
    # value, but it will alter the 'negative' field.
    with qtbot.assertNotEmitted(wizard.pedigree.mean.textEdited):
        wizard.pedigree.mean.setText("-5")
        wizard.pedigree.balance_loc_with_mean()
        wizard.pedigree.check_negative()
    assert np.isclose(np.exp(float(wizard.pedigree.loc.text())), 5)
    assert wizard.field("negative")
