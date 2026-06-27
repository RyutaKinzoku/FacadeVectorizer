"""Application entry point.

This is the first commit where the window actually does the thing the
app exists for, instead of being a placeholder proving the packaging
skeleton runs. It's a basic, form-based GUI -- numeric spin boxes for the
four rectification corners and the optional calibration points, not yet
an interactive canvas where the user clicks/drags corners directly on
the photo. That polished interaction is a real, separate, larger Phase 4
UI commit; this one's job is narrower: prove the GUI-to-pipeline wiring
itself works, with whatever input widgets are simplest to get there
correctly.

Every user-facing string still goes through self.tr(...), per the
internationalisation plan (English / Spanish via Qt .ts/.qm files).

Layering: this module reads image dimensions via QImageReader (Qt's own
image support), never PIL/cv2 directly -- those stay behind the
infrastructure adapters per ui/__init__.py's own docstring. The pipeline
itself is injected (defaulting to app.composition.build_pipeline()), the
same Dependency Inversion every other layer in this codebase already
follows -- which is also what lets tests substitute a fake-backed
pipeline instead of exercising real cv2 calls for every UI test.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QLocale, Qt, QTranslator
from PySide6.QtGui import QImageReader, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.application.pipeline import PhotoToCadPipeline
from app.composition import build_pipeline
from app.domain.drawing import DrawingModel
from app.domain.geometry import Point
from app.domain.units import LengthUnit

IMAGE_FILE_FILTER = "Images (*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp)"
PREVIEW_MAX_SIZE = 480
COORDINATE_MAX = 100_000.0
LENGTH_MAX = 100_000.0


class CornerInputs:
    """The four corner spin-box pairs, grouped so MainWindow doesn't have
    to juggle eight loose widgets individually.
    """

    def __init__(self, form: QFormLayout) -> None:
        self.top_left = self._add_row(form, "Top-left")
        self.top_right = self._add_row(form, "Top-right")
        self.bottom_right = self._add_row(form, "Bottom-right")
        self.bottom_left = self._add_row(form, "Bottom-left")

    @staticmethod
    def _add_row(form: QFormLayout, label: str) -> tuple[QDoubleSpinBox, QDoubleSpinBox]:
        x_box, y_box = QDoubleSpinBox(), QDoubleSpinBox()
        for box in (x_box, y_box):
            box.setRange(0, COORDINATE_MAX)
            box.setDecimals(1)
        row = QHBoxLayout()
        row.addWidget(QLabel("x"))
        row.addWidget(x_box)
        row.addWidget(QLabel("y"))
        row.addWidget(y_box)
        container = QWidget()
        container.setLayout(row)
        form.addRow(label, container)
        return x_box, y_box

    def set_to_full_image(self, width: float, height: float) -> None:
        self.top_left[0].setValue(0)
        self.top_left[1].setValue(0)
        self.top_right[0].setValue(width - 1)
        self.top_right[1].setValue(0)
        self.bottom_right[0].setValue(width - 1)
        self.bottom_right[1].setValue(height - 1)
        self.bottom_left[0].setValue(0)
        self.bottom_left[1].setValue(height - 1)

    def as_corner_quad(self) -> tuple[Point, Point, Point, Point]:
        return (
            Point(self.top_left[0].value(), self.top_left[1].value()),
            Point(self.top_right[0].value(), self.top_right[1].value()),
            Point(self.bottom_right[0].value(), self.bottom_right[1].value()),
            Point(self.bottom_left[0].value(), self.bottom_left[1].value()),
        )


class MainWindow(QMainWindow):
    def __init__(self, pipeline: PhotoToCadPipeline | None = None) -> None:
        super().__init__()
        self._pipeline = pipeline if pipeline is not None else build_pipeline()
        self._photo_path: Path | None = None

        self.setWindowTitle(self.tr("Photo to CAD"))
        self.resize(720, 900)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll.setWidget(content)
        self.setCentralWidget(scroll)

        layout = QVBoxLayout(content)
        layout.addLayout(self._build_photo_section())
        layout.addWidget(self._build_corners_section())
        layout.addWidget(self._build_calibration_section())
        layout.addLayout(self._build_output_section())
        self._generate_button = self._build_generate_button()
        layout.addWidget(self._generate_button)
        self._status_label = QLabel("")
        layout.addWidget(self._status_label)
        self._preview_label = QLabel(self.tr("No photo selected yet."))
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._preview_label)

    # -- section builders ------------------------------------------------

    def _build_photo_section(self) -> QHBoxLayout:
        row = QHBoxLayout()
        browse_button = QPushButton(self.tr("Select Photo..."))
        browse_button.clicked.connect(self._on_browse_photo)
        self._photo_path_label = QLabel(self.tr("(none selected)"))
        row.addWidget(browse_button)
        row.addWidget(self._photo_path_label)
        return row

    def _build_corners_section(self) -> QGroupBox:
        group = QGroupBox(self.tr("Rectification corners (pixel coordinates)"))
        form = QFormLayout()
        self._corners = CornerInputs(form)
        reset_button = QPushButton(self.tr("Reset to full image"))
        reset_button.clicked.connect(self._on_reset_corners)
        form.addRow(reset_button)
        group.setLayout(form)
        return group

    def _build_calibration_section(self) -> QGroupBox:
        group = QGroupBox(self.tr("Scale calibration (optional)"))
        group.setCheckable(True)
        group.setChecked(False)
        self._calibration_group = group

        form = QFormLayout()
        self._calibration_point_a = self._calibration_point_row(form, self.tr("Point A"))
        self._calibration_point_b = self._calibration_point_row(form, self.tr("Point B"))

        self._known_length_box = QDoubleSpinBox()
        self._known_length_box.setRange(0.001, LENGTH_MAX)
        self._known_length_box.setDecimals(3)
        self._known_length_box.setValue(1.0)
        form.addRow(self.tr("Known length (A to B)"), self._known_length_box)

        self._unit_combo = QComboBox()
        self._unit_combo.addItem(self.tr("millimetres (mm)"), LengthUnit.MILLIMETRE)
        self._unit_combo.addItem(self.tr("metres (m)"), LengthUnit.METRE)
        self._unit_combo.setCurrentIndex(1)  # metres is the common case for a facade
        form.addRow(self.tr("Unit"), self._unit_combo)

        group.setLayout(form)
        return group

    @staticmethod
    def _calibration_point_row(
        form: QFormLayout, label: str
    ) -> tuple[QDoubleSpinBox, QDoubleSpinBox]:
        x_box, y_box = QDoubleSpinBox(), QDoubleSpinBox()
        for box in (x_box, y_box):
            box.setRange(0, COORDINATE_MAX)
            box.setDecimals(1)
        row = QHBoxLayout()
        row.addWidget(QLabel("x"))
        row.addWidget(x_box)
        row.addWidget(QLabel("y"))
        row.addWidget(y_box)
        container = QWidget()
        container.setLayout(row)
        form.addRow(label, container)
        return x_box, y_box

    def _build_output_section(self) -> QFormLayout:
        form = QFormLayout()
        self._png_output_edit, png_browse = self._output_path_row(self._on_browse_png_output)
        self._dxf_output_edit, dxf_browse = self._output_path_row(self._on_browse_dxf_output)
        form.addRow(self.tr("PNG output"), self._row_with_browse(self._png_output_edit, png_browse))
        form.addRow(self.tr("DXF output"), self._row_with_browse(self._dxf_output_edit, dxf_browse))
        return form

    @staticmethod
    def _output_path_row(on_browse: Callable[[], None]) -> tuple[QLineEdit, QPushButton]:
        edit = QLineEdit()
        button = QPushButton("...")
        button.clicked.connect(on_browse)
        return edit, button

    @staticmethod
    def _row_with_browse(edit: QLineEdit, button: QPushButton) -> QWidget:
        row = QHBoxLayout()
        row.addWidget(edit)
        row.addWidget(button)
        container = QWidget()
        container.setLayout(row)
        return container

    def _build_generate_button(self) -> QPushButton:
        button = QPushButton(self.tr("Generate Drawing"))
        button.clicked.connect(self._on_generate_clicked)
        return button

    # -- slots ------------------------------------------------------------

    def _on_browse_photo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.tr("Select Photo"), "", IMAGE_FILE_FILTER)
        if path:
            self._set_photo(Path(path))

    def _set_photo(self, path: Path) -> None:
        self._photo_path = path
        self._photo_path_label.setText(path.name)

        reader = QImageReader(str(path))
        size = reader.size()
        if size.isValid():
            self._corners.set_to_full_image(size.width(), size.height())

        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            self._preview_label.setPixmap(
                pixmap.scaled(
                    PREVIEW_MAX_SIZE,
                    PREVIEW_MAX_SIZE,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        self._png_output_edit.setText(str(path.with_suffix(".png")))
        self._dxf_output_edit.setText(str(path.with_suffix(".dxf")))

    def _on_reset_corners(self) -> None:
        if self._photo_path is None:
            return
        reader = QImageReader(str(self._photo_path))
        size = reader.size()
        if size.isValid():
            self._corners.set_to_full_image(size.width(), size.height())

    def _on_browse_png_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, self.tr("PNG Output"), "", "PNG (*.png)")
        if path:
            self._png_output_edit.setText(path)

    def _on_browse_dxf_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, self.tr("DXF Output"), "", "DXF (*.dxf)")
        if path:
            self._dxf_output_edit.setText(path)

    def _on_generate_clicked(self) -> None:
        if self._photo_path is None:
            self._show_error(self.tr("Select a photo first."))
            return

        png_path = self._png_output_edit.text().strip()
        dxf_path = self._dxf_output_edit.text().strip()
        if not png_path or not dxf_path:
            self._show_error(self.tr("Choose both a PNG and a DXF output path first."))
            return

        pixel_start, pixel_end, known_length, unit = self._calibration_inputs()

        try:
            drawing = self._pipeline.run(
                str(self._photo_path),
                self._corners.as_corner_quad(),
                png_path,
                dxf_path,
                calibration_pixel_start=pixel_start,
                calibration_pixel_end=pixel_end,
                calibration_known_length=known_length,
                calibration_unit=unit,
            )
        except (ValueError, NotImplementedError, OSError) as error:
            self._show_error(str(error))
            return

        self._show_success(drawing, png_path)

    def _calibration_inputs(self) -> tuple[Point | None, Point | None, float | None, LengthUnit]:
        if not self._calibration_group.isChecked():
            return None, None, None, LengthUnit.MILLIMETRE
        a_x, a_y = self._calibration_point_a
        b_x, b_y = self._calibration_point_b
        unit: LengthUnit = self._unit_combo.currentData()
        return (
            Point(a_x.value(), a_y.value()),
            Point(b_x.value(), b_y.value()),
            self._known_length_box.value(),
            unit,
        )

    def _show_error(self, message: str) -> None:
        self._status_label.setText(self.tr("Error: {0}").format(message))
        self._status_label.setStyleSheet("color: #b00020;")

    def _show_success(self, drawing: DrawingModel, png_path: str) -> None:
        stroke_count = len(drawing.strokes)
        self._status_label.setText(
            self.tr("Done — {0} strokes written to PNG and DXF.").format(stroke_count)
        )
        self._status_label.setStyleSheet("color: #006400;")

        pixmap = QPixmap(png_path)
        if not pixmap.isNull():
            self._preview_label.setPixmap(
                pixmap.scaled(
                    PREVIEW_MAX_SIZE,
                    PREVIEW_MAX_SIZE,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )


def _install_translator(app: QApplication) -> QTranslator:
    """Load the compiled translation matching the system locale.

    Falls back silently to English (the source language, no .qm needed)
    if no matching .qm is found under i18n/ — e.g. before any translations
    have been compiled yet, as is still the case at this point.
    """
    translator = QTranslator()
    locale = QLocale.system().name()  # e.g. "es_ES"
    translator.load(f"app_{locale[:2]}", "i18n")
    app.installTranslator(translator)
    return translator


def main() -> int:
    app = QApplication(sys.argv)
    translator = _install_translator(app)  # noqa: F841 — keep alive for app lifetime

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())