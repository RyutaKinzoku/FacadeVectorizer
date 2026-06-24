"""Smoke tests for the project skeleton itself.

These don't test any pipeline logic yet (there isn't any) — they exist to
catch a broken environment or packaging mistake before it reaches a real
feature commit: can the package be imported, do the runtime dependencies
resolve, and can the main window actually be constructed headlessly.
"""

from __future__ import annotations


def test_app_package_imports() -> None:
    import app

    assert app is not None


def test_runtime_dependencies_importable() -> None:
    import cv2
    import ezdxf
    import numpy
    import onnxruntime
    import shapely
    from PIL import Image

    assert all([cv2, ezdxf, numpy, onnxruntime, shapely, Image])


def test_main_window_constructs_headless(qtbot) -> None:
    from app.main import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "Photo to CAD"
