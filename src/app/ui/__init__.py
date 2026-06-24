"""UI layer: PySide6 widgets, view-models, and the editing canvas.

Depends only on `app.application`. Never imports `cv2`, `onnxruntime`, or
`ezdxf` directly — those live behind adapters in `app.infrastructure`.
"""
