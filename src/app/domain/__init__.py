"""Domain layer: the core model, free of any framework or library dependency.

Will hold DrawingModel, Layer, Stroke, ScaleCalibration, and related value
objects as plain dataclasses. Nothing in this package may import PySide6,
cv2, onnxruntime, or ezdxf.
"""
