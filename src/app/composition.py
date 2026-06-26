"""Dependency-injection composition root.

This is the ONLY module allowed to import concrete infrastructure classes
and wire them to the Protocols defined in `app.application`. Nothing else
in the codebase should construct an OpenCV/onnxruntime/ezdxf adapter
directly — ask the composition root for one instead.

Progress so far: ImageValidator has a concrete adapter
(app.infrastructure.io.image_validator.PillowImageValidator). The other 8
Protocols don't yet. Real wiring in build_pipeline() below is deferred
until enough stages have adapters for it to be more than a stub calling a
single class — see docs/architecture.md roadmap for what's next.
"""

from __future__ import annotations


def build_pipeline() -> None:
    """Assemble and return the configured processing pipeline.

    Placeholder — will return an `application.Pipeline` built from
    concrete `infrastructure` adapters once enough stage Protocols have
    implementations for that to be meaningful.
    """
    raise NotImplementedError("Pipeline assembly lands once more stages have adapters.")