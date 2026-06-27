"""Tests for the MainWindow GUI.

Native file/save dialogs (QFileDialog) aren't simulated here -- that's
standard practice for Qt testing. The public, testable surface is what
happens once a path is already chosen, not the OS dialog itself, so
these tests call _set_photo(...) directly and set the output-path line
edits directly, rather than trying to drive QFileDialog headlessly.

The injected pipeline uses the shared fakes from tests/fakes.py for
ImageValidator/Rectifier/EdgeDetector, with the REAL Vectorizer,
GeometryRegularizer, ScaleCalibrator, and both exporters underneath --
same balance as test_pipeline.py: these tests exercise the real widget
wiring and the real downstream stages, without needing a real photo file
on disk or paying for real cv2 calls.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from app.application.pipeline import PhotoToCadPipeline
from app.domain.geometry import LineSegment, Point
from app.infrastructure.calibration.scale_calibrator import SingleMeasurementScaleCalibrator
from app.infrastructure.export.dxf_exporter import DxfExporter
from app.infrastructure.export.png_exporter import PreviewPngExporter
from app.infrastructure.regularization.regularizer import OrthoSnapMergeRegularizer
from app.infrastructure.vectorization.vectorizer import SingleLayerVectorizer
from app.main import MainWindow
from tests.fakes import FakeEdgeDetector, FakeImageValidator, FakeRectifier


def _fake_pipeline(segments: list[LineSegment]) -> PhotoToCadPipeline:
    return PhotoToCadPipeline(
        image_validator=FakeImageValidator(),
        rectifier=FakeRectifier(),
        edge_detector=FakeEdgeDetector(segments),
        vectorizer=SingleLayerVectorizer(),
        scale_calibrator=SingleMeasurementScaleCalibrator(),
        png_exporter=PreviewPngExporter(),
        dxf_exporter=DxfExporter(),
        regularizer=OrthoSnapMergeRegularizer(),
    )


@pytest.fixture
def real_photo(tmp_path: Path) -> Path:
    """A real, tiny, valid image file on disk -- needed because _set_photo
    reads it with QImageReader/QPixmap for the dimension-detection and
    preview-thumbnail behaviour, even though FakeImageValidator never
    actually decodes it for the pipeline itself.
    """
    path = tmp_path / "photo.png"
    Image.new("RGB", (200, 150), color=(120, 120, 120)).save(path)
    return path


class TestPhotoSelectionPopulatesDefaults:
    def test_corners_default_to_the_full_image_bounds(
        self, qtbot: QtBot, real_photo: Path
    ) -> None:
        window = MainWindow(pipeline=_fake_pipeline([]))
        qtbot.addWidget(window)

        window._set_photo(real_photo)

        corners = window._corners.as_corner_quad()
        assert corners == (Point(0, 0), Point(199, 0), Point(199, 149), Point(0, 149))

    def test_output_paths_default_next_to_the_source_photo(
        self, qtbot: QtBot, real_photo: Path
    ) -> None:
        window = MainWindow(pipeline=_fake_pipeline([]))
        qtbot.addWidget(window)

        window._set_photo(real_photo)

        assert window._png_output_edit.text() == str(real_photo.with_suffix(".png"))
        assert window._dxf_output_edit.text() == str(real_photo.with_suffix(".dxf"))


class TestGenerateWithoutCalibration:
    def test_clicking_generate_produces_both_files(
        self, qtbot: QtBot, real_photo: Path, tmp_path: Path
    ) -> None:
        segments = [LineSegment(Point(10, 10), Point(90, 10))]
        window = MainWindow(pipeline=_fake_pipeline(segments))
        qtbot.addWidget(window)
        window._set_photo(real_photo)

        png_path = tmp_path / "result.png"
        dxf_path = tmp_path / "result.dxf"
        window._png_output_edit.setText(str(png_path))
        window._dxf_output_edit.setText(str(dxf_path))

        qtbot.mouseClick(window._generate_button, Qt.MouseButton.LeftButton)

        assert png_path.exists()
        assert dxf_path.exists()
        assert "Done" in window._status_label.text()


class TestGenerateWithCalibration:
    def test_calibration_checkbox_enables_scaled_output(
        self, qtbot: QtBot, real_photo: Path, tmp_path: Path
    ) -> None:
        # A 100px segment, calibrated 100px == 1.0 metre.
        segments = [LineSegment(Point(0, 0), Point(100, 0))]
        window = MainWindow(pipeline=_fake_pipeline(segments))
        qtbot.addWidget(window)
        window._set_photo(real_photo)
        window._png_output_edit.setText(str(tmp_path / "result.png"))
        window._dxf_output_edit.setText(str(tmp_path / "result.dxf"))

        window._calibration_group.setChecked(True)
        window._calibration_point_a[0].setValue(0)
        window._calibration_point_a[1].setValue(0)
        window._calibration_point_b[0].setValue(100)
        window._calibration_point_b[1].setValue(0)
        window._known_length_box.setValue(1.0)
        window._unit_combo.setCurrentIndex(1)  # metres

        qtbot.mouseClick(window._generate_button, Qt.MouseButton.LeftButton)

        assert "Done" in window._status_label.text()


class TestMissingPhotoShowsAFriendlyError:
    def test_generate_without_a_photo_shows_an_error_not_a_crash(self, qtbot: QtBot) -> None:
        window = MainWindow(pipeline=_fake_pipeline([]))
        qtbot.addWidget(window)

        qtbot.mouseClick(window._generate_button, Qt.MouseButton.LeftButton)

        assert "Error" in window._status_label.text()