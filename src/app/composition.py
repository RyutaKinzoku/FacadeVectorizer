"""Dependency-injection composition root.

This is the ONLY module allowed to import concrete infrastructure classes
and wire them to the Protocols defined in `app.application`. Nothing else
in the codebase should construct an OpenCV/onnxruntime/ezdxf adapter
directly — ask the composition root for one instead.

Progress so far: every Protocol except Preprocessor and FacadeSegmenter
now has a concrete adapter (app.infrastructure.io.image_validator.
PillowImageValidator, app.infrastructure.calibration.scale_calibrator.
SingleMeasurementScaleCalibrator, app.infrastructure.vision.rectifier.
ManualCornerRectifier, app.infrastructure.vision.edge_detector.
CannyFastLineEdgeDetector, app.infrastructure.vectorization.vectorizer.
SingleLayerVectorizer, app.infrastructure.regularization.regularizer.
OrthoSnapMergeRegularizer, app.infrastructure.export.png_exporter.
PreviewPngExporter, app.infrastructure.export.dxf_exporter.DxfExporter).
Preprocessor (denoise/contrast/undistort, folded informally into
EdgeDetector's own bilateral filter for now) and FacadeSegmenter (Phase 3,
needs a real model) are the two still missing. Real wiring in
build_pipeline() below is the natural next step — see docs/architecture.md
roadmap.

Ordering constraint for whoever writes that wiring, discovered while
validating OrthoSnapMergeRegularizer against the real photo (see its own
docstring): GeometryRegularizer's tolerances are pixel-scale, so it must
run on Vectorizer's output BEFORE any ScaleCalibration has been applied
— calibrating first turns "15 pixels" into "15 metres" and silently
wrecks the merge step. Call order: Vectorizer(calibration=None) ->
GeometryRegularizer -> (scale applied separately, downstream, whenever
that step exists).
"""

from __future__ import annotations


def build_pipeline() -> None:
    """Assemble and return the configured processing pipeline.

    Placeholder — will return an `application.Pipeline` built from
    concrete `infrastructure` adapters once enough stage Protocols have
    implementations for that to be meaningful.
    """
    raise NotImplementedError("Pipeline assembly lands once more stages have adapters.")