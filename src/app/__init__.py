"""Photo-to-CAD application package.

Layered architecture (dependencies point inward):

    ui/              PySide6 widgets, view-models, editing canvas.
    application/      Use-cases, pipeline orchestrator, Protocols, undo/redo.
    domain/           DrawingModel, Layer, Stroke, ScaleCalibration, value objects.
    infrastructure/   Adapters for opencv, onnxruntime, ezdxf, filesystem.
    composition.py    The only place concrete classes are wired to Protocols (DI root).
"""
