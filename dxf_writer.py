import ezdxf
import math


# ============================================================
# DXF LAYERS
# ============================================================

LINE_LAYER = "PDF_LINE"
POLYLINE_LAYER = "PDF_POLYLINE"
TEXT_LAYER = "PDF_TEXT"


# ============================================================
# PDF → DXF COORDINATE
# ============================================================

def _pdf_to_dxf_xy(x, y, page_height):
    """
    Convert PDF coordinate system to DXF coordinate system.

    PDF:
        origin = top-left
        Y increases downward

    DXF:
        origin = bottom-left
        Y increases upward
    """
    return float(x), float(page_height - y)


# ============================================================
# FONT MAPPING
# ============================================================

FONT_MAP = {
    # Arial
    "arialmt": "arial.ttf",
    "arial": "arial.ttf",

    # Arial Bold
    "arial-boldmt": "arialbd.ttf",
    "arial-bold": "arialbd.ttf",

    # Arial Narrow Bold
    "arialnarrow-bold": "arialnb.ttf",
    "arial narrow bold": "arialnb.ttf",

    # Tahoma
    "tahoma": "tahoma.ttf",
}


# ============================================================
# FONT NORMALIZATION
# ============================================================

def _normalize_font_name(font_name):
    """
    Normalize PDF font name.

    Examples:
        ArialMT
        ABCDEF+ArialMT
        Arial-BoldMT
    """

    if not font_name:
        return "ArialMT"

    name = str(font_name).strip()

    # Remove PDF subset prefix:
    # ABCDEF+ArialMT → ArialMT
    if "+" in name:
        name = name.split("+", 1)[1]

    return name


def _font_file_from_pdf_name(font_name):
    """
    Convert PDF BASEFONT name into a DXF font filename.
    """

    normalized = _normalize_font_name(font_name)

    key = normalized.lower()

    # Exact known fonts
    if key in FONT_MAP:
        return FONT_MAP[key]

    # Fallback rules
    if "arialnarrow" in key and "bold" in key:
        return "arialnb.ttf"

    if "arial" in key and "bold" in key:
        return "arialbd.ttf"

    if "arial" in key:
        return "arial.ttf"

    if "tahoma" in key:
        return "tahoma.ttf"

    # Generic fallback
    return "arial.ttf"


def _style_name_from_font(font_name):
    """
    Create a safe DXF style name.
    """

    normalized = _normalize_font_name(font_name)

    safe = normalized.replace(" ", "_")
    safe = safe.replace("-", "_")
    safe = safe.replace("+", "_")

    return "PDF_" + safe


# ============================================================
# DXF TEXT STYLE
# ============================================================

def _ensure_text_style(doc, font_name):
    """
    Create or reuse a DXF text style corresponding
    to the PDF font.
    """

    normalized = _normalize_font_name(font_name)
    style_name = _style_name_from_font(normalized)
    font_file = _font_file_from_pdf_name(normalized)

    # Already exists
    if style_name in doc.styles:
        return style_name

    try:
        doc.styles.add(
            style_name,
            font=font_file
        )
    except Exception:
        # Final fallback
        if style_name not in doc.styles:
            doc.styles.add(
                style_name,
                font="arial.ttf"
            )

    return style_name


# ============================================================
# SAFE FLOAT
# ============================================================

def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


# ============================================================
# COLOR
# ============================================================

def _rgb_to_true_color(rgb):
    """
    Convert RGB tuple to AutoCAD true color integer.
    """

    if not rgb:
        return None

    try:
        r, g, b = rgb[:3]

        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))

        return (r << 16) | (g << 8) | b

    except Exception:
        return None


# ============================================================
# MAIN DXF WRITER
# ============================================================

def write_dxf(objects, page_info, output_path):
    """
    Write extracted PDF objects into DXF.

    Supported:
        LINE
        POLYLINE
        TEXT

    TEXT preserves:
        - text content
        - font
        - size
        - position
        - rotation
        - color when available
    """

    doc = ezdxf.new(
        "R2018",
        setup=True
    )

    # --------------------------------------------------------
    # Layers
    # --------------------------------------------------------

    if LINE_LAYER not in doc.layers:
        doc.layers.add(
            LINE_LAYER,
            color=7
        )

    if POLYLINE_LAYER not in doc.layers:
        doc.layers.add(
            POLYLINE_LAYER,
            color=7
        )

    if TEXT_LAYER not in doc.layers:
        doc.layers.add(
            TEXT_LAYER,
            color=7
        )

    msp = doc.modelspace()

    page_width = _safe_float(
        page_info.get("width", 0)
    )

    page_height = _safe_float(
        page_info.get("height", 0)
    )

    # --------------------------------------------------------
    # Objects
    # --------------------------------------------------------

    for obj in objects:

        obj_type = obj.get("type")

        # ====================================================
        # LINE
        # ====================================================

        if obj_type == "LINE":

            start = obj.get("start")
            end = obj.get("end")

            if not start or not end:
                continue

            x1, y1 = _pdf_to_dxf_xy(
                start[0],
                start[1],
                page_height
            )

            x2, y2 = _pdf_to_dxf_xy(
                end[0],
                end[1],
                page_height
            )

            entity = msp.add_line(
                (x1, y1),
                (x2, y2),
                dxfattribs={
                    "layer": LINE_LAYER
                }
            )

            color = _rgb_to_true_color(
                obj.get("color")
            )

            if color is not None:
                entity.dxf.true_color = color

        # ====================================================
        # POLYLINE
        # ====================================================

        elif obj_type == "POLYLINE":

            points = obj.get("points")

            if not points or len(points) < 2:
                continue

            dxf_points = []

            for point in points:

                x, y = _pdf_to_dxf_xy(
                    point[0],
                    point[1],
                    page_height
                )

                dxf_points.append(
                    (x, y)
                )

            entity = msp.add_lwpolyline(
                dxf_points,
                close=bool(
                    obj.get("closed", False)
                ),
                dxfattribs={
                    "layer": POLYLINE_LAYER
                }
            )

            color = _rgb_to_true_color(
                obj.get("color")
            )

            if color is not None:
                entity.dxf.true_color = color

        # ====================================================
        # TEXT
        # ====================================================

        elif obj_type == "TEXT":

            text = obj.get("text", "")

            if not text:
                continue

            # ------------------------------------------------
            # Font
            # ------------------------------------------------

            pdf_font = obj.get(
                "font",
                "ArialMT"
            )

            style_name = _ensure_text_style(
                doc,
                pdf_font
            )

            # ------------------------------------------------
            # Position
            # ------------------------------------------------

            position = obj.get("position")

            if not position:

                bbox = obj.get("bbox")

                if bbox:
                    position = (
                        bbox[0],
                        bbox[3]
                    )
                else:
                    continue

            x, y = _pdf_to_dxf_xy(
                position[0],
                position[1],
                page_height
            )

            # ------------------------------------------------
            # Height
            # ------------------------------------------------

            height = _safe_float(
                obj.get("height"),
                10.0
            )

            if height <= 0:
                height = 10.0

            # ------------------------------------------------
            # Rotation
            # ------------------------------------------------

            rotation = _safe_float(
                obj.get("rotation"),
                0.0
            )

            # ------------------------------------------------
            # TEXT
            # ------------------------------------------------

            entity = msp.add_text(
                text,
                dxfattribs={
                    "layer": TEXT_LAYER,
                    "style": style_name,
                    "height": height,
                    "rotation": rotation,
                    "insert": (x, y),
                }
            )

            # ------------------------------------------------
            # Color
            # ------------------------------------------------

            color = _rgb_to_true_color(
                obj.get("color")
            )

            if color is not None:
                entity.dxf.true_color = color

    # ========================================================
    # HEADER / PAGE INFORMATION
    # ========================================================

    try:
        doc.header["$INSUNITS"] = 0
    except Exception:
        pass

    # ========================================================
    # SAVE
    # ========================================================

    doc.saveas(output_path)
