"""Infrastructure layer: adapters around third-party libraries.

Sub-packages:
    io/            Pillow adapters — defensive image validation/ingestion.
    vision/        opencv adapters — rectification, edge/line detection.
    ml/            onnxruntime adapters — model loading + SHA-256 verification.
    export/        PNG and ezdxf exporters.
    persistence/   project (photo + calibration + edits + settings) repository.

Each adapter implements a Protocol defined in `app.application` (Dependency
Inversion) so the rest of the codebase never imports cv2 / onnxruntime /
ezdxf / PIL directly.
"""