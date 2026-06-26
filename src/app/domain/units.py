"""Real-world units the drawing can be expressed in.

Kept deliberately small (mm, m) — these are the two units architectural
DXF files are realistically drawn in. Add more here only if a real need
shows up; this is not the place to speculatively support every unit.
"""

from __future__ import annotations

from enum import StrEnum


class LengthUnit(StrEnum):
    MILLIMETRE = "mm"
    METRE = "m"

    @property
    def to_millimetres(self) -> float:
        """Multiply a value expressed in this unit by this factor to get mm."""
        return {"mm": 1.0, "m": 1000.0}[self.value]