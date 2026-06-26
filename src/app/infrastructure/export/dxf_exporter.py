"""DxfExporter — writes a DrawingModel to a layered DXF file.

Implements app.application.protocols.DrawingExporter. Writes real, named
DXF layers — one per LayerKind actually used by at least one Stroke, not
all seven kinds unconditionally, so the file doesn't end up cluttered
with empty layers nothing was assigned to — and LWPOLYLINE entities, per
docs/architecture.md §3 ("DXF output specifics").

Y-axis: flipped relative to the DrawingModel's own coordinates. Every
upstream stage (ImageValidator, Rectifier, Vectorizer) works in
image-style coordinates — Y increasing downward, matching how pixels are
addressed in a photo. CAD's convention is the opposite: Y increasing
upward, the way an elevation drawing is actually drawn (roof above
ground, not below it). Flipping Y here, once, at the export boundary —
rather than asking every upstream stage to privately agree on a sign
convention — is what makes the resulting DXF open right-side-up in
AutoCAD or Rhino without the user needing to flip it themselves first.
Contrast with PreviewPngExporter, which deliberately does NOT flip, since
its job is to look like the photo it came from, not like a CAD drawing.
Verified against a real ezdxf write/read round-trip while building this,
not just assumed.

Units: the DXF header's $INSUNITS is always set from drawing.unit, even
when drawing.is_calibrated is False. That's not a claim the numbers are
correct in that unit — it's the most defensible default header value
available when there's no real calibration to report honestly (see
docs/architecture.md §1, "you cannot recover true scale from one photo").
drawing.is_calibrated is the actual source of truth for whether the
geometry means anything dimensionally; this exporter doesn't hide that
distinction, it just doesn't have a better unit to put in the header.

Failure mode, for contrast with PreviewPngExporter: ezdxf's saveas raises
a real exception (FileNotFoundError, PermissionError, ...) on a bad path
— confirmed empirically, not assumed — so unlike cv2.imwrite, no manual
success check is needed here.
"""

from __future__ import annotations

import ezdxf

from app.domain.drawing import DrawingModel
from app.domain.units import LengthUnit

#: Maps our LengthUnit to ezdxf's DXF header unit codes.
_DXF_UNIT_CODE = {
    LengthUnit.MILLIMETRE: ezdxf.units.MM,
    LengthUnit.METRE: ezdxf.units.M,
}


class DxfExporter:
    def export(self, drawing: DrawingModel, output_path: str) -> None:
        if not drawing.strokes:
            raise ValueError("Cannot export a DXF with zero strokes.")

        document = ezdxf.new(setup=True)
        document.header["$INSUNITS"] = _DXF_UNIT_CODE[drawing.unit]
        self._create_used_layers(document, drawing)

        modelspace = document.modelspace()
        max_y = max(point.y for stroke in drawing.strokes for point in stroke.geometry.points)

        for stroke in drawing.strokes:
            points = [(point.x, max_y - point.y) for point in stroke.geometry.points]
            modelspace.add_lwpolyline(
                points,
                close=stroke.geometry.closed,
                dxfattribs={"layer": stroke.layer.value},
            )

        document.saveas(output_path)

    @staticmethod
    def _create_used_layers(document: ezdxf.document.Drawing, drawing: DrawingModel) -> None:
        used_kinds = {stroke.layer for stroke in drawing.strokes}
        layers_by_kind = {layer.kind: layer for layer in drawing.layers}

        for kind in used_kinds:
            layer = layers_by_kind.get(kind)
            color = layer.color if layer is not None else 7
            document.layers.add(name=kind.value, color=color)