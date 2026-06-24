"""Dependency-injection composition root.

This is the ONLY module allowed to import concrete infrastructure classes
and wire them to the Protocols defined in `app.application`. Nothing else
in the codebase should construct an OpenCV/onnxruntime/ezdxf adapter
directly — ask the composition root for one instead.

Intentionally empty until the domain model and stage Protocols are locked
(see docs/architecture.md, "First three concrete steps"). Filling this in
is the next commit after this skeleton.
"""

from __future__ import annotations


def build_pipeline() -> None:
    """Assemble and return the configured processing pipeline.

    Placeholder — will return an `application.Pipeline` built from
    concrete `infrastructure` adapters once the stage Protocols exist.
    """
    raise NotImplementedError("Pipeline assembly lands in the next commit.")
