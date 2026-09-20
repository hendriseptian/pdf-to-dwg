cat > pdf_parser.py <<'PY'
import pymupdf as fitz


# ============================================================
# PDF PARSER - FAST & STABLE V2
# ============================================================

# Bézier curve sampling.
# Lebih kecil = lebih ringan.
# 8 cukup untuk menjaga bentuk teknis sambil mengurangi vertex.
CURVE_STEPS = 8


def point_xy(point):
    """
    Convert PyMuPDF point-like data to [x, y].

    Supports:
    - PyMuPDF Point
    - tuple/list: (x, y)
    """
    try:
        return [float(point.x), float(point.y)]
    except AttributeError:
        return [float(point[0]), float(point[1])]


def points_equal(p1, p2, tolerance=0.001):
    """Check whether two points are effectively identical."""
    return (
        abs(p1[0] - p2[0]) <= tolerance
        and abs(p1[1] - p2[1]) <= tolerance
    )


def append_unique(points, point):
    """Append point only when different from previous point."""
    xy = point_xy(point)

    if not points or not points_equal(points[-1], xy):
        points.append(xy)


def cubic_bezier(p0, p1, p2, p3, steps=CURVE_STEPS):
    """
    Approximate cubic Bézier curve using a lightweight polyline.
    """

    p0 = point_xy(p0)
    p1 = point_xy(p1)
    p2 = point_xy(p2)
    p3 = point_xy(p3)

    result = []

    for i in range(steps + 1):

        t = i / steps
        mt = 1.0 - t

        mt2 = mt * mt
        t2 = t * t

        x = (
            mt2 * mt * p0[0]
            + 3.0 * mt2 * t * p1[0]
            + 3.0 * mt * t2 * p2[0]
            + t2 * t * p3[0]
        )

        y = (
            mt2 * mt * p0[1]
            + 3.0 * mt2 * t * p1[1]
            + 3.0 * mt * t2 * p2[1]
            + t2 * t * p3[1]
        )

        point = [x, y]

        if not result or not points_equal(
            result[-1],
            point
        ):
            result.append(point)

    return result


def rectangle_points(rect):
    """
    Convert rect-like tuple to closed polyline.
    """

    x0 = float(rect[0])
    y0 = float(rect[1])
    x1 = float(rect[2])
    y1 = float(rect[3])

    return [
        [x0, y0],
        [x1, y0],
        [x1, y1],
        [x0, y1],
        [x0, y0],
    ]


def quad_points(quad):
    """
    Convert quad-like tuple/list to closed polyline.
    """

    return [
        point_xy(quad[0]),
        point_xy(quad[1]),
        point_xy(quad[2]),
        point_xy(quad[3]),
        point_xy(quad[0]),
    ]


def flush_polyline(objects, points):
    """
    Add accumulated curve/polyline to objects.
    """

    if len(points) < 2:
        return

    cleaned = []

    for point in points:

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


def extract_pdf_page(pdf_path, page_number):
    """
    Extract vector geometry and text from one PDF page.

    Returns:
        objects
        page_info
    """

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

        # ====================================================
        # PAGE INFORMATION
        # ====================================================

        rect = page.rect

        page_info = {
            "width": float(rect.width),
            "height": float(rect.height),
            "unit": "pt",
            "pdf_unit": "point",
        }

        # ====================================================
        # VECTOR GRAPHICS
        #
        # IMPORTANT:
        # get_cdrawings() is used instead of get_drawings()
        # because it avoids creation of many Python geometry
        # objects and is significantly faster.
        # ====================================================

        drawings = page.get_cdrawings()

        for drawing in drawings:

            items = drawing.get("items", [])

            current_polyline = []

            for item in items:

                if not item:
                    continue

                item_type = item[0]

                # --------------------------------------------
                # LINE
                # --------------------------------------------

                if item_type == "l":

                    flush_polyline(
                        objects,
                        current_polyline
                    )

                    current_polyline = []

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

                    flush_polyline(
                        objects,
                        current_polyline
                    )

                    current_polyline = []

                    points = rectangle_points(
                        item[1]
                    )

                    objects.append({
                        "type": "POLYLINE",
                        "points": points,
                    })

                # --------------------------------------------
                # QUAD
                # --------------------------------------------

                elif item_type == "qu":

                    flush_polyline(
                        objects,
                        current_polyline
                    )

                    current_polyline = []

                    points = quad_points(
                        item[1]
                    )

                    objects.append({
                        "type": "POLYLINE",
                        "points": points,
                    })

                # --------------------------------------------
                # CUBIC BÉZIER
                # --------------------------------------------

                elif item_type == "c":

                    curve = cubic_bezier(
                        item[1],
                        item[2],
                        item[3],
                        item[4],
                        CURVE_STEPS,
                    )

                    for point in curve:

                        if (
                            not current_polyline
                            or not points_equal(
                                current_polyline[-1],
                                point
                            )
                        ):
                            current_polyline.append(
                                point
                            )

                # --------------------------------------------
                # UNKNOWN
                # --------------------------------------------

                else:

                    flush_polyline(
                        objects,
                        current_polyline
                    )

                    current_polyline = []

            # Flush remaining curve
            flush_polyline(
                objects,
                current_polyline
            )

        # ====================================================
        # TEXT
        # ====================================================

        text_dict = page.get_text(
            "dict",
            flags=11
        )

        for block in text_dict.get(
            "blocks",
            []
        ):

            # Ignore images / non-text blocks
            if block.get("type") != 0:
                continue

            for line in block.get(
                "lines",
                []
            ):

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

                    x = float(bbox[0])
                    y = float(bbox[3])

                    height = float(
                        span.get(
                            "size",
                            10.0
                        )
                    )

                    objects.append({
                        "type": "TEXT",
                        "text": text,
                        "position": [x, y],
                        "height": height,
                    })

        return objects, page_info

    finally:

        doc.close()
PY
