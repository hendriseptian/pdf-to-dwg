cat > pdf_parser.py <<'PY'
import pymupdf as fitz
import math


# ============================================================
# PDF PARSER - TEXT PRESERVE
# ============================================================

CURVE_STEPS = 8


def point_xy(point):
    try:
        return [float(point.x), float(point.y)]
    except AttributeError:
        return [float(point[0]), float(point[1])]


def points_equal(p1, p2, tolerance=0.001):
    return (
        abs(p1[0] - p2[0]) <= tolerance
        and abs(p1[1] - p2[1]) <= tolerance
    )


def cubic_bezier(p0, p1, p2, p3, steps=CURVE_STEPS):

    p0 = point_xy(p0)
    p1 = point_xy(p1)
    p2 = point_xy(p2)
    p3 = point_xy(p3)

    result = []

    for i in range(steps + 1):

        t = i / steps
        mt = 1.0 - t

        x = (
            mt ** 3 * p0[0]
            + 3 * mt ** 2 * t * p1[0]
            + 3 * mt * t ** 2 * p2[0]
            + t ** 3 * p3[0]
        )

        y = (
            mt ** 3 * p0[1]
            + 3 * mt ** 2 * t * p1[1]
            + 3 * mt * t ** 2 * p2[1]
            + t ** 3 * p3[1]
        )

        point = [x, y]

        if (
            not result
            or not points_equal(result[-1], point)
        ):
            result.append(point)

    return result


def extract_pdf_page(pdf_path, page_number):

    doc = fitz.open(pdf_path)

    try:

        if page_number < 1:
            raise ValueError(
                "Page number must be 1 or greater."
            )

        if page_number > len(doc):
            raise ValueError(
                f"PDF has only {len(doc)} page(s)."
            )

        page = doc[page_number - 1]

        objects = []

        rect = page.rect

        page_info = {
            "width": float(rect.width),
            "height": float(rect.height),
            "unit": "pt",
            "pdf_unit": "point",
        }

        # ====================================================
        # VECTOR DRAWINGS
        # ====================================================

        drawings = page.get_drawings()

        for drawing in drawings:

            items = drawing.get(
                "items",
                []
            )

            current_polyline = []

            def flush_polyline():

                nonlocal current_polyline

                if len(current_polyline) >= 2:

                    cleaned = []

                    for point in current_polyline:

                        if (
                            not cleaned
                            or not points_equal(
                                cleaned[-1],
                                point
                            )
                        ):
                            cleaned.append(point)

                    if len(cleaned) >= 2:

                        objects.append({
                            "type": "POLYLINE",
                            "points": cleaned,
                        })

                current_polyline = []

            for item in items:

                if not item:
                    continue

                item_type = item[0]

                # --------------------------------------------
                # LINE
                # --------------------------------------------

                if item_type == "l":

                    flush_polyline()

                    p1 = point_xy(item[1])
                    p2 = point_xy(item[2])

                    if not points_equal(p1, p2):

                        objects.append({
                            "type": "LINE",
                            "start": p1,
                            "end": p2,
                        })

                # --------------------------------------------
                # RECTANGLE
                # --------------------------------------------

                elif item_type == "re":

                    flush_polyline()

                    r = item[1]

                    x0 = float(r.x0)
                    y0 = float(r.y0)
                    x1 = float(r.x1)
                    y1 = float(r.y1)

                    objects.append({
                        "type": "POLYLINE",
                        "points": [
                            [x0, y0],
                            [x1, y0],
                            [x1, y1],
                            [x0, y1],
                            [x0, y0],
                        ],
                        "closed": True,
                    })

                # --------------------------------------------
                # QUAD
                # --------------------------------------------

                elif item_type == "qu":

                    flush_polyline()

                    q = item[1]

                    objects.append({
                        "type": "POLYLINE",
                        "points": [
                            point_xy(q.ul),
                            point_xy(q.ur),
                            point_xy(q.lr),
                            point_xy(q.ll),
                            point_xy(q.ul),
                        ],
                        "closed": True,
                    })

                # --------------------------------------------
                # CUBIC
                # --------------------------------------------

                elif item_type == "c":

                    curve = cubic_bezier(
                        item[1],
                        item[2],
                        item[3],
                        item[4],
                    )

                    for point in curve:

                        if (
                            not current_polyline
                            or not points_equal(
                                current_polyline[-1],
                                point,
                            )
                        ):
                            current_polyline.append(
                                point
                            )

                else:

                    flush_polyline()

            flush_polyline()

        # ====================================================
        # TEXT
        # ====================================================

        text_dict = page.get_text(
            "dict"
        )

        for block in text_dict.get(
            "blocks",
            []
        ):

            if block.get("type") != 0:
                continue

            for line in block.get(
                "lines",
                []
            ):

                # ------------------------------------------------
                # Text direction
                # ------------------------------------------------

                direction = line.get(
                    "dir",
                    (1.0, 0.0)
                )

                try:
                    dx = float(direction[0])
                    dy = float(direction[1])

                    rotation = math.degrees(
                        math.atan2(
                            -dy,
                            dx
                        )
                    )

                except Exception:
                    rotation = 0.0

                for span in line.get(
                    "spans",
                    []
                ):

                    text = span.get(
                        "text",
                        ""
                    )

                    if not text.strip():
                        continue

                    bbox = span.get(
                        "bbox"
                    )

                    if not bbox:
                        continue

                    # ------------------------------------------------
                    # PDF font information
                    # ------------------------------------------------

                    font_name = str(
                        span.get(
                            "font",
                            ""
                        )
                    ).strip()

                    font_flags = int(
                        span.get(
                            "flags",
                            0
                        )
                    )

                    # ------------------------------------------------
                    # Position
                    #
                    # Use baseline origin when available.
                    # This is generally more accurate for TEXT.
                    # ------------------------------------------------

                    origin = span.get(
                        "origin"
                    )

                    if origin:

                        position = [
                            float(origin[0]),
                            float(origin[1]),
                        ]

                    else:

                        position = [
                            float(bbox[0]),
                            float(bbox[3]),
                        ]

                    # ------------------------------------------------
                    # Font size
                    # ------------------------------------------------

                    height = float(
                        span.get(
                            "size",
                            10.0
                        )
                    )

                    if height <= 0:
                        height = 10.0

                    # ------------------------------------------------
                    # PDF color
                    # ------------------------------------------------

                    color = span.get(
                        "color",
                        0
                    )

                    # ------------------------------------------------
                    # Preserve text metadata
                    # ------------------------------------------------

                    objects.append({

                        "type": "TEXT",

                        "text": text,

                        "position": position,

                        "height": height,

                        "font": font_name,

                        "font_flags": font_flags,

                        "rotation": rotation,

                        "color": color,

                        "bbox": [
                            float(bbox[0]),
                            float(bbox[1]),
                            float(bbox[2]),
                            float(bbox[3]),
                        ],

                    })

        return objects, page_info

    finally:

        doc.close()
PY
