"""Semantic drawing layers — the DXF layer scheme from docs/architecture.md
(§3, "DXF output specifics"): WALLS, OPENINGS, WINDOWS, DOORS, BALCONY,
ORNAMENT, GUIDES.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class LayerKind(StrEnum):
    WALLS = "WALLS"
    OPENINGS = "OPENINGS"
    WINDOWS = "WINDOWS"
    DOORS = "DOORS"
    BALCONY = "BALCONY"
    ORNAMENT = "ORNAMENT"
    GUIDES = "GUIDES"


@dataclass(frozen=True, slots=True)
class Layer:
    """A named, styled layer that Strokes are assigned to.

    `color` follows the DXF/AutoCAD Color Index (ACI) convention — an int
    0-255 — so it maps directly onto ezdxf's layer color without any
    translation step in the exporter.
    """

    kind: LayerKind
    color: int = 7  # ACI 7 = default white/black
    visible: bool = True
    locked: bool = False

    @property
    def name(self) -> str:
        return self.kind.value