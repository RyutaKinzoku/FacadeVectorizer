"""Shared structural types for pipeline stage Protocols.

`ImageArray` is the common currency for the raster-facing stages
(preprocess, rectify, edge-detect, segment): a NumPy array. This is a
deliberate, narrow exception to "application depends only on domain" —
numpy is treated as a fundamental data structure here (the way `list` or
`dict` would be), not as a third-party business-logic dependency. cv2,
onnxruntime, and PySide6 still never appear above the infrastructure
layer; only their common numpy currency does.

Vector-space stages (calibrate, vectorize, regularize, export) use the
domain dataclasses instead — see app.domain.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

ImageArray = npt.NDArray[np.uint8]