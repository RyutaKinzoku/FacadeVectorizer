"""Domain layer: the core model, free of any framework or library dependency.

Holds DrawingModel, Layer, Stroke, ScaleCalibration, and the geometry value
objects (Point, LineSegment, Polyline, BoundingBox) as plain dataclasses.
Nothing in this package may import PySide6, cv2, onnxruntime, or ezdxf.
"""

from __future__ import annotations

from app.domain.calibration import ScaleCalibration
from app.domain.drawing import DrawingModel
from app.domain.geometry import BoundingBox, LineSegment, Point, Polyline
from app.domain.layer import Layer, LayerKind
from app.domain.stroke import Stroke
from app.domain.units import LengthUnit

__all__ = [
    "BoundingBox",
    "DrawingModel",
    "Layer",
    "LayerKind",
    "LengthUnit",
    "LineSegment",
    "Point",
    "Polyline",
    "ScaleCalibration",
    "Stroke",
]