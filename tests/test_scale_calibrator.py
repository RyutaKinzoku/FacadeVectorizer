"""Tests for SingleMeasurementScaleCalibrator.

Deliberately thin: the actual validation rules (positive known_length,
distinct pixel points) belong to ScaleCalibration itself and are already
covered in tests/test_domain.py. These tests check the adapter delegates
correctly and satisfies the Protocol — they don't re-test the domain.
"""

from __future__ import annotations

import pytest

from app.application.protocols import ScaleCalibrator
from app.domain.geometry import Point
from app.domain.units import LengthUnit
from app.infrastructure.calibration.scale_calibrator import SingleMeasurementScaleCalibrator


@pytest.fixture
def calibrator() -> SingleMeasurementScaleCalibrator:
    return SingleMeasurementScaleCalibrator()


def test_builds_a_scale_calibration_from_the_given_measurement(
    calibrator: SingleMeasurementScaleCalibrator,
) -> None:
    result = calibrator.calibrate(
        pixel_start=Point(0, 0),
        pixel_end=Point(0, 200),
        known_length=2.0,
        unit=LengthUnit.METRE,
    )

    assert result.pixel_start == Point(0, 0)
    assert result.pixel_end == Point(0, 200)
    assert result.known_length == 2.0
    assert result.unit == LengthUnit.METRE
    assert result.pixels_per_unit == pytest.approx(100.0)


def test_delegates_validation_to_the_domain_value_object(
    calibrator: SingleMeasurementScaleCalibrator,
) -> None:
    # ScaleCalibration.__post_init__ rejects this -- the adapter doesn't
    # duplicate that rule, it just lets the domain object enforce it.
    with pytest.raises(ValueError, match="positive"):
        calibrator.calibrate(Point(0, 0), Point(0, 200), known_length=0, unit=LengthUnit.METRE)


def test_satisfies_the_protocol(calibrator: SingleMeasurementScaleCalibrator) -> None:
    assert isinstance(calibrator, ScaleCalibrator)