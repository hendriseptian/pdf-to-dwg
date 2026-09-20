import fitz  # PyMuPDF
from pathlib import Path


def _color_to_rgb(color):
    """Convert PyMuPDF integer RGB color to an RGB tuple."""
    if color is None:
        return None

    try:
        return (
            (color >> 16) & 255,
            (color >> 8) & 255,
            color & 255,
        )
    except Exception:
        return None


def _append_line(objects, p1, p2):
    objects.append({
        "type": "LINE",
        "start": [float(p1.x), float(p1.y)],
        "end": [float(p2.x), float(p2.y)],
    })


def _append_polyline(objects, points, closed=False):
    if len(points) < 2:
        return

    objects.append({
        "type": "POLYLINE",
        "points": [[float(p.x), float(p.y)] for p in points],
        "closed": bool(closed),
    })


def extract_pdf_page(pdf_path, page_number):
    """
    Extract vector drawing objects and text from one PDF page.

    PDF coordinates are preserved in PDF points.
    No arbitrary mm/inch conversion is applied in V1.
    """
    pdf_path = Path(pdf_path)

    doc = fitz.open(pdf_path)

    try:
        page_count = len(doc)

        if page_number < 1 or page_number > page_count:
            raise ValueError(
                f"PDF has {page_count} sheet(s). "
                f"Requested sheet {page_number} does not exist."
            )

        page = doc[page_number - 1]
        rect = page.rect

        objects = []

        # Vector drawings: lines, rectangles, curves, etc.
        drawings = page.get_drawings()

        for drawing in drawings:
            for item in drawing.get("items", []):
                op = item[0]

                if op == "l":
                    p1, p2 = item[1], item[2]
                    _append_line(objects, p1, p2)

                elif op == "re":
                    rect_obj = item[1]
                    points = [
                        fitz.Point(rect_obj.x0, rect_obj.y0),
                        fitz.Point(rect_obj.x1, rect_obj.y0),
                        fitz.Point(rect_obj.x1, rect_obj.y1),
                        fitz.Point(rect_obj.x0, rect_obj.y1),
                    ]
                    _append_polyline(objects, points, closed=True)

                elif op == "qu":
                    quad = item[1]
                    points = [quad.ul, quad.ur, quad.lr, quad.ll]
                    _append_polyline(objects, points, closed=True)

                elif op == "c":
                    # Cubic Bezier curve. V1 approximates it with a polyline.
                    p0, p1, p2, p3 = item[1], item[2], item[3], item[4]
                    curve_points = []

                    steps = 24
                    for i in range(steps + 1):
                        t = i / steps
                        mt = 1 - t
                        x = (
                            mt**3 * p0.x
                            + 3 * mt**2 * t * p1.x
                            + 3 * mt * t**2 * p2.x
                            + t**3 * p3.x
                        )
                        y = (
                            mt**3 * p0.y
                            + 3 * mt**2 * t * p1.y
                            + 3 * mt * t**2 * p2.y
                            + t**3 * p3.y
                        )
                        curve_points.append(fitz.Point(x, y))

                    _append_polyline(objects, curve_points, closed=False)

        # Text extraction.
        text_dict = page.get_text("dict")

        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if not text.strip():
                        continue

                    bbox = span.get("bbox", [0, 0, 0, 0])
                    x = (bbox[0] + bbox[2]) / 2
                    y = (bbox[1] + bbox[3]) / 2

                    objects.append({
                        "type": "TEXT",
                        "text": text,
                        "position": [float(x), float(y)],
                        "height": float(span.get("size", 10.0)),
                        "font": span.get("font", ""),
                        "color": _color_to_rgb(span.get("color")),
                    })

        page_info = {
            "page": page_number,
            "page_count": page_count,
            "width": float(rect.width),
            "height": float(rect.height),
            "pdf_unit": "PDF point",
        }

        return objects, page_info

    finally:
        doc.close()


def get_pdf_info(pdf_path):
    """Return basic information used by the frontend sheet selector."""
    doc = fitz.open(pdf_path)

    try:
        pages = []

        for index, page in enumerate(doc):
            rect = page.rect
            pages.append({
                "sheet": index + 1,
                "width": round(float(rect.width), 3),
                "height": round(float(rect.height), 3),
            })

        return {
            "filename": Path(pdf_path).name,
            "page_count": len(doc),
            "pages": pages,
        }
    finally:
        doc.close()
