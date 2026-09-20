cat > dxf_writer.py <<'PY'
import ezdxf
from pathlib import Path


# ============================================================
# DXF WRITER - OPTIMIZED / STABLE
# ============================================================

LINE_LAYER = "PDF_LINE"
POLYLINE_LAYER = "PDF_POLYLINE"
TEXT_LAYER = "PDF_TEXT"

LINE_ATTR = {
    "layer": LINE_LAYER,
}

POLYLINE_ATTR = {
    "layer": POLYLINE_LAYER,
}

TEXT_ATTR_BASE = {
    "layer": TEXT_LAYER,
}


def _pdf_to_dxf_xy(x, y, page_height):
    """
    Convert PDF top-left Y direction
    into CAD bottom-left Y direction.
    """
    return (
        float(x),
        float(page_height - y),
    )


def _convert_points(points, page_height):
    """
    Convert PDF points to DXF coordinates.
    """
    return [
        (
            float(point[0]),
            float(page_height - point[1]),
        )
        for point in points
    ]


def write_dxf(output_path, objects, page_info):
    """
    Write extracted PDF objects to editable DXF.

    V1/V1.1:
    - PDF coordinate scale is preserved.
    - No guessed mm/inch conversion.
    - LINE remains LINE.
    - POLYLINE remains LWPOLYLINE.
    - TEXT remains TEXT.
    """

    output_path = Path(output_path)

    # --------------------------------------------------------
    # CREATE DXF
    # --------------------------------------------------------

    doc = ezdxf.new(
        "R2018",
        setup=True,
    )

    # Unit-neutral.
    doc.units = 0

    # --------------------------------------------------------
    # LAYERS
    # --------------------------------------------------------

    layers = (
        (LINE_LAYER, 7),
        (POLYLINE_LAYER, 7),
        (TEXT_LAYER, 7),
    )

    for name, color in layers:

        if name not in doc.layers:

            doc.layers.add(
                name,
                color=color,
            )

    msp = doc.modelspace()

    page_height = float(
        page_info["height"]
    )

    # --------------------------------------------------------
    # WRITE OBJECTS
    # --------------------------------------------------------

    for obj in objects:

        obj_type = obj.get("type")

        # ====================================================
        # LINE
        # ====================================================

        if obj_type == "LINE":

            start = obj["start"]
            end = obj["end"]

            x1 = float(start[0])
            y1 = float(
                page_height - start[1]
            )

            x2 = float(end[0])
            y2 = float(
                page_height - end[1]
            )

            msp.add_line(
                (x1, y1),
                (x2, y2),
                dxfattribs=LINE_ATTR,
            )

        # ====================================================
        # POLYLINE
        # ====================================================

        elif obj_type == "POLYLINE":

            source_points = obj.get(
                "points",
                []
            )

            if len(source_points) < 2:
                continue

            points = _convert_points(
                source_points,
                page_height,
            )

            msp.add_lwpolyline(
                points,
                close=bool(
                    obj.get(
                        "closed",
                        False
                    )
                ),
                dxfattribs=POLYLINE_ATTR,
            )

        # ====================================================
        # TEXT
        # ====================================================

        elif obj_type == "TEXT":

            position = obj.get(
                "position",
                [0.0, 0.0]
            )

            x = float(position[0])
            y = float(
                page_height - position[1]
            )

            text = str(
                obj.get(
                    "text",
                    ""
                )
            )

            if not text:
                continue

            height = max(
                float(
                    obj.get(
                        "height",
                        10.0
                    )
                ),
                0.1,
            )

            text_entity = msp.add_text(
                text,
                dxfattribs={
                    "layer": TEXT_LAYER,
                    "height": height,
                },
            )

            text_entity.dxf.insert = (
                x,
                y,
            )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    doc.saveas(
        output_path
    )

    return output_path
PY
