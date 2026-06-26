"""ManualCornerRectifier — perspective-correct to a fronto-parallel view by
warping four user-marked corners onto a rectangle.

Implements app.application.protocols.Rectifier. This is the only
rectification strategy this commit implements. Automatic vanishing-point
detection (docs/architecture.md §3, Phase 2) will be a future sibling
class satisfying the same Protocol, not something this one falls back to.
Calling rectify() with manual_corners=None raises NotImplementedError —
a clear, honest failure rather than silently doing nothing.

Channel order: cv2.warpPerspective is a pure spatial remap — it moves
pixels by coordinate and never reads their colour values to decide where
they go — so it's the one cv2 operation in this codebase that's genuinely
agnostic to RGB vs BGR. No conversion happens here; the output keeps
whatever channel order the input had. Contrast with a future grayscale-
based stage (EdgeDetector), where the order does matter and must be
converted explicitly at that adapter's own boundary.

Scope limit, deliberate: corners aren't checked for being a simple
(non-self-intersecting) convex quad — only for not being degenerate. A
user who marks a bowtie shape gets a bowtie warp, not a friendly error.
Stricter geometric validation belongs with the corner-picking UI
interaction (Phase 4), not duplicated here.
"""

from __future__ import annotations

import cv2
import numpy as np

from app.application.types import ImageArray
from app.domain.geometry import Point

CornerQuad = tuple[Point, Point, Point, Point]


class ManualCornerRectifier:
    """Warps a user-marked quad onto an axis-aligned rectangle.

    `manual_corners` must be given as (top_left, top_right, bottom_right,
    bottom_left) — clockwise from the top-left, in the original image's
    pixel coordinates. The output size is sized to the quad's own longer
    opposite edges (top vs bottom for width, left vs right for height)
    rather than an arbitrary fixed size, so it doesn't stretch or squash
    whatever the user actually marked.
    """

    def rectify(
        self,
        image: ImageArray,
        manual_corners: CornerQuad | None = None,
    ) -> ImageArray:
        if manual_corners is None:
            raise NotImplementedError(
                "Automatic rectification isn't implemented yet "
                "(see docs/architecture.md, Phase 2) — pass manual_corners."
            )

        self._validate_image(image)
        top_left, top_right, bottom_right, bottom_left = self._validate_corners(manual_corners)

        max_width = self._longer_edge(top_left, top_right, bottom_left, bottom_right)
        max_height = self._longer_edge(top_left, bottom_left, top_right, bottom_right)

        source = np.array(
            [
                (top_left.x, top_left.y),
                (top_right.x, top_right.y),
                (bottom_right.x, bottom_right.y),
                (bottom_left.x, bottom_left.y),
            ],
            dtype=np.float32,
        )
        destination = np.array(
            [
                (0, 0),
                (max_width - 1, 0),
                (max_width - 1, max_height - 1),
                (0, max_height - 1),
            ],
            dtype=np.float32,
        )

        transform = cv2.getPerspectiveTransform(source, destination)
        warped = cv2.warpPerspective(
            image,
            transform,
            (max_width, max_height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0),
        )
        return warped.astype(np.uint8)

    @staticmethod
    def _validate_image(image: ImageArray) -> None:
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError(f"Expected an HxWx3 image array, got shape {image.shape}.")

    @staticmethod
    def _validate_corners(corners: CornerQuad) -> CornerQuad:
        if len(corners) != 4:
            raise ValueError(f"Expected exactly 4 corners, got {len(corners)}.")
        return corners

    @staticmethod
    def _longer_edge(a1: Point, a2: Point, b1: Point, b2: Point) -> int:
        """The longer of two opposite edges of the quad, rounded to a
        whole pixel and floored at 1 so a degenerate quad fails loudly
        rather than producing a zero-area output.
        """
        length = max(a1.distance_to(a2), b1.distance_to(b2))
        rounded = round(length)
        if rounded < 1:
            raise ValueError("The marked corners describe a degenerate (zero-area) quad.")
        return rounded