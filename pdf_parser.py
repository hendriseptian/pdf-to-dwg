import pymupdf as fitz


# ============================================================
# PDF PARSER - OPTIMIZED V1.1
# ============================================================

# Curve sampling.
# V1 sebelumnya menggunakan 24 steps.
# V1.1 menggunakan 8 untuk mengurangi jumlah vertex DXF.
CURVE_STEPS = 8


def _point_xy(point):
    """Convert PyMuPDF point-like object to [x, y]."""
    return [float(point.x), float(point.y)]


def _points_equal(p1, p2, tolerance=0.001):
    """Check whether two points are effectively identical."""
    return (
        abs(p1[0] - p2[0]) <= tolerance
        and abs(p1[1] - p2[1]) <= tolerance
    )


def _append_point(points, point):
    """
    Append a point only when it is different from
    the previous point.
    """
    xy = _point_xy(point)

    if not points or not _points_equal(points[-1], xy):
        points.append(xy)


def _cubic_bezier(p0, p1, p2, p3, steps=CURVE_STEPS):
    """
    Approximate cubic Bézier curve with a polyline.

    Lower sampling reduces DXF entity size and processing time.
    """
    result = []

    p0 = _point_xy(p0)
    p1 = _point_xy(p1)
    p2 = _point_xy(p2)
    p3 = _point_xy(p3)

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

        if not result or not _points_equal(
            result[-1],
            point
        ):
            result.append(point)

    return result


def _rect_to_polyline(rect):
    """Convert PDF rectangle to closed polyline."""
    x0 = float(rect.x0)
    y0 = float(rect.y0)
    x1 = float(rect.x1)
    y1 = float(rect.y1)

    return [
        [x0, y0],
        [x1, y0],
        [x1, y1],
        [x0, y1],
        [x0, y0],
    ]


def _quad_to_polyline(quad):
    """Convert PDF quad to closed polyline."""
    return [
        _point_xy(quad.ul),
        _point_xy(quad.ur),
        _point_xy(quad.lr),
        _point_xy(quad.ll),
        _point_xy(quad.ul),
    ]


def extract_pdf_page(pdf_path, page_number):
    """
    Extract vector geometry and text from one PDF page.

    Returns:
        objects   : list of parsed drawing/text objects
        page_info : page metadata
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
        # VECTOR DRAWINGS
        # ====================================================

        drawings = page.get_drawings()

        for drawing in drawings:

            items = drawing.get("items", [])

            current_polyline = []

            def flush_polyline():
                nonlocal current_polyline

                if len(current_polyline) >= 2:

                    # Remove duplicate closing points
                    cleaned = []

                    for point in current_polyline:
                        if (
                            not cleaned
                            or not _points_equal(
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

                    p1 = _point_xy(item[1])
                    p2 = _point_xy(item[2])

                    if not _points_equal(p1, p2):
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

                    rect_item = item[1]

                    points = _rect_to_polyline(
                        rect_item
                    )

                    objects.append({
                        "type": "POLYLINE",
                        "points": points,
                    })

                # --------------------------------------------
                # QUAD
                # --------------------------------------------

                elif item_type == "qu":

                    flush_polyline()

                    quad = item[1]

                    points = _quad_to_polyline(
                        quad
                    )

                    objects.append({
                        "type": "POLYLINE",
                        "points": points,
                    })

                # --------------------------------------------
                # CUBIC BÉZIER CURVE
                # --------------------------------------------

                elif item_type == "c":

                    # PyMuPDF cubic item:
                    # ('c', p1, p2, p3, p4)

                    curve_points = _cubic_bezier(
                        item[1],
                        item[2],
                        item[3],
                        item[4],
                        CURVE_STEPS,
                    )

                    for point in curve_points:

                        if (
                            not current_polyline
                            or not _points_equal(
                                current_polyline[-1],
                                point,
                            )
                        ):
                            current_polyline.append(
                                point
                            )

                # --------------------------------------------
                # UNKNOWN DRAWING TYPE
                # --------------------------------------------

                else:

                    flush_polyline()

            # Flush remaining curve/polyline
            flush_polyline()

        # ====================================================
        # TEXT
        # ====================================================

        text_dict = page.get_text("dict")

        for block in text_dict.get("blocks", []):

            if block.get("type") != 0:
                continue

            for line in block.get("lines", []):

                for span in line.get("spans", []):

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

                    font_size = float(
                        span.get(
                            "size",
                            10.0
                        )
                    )

                    objects.append({
                        "type": "TEXT",
                        "text": text,
                        "position": [x, y],
                        "height": font_size,
                    })

        return objects, page_info

    finally:
        doc.close()
