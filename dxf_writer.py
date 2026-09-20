cat > dxf_writer.py <<'PY'
import ezdxf
from pathlib import Path
import re


# ============================================================
# DXF WRITER - PDF TEXT PRESERVE
# ============================================================

LINE_LAYER = "PDF_LINE"
POLYLINE_LAYER = "PDF_POLYLINE"
TEXT_LAYER = "PDF_TEXT"


def _pdf_to_dxf_xy(x, y, page_height):

    return (
        float(x),
        float(page_height - y),
    )


def _safe_style_name(font_name):

    if not font_name:
        return "PDF_DEFAULT"

    name = str(font_name)

    # Remove PDF subset prefix.
    # Example:
    # ABCDEF+ArialMT
    # becomes:
    # ArialMT
    if "+" in name:
        prefix, remainder = name.split(
            "+",
            1
        )

        if len(prefix) == 6:
            name = remainder

    name = re.sub(
        r"[^A-Za-z0-9_]+",
        "_",
        name
    )

    if not name:
        name = "PDF_DEFAULT"

    # DXF names should remain reasonably short.
    return (
        "PDF_"
        + name[:200]
    )


def _font_filename(font_name):

    """
    Convert common PDF font names into a font filename.

    Important:
    DXF cannot embed the PDF font itself.
    The referenced font must exist on the CAD computer.
    """

    if not font_name:
        return "txt.shx"

    name = str(font_name)

    # Remove PDF subset prefix.
    if "+" in name:

        prefix, remainder = name.split(
            "+",
            1
        )

        if len(prefix) == 6:
            name = remainder

    lower = name.lower()

    # Common Windows fonts.
    known_fonts = {
        "arialmt": "arial.ttf",
        "arial": "arial.ttf",
        "timesnewromanpsmt": "times.ttf",
        "timesnewroman": "times.ttf",
        "calibri": "calibri.ttf",
        "calibrib": "calibrib.ttf",
        "calibrii": "calibrii.ttf",
        "couriernewpsmt": "cour.ttf",
        "couriernew": "cour.ttf",
        "segoeui": "segoeui.ttf",
        "tahoma": "tahoma.ttf",
        "verdana": "verdana.ttf",
    }

    if lower in known_fonts:
        return known_fonts[lower]

    # If PDF font name already looks like a font file.
    if lower.endswith(
        (
            ".ttf",
            ".otf",
            ".shx",
        )
    ):
        return name

    # Best effort:
    # use font name as filename.
    return name + ".ttf"


def _ensure_text_style(
    doc,
    font_name,
    font_flags,
):

    style_name = _safe_style_name(
        font_name
    )

    font_file = _font_filename(
        font_name
    )

    if style_name not in doc.styles:

        try:

            doc.styles.add(
                style_name,
                font=font_file,
            )

        except Exception:

            # Safe fallback if an unusual
            # font name is rejected.
            doc.styles.add(
                style_name,
                font="txt.shx",
            )

    return style_name


def _text_rotation_from_flags(
    rotation
):

    try:
        return float(rotation)
    except Exception:
        return 0.0


def write_dxf(
    output_path,
    objects,
    page_info
):

    output_path = Path(
        output_path
    )

    # ========================================================
    # CREATE DXF
    # ========================================================

    doc = ezdxf.new(
        "R2018",
        setup=True,
    )

    # Keep PDF coordinates unit-neutral.
    doc.units = 0

    # ========================================================
    # LAYERS
    # ========================================================

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

    # ========================================================
    # OBJECTS
    # ========================================================

    for obj in objects:

        obj_type = obj.get(
            "type"
        )

        # ====================================================
        # LINE
        # ====================================================

        if obj_type == "LINE":

            start = obj["start"]
            end = obj["end"]

            x1, y1 = _pdf_to_dxf_xy(
                start[0],
                start[1],
                page_height,
            )

            x2, y2 = _pdf_to_dxf_xy(
                end[0],
                end[1],
                page_height,
            )

            msp.add_line(
                (x1, y1),
                (x2, y2),
                dxfattribs={
                    "layer": LINE_LAYER,
                },
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

            points = [
                _pdf_to_dxf_xy(
                    p[0],
                    p[1],
                    page_height,
                )
                for p in source_points
            ]

            msp.add_lwpolyline(
                points,
                close=bool(
                    obj.get(
                        "closed",
                        False
                    )
                ),
                dxfattribs={
                    "layer": POLYLINE_LAYER,
                },
            )

        # ====================================================
        # TEXT
        # ====================================================

        elif obj_type == "TEXT":

            position = obj.get(
                "position",
                [0.0, 0.0]
            )

            x, y = _pdf_to_dxf_xy(
                position[0],
                position[1],
                page_height,
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

            font_name = obj.get(
                "font",
                ""
            )

            font_flags = obj.get(
                "font_flags",
                0
            )

            rotation = _text_rotation_from_flags(
                obj.get(
                    "rotation",
                    0.0
                )
            )

            style_name = _ensure_text_style(
                doc,
                font_name,
                font_flags,
            )

            text_entity = msp.add_text(
                text,
                dxfattribs={
                    "layer": TEXT_LAYER,
                    "height": height,
                    "style": style_name,
                    "rotation": rotation,
                },
            )

            text_entity.dxf.insert = (
                x,
                y,
            )

    # ========================================================
    # SAVE
    # ========================================================

    doc.saveas(
        output_path
    )

    return output_path
PY
