"""CannyFastLineEdgeDetector — bilateral filter -> Canny -> FastLineDetector.

Implements app.application.protocols.EdgeDetector. The only edge-detection
strategy this commit implements — a future learned model (PiDiNet/DexiNed
via onnxruntime, docs/architecture.md §3, Phase 2) would be a sibling
class on the same Protocol, not something this one falls back to.

Channel order: unlike the Rectifier (a pure spatial remap, genuinely
order-agnostic — see its own docstring), grayscale conversion's luminance
weighting DOES depend on channel order. The ImageArray contract is RGB
(see app.infrastructure.io), so this adapter converts with
cv2.COLOR_RGB2GRAY, never COLOR_BGR2GRAY. Getting this wrong wouldn't
crash — it would silently weight the channels wrong (a pure red pixel
[255,0,0] converts to gray value 76 read as RGB, but 29 read as BGR,
because BGR-mode treats that same array as if the blue channel were 255
instead of red). No error, just a quietly wrong edge map.

Why we run our own Canny rather than letting FastLineDetector run its own
internal one: cv2.ximgproc.FastLineDetector CAN run Canny internally
(canny_aperture_size != 0), but that would skip the bilateral-filter
denoising step docs/architecture.md §3 calls for. Running Canny explicitly
first and passing canny_aperture_size=0 ("the input image is taken as an
edge image") keeps denoise -> edge -> line an explicit, separately-
tunable sequence instead of one opaque call.
"""

from __future__ import annotations

import cv2

from app.application.types import ImageArray
from app.domain.geometry import LineSegment, Point

#: Bilateral filter parameters — denoise while preserving edges.
BILATERAL_DIAMETER = 9
BILATERAL_SIGMA_COLOR = 75.0
BILATERAL_SIGMA_SPACE = 75.0

#: Canny hysteresis thresholds. These are the ones that actually run —
#: FastLineDetector's own internal Canny is disabled below.
CANNY_THRESHOLD_1 = 50.0
CANNY_THRESHOLD_2 = 150.0

#: FastLineDetector parameters.
FLD_LENGTH_THRESHOLD = 10  # segments shorter than this (px) are discarded
FLD_DISTANCE_THRESHOLD = 1.414213562  # sqrt(2): a one-pixel diagonal tolerance
FLD_DO_MERGE = False  # leave merging of nearby segments to a later Vectorizer stage


class CannyFastLineEdgeDetector:
    def detect(self, image: ImageArray) -> list[LineSegment]:
        self._validate_image(image)

        grayscale = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        denoised = cv2.bilateralFilter(
            grayscale, BILATERAL_DIAMETER, BILATERAL_SIGMA_COLOR, BILATERAL_SIGMA_SPACE
        )
        edges = cv2.Canny(denoised, CANNY_THRESHOLD_1, CANNY_THRESHOLD_2)

        detector = cv2.ximgproc.createFastLineDetector(
            length_threshold=FLD_LENGTH_THRESHOLD,
            distance_threshold=FLD_DISTANCE_THRESHOLD,
            canny_aperture_size=0,  # we already supplied an edge image above
            do_merge=FLD_DO_MERGE,
        )
        raw_lines = detector.detect(edges)

        if raw_lines is None:  # FastLineDetector's documented "no lines found" result
            return []

        return [
            LineSegment(Point(float(x1), float(y1)), Point(float(x2), float(y2)))
            for x1, y1, x2, y2 in raw_lines.reshape(-1, 4)
        ]

    @staticmethod
    def _validate_image(image: ImageArray) -> None:
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError(f"Expected an HxWx3 image array, got shape {image.shape}.")