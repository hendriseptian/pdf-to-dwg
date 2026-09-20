import ezdxf
from pathlib import Path


def _pdf_to_dxf_xy(x, y, page_height):
    """
    Convert PDF's top-left Y direction into CAD's bottom-left Y direction.
    X is preserved.
    """
    return float(x), float(page_height - y)


def write_dxf(output_path, objects, page_info):
    """
    Write extracted PDF objects to an editable DXF.

    V1 deliberately preserves the PDF coordinate scale.
    No guessed mm/inch conversion is performed.
    """
    output_path = Path(output_path)

    doc = ezdxf.new("R2018", setup=True)

    # Keep the file effectively unit-neutral in V1.
    # PDF points are preserved so we do not invent a unit.
    doc.units = 0  # Unitless

    layers = {
        "PDF_LINE": 7,
        "PDF_POLYLINE": 7,
        "PDF_TEXT": 7,
    }

    for name, color in layers.items():
        if name not in doc.layers:
            doc.layers.add(name, color=color)

    msp = doc.modelspace()
    page_height = page_info["height"]

    for obj in objects:
        obj_type = obj["type"]

        if obj_type == "LINE":
            x1, y1 = _pdf_to_dxf_xy(
                obj["start"][0],
                obj["start"][1],
                page_height,
            )
            x2, y2 = _pdf_to_dxf_xy(
                obj["end"][0],
                obj["end"][1],
                page_height,
            )

            msp.add_line(
                (x1, y1),
                (x2, y2),
                dxfattribs={"layer": "PDF_LINE"},
            )

        elif obj_type == "POLYLINE":
            points = [
                _pdf_to_dxf_xy(p[0], p[1], page_height)
                for p in obj["points"]
            ]

            if len(points) >= 2:
                msp.add_lwpolyline(
                    points,
                    close=obj.get("closed", False),
                    dxfattribs={"layer": "PDF_POLYLINE"},
                )

        elif obj_type == "TEXT":
            x, y = _pdf_to_dxf_xy(
                obj["position"][0],
                obj["position"][1],
                page_height,
            )

            text_entity = msp.add_text(
                obj["text"],
                dxfattribs={
                    "layer": "PDF_TEXT",
                    "height": max(float(obj.get("height", 10.0)), 0.1),
                },
            )
            text_entity.dxf.insert = (x, y)

    doc.saveas(output_path)

    return output_path
