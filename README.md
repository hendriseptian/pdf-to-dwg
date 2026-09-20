# PDF2DXF

Online PDF → Editable DXF converter.

## V1 scope

- One PDF upload
- Select one sheet/page
- Vector PDF conversion
- LINE
- POLYLINE
- Rectangle
- Quadrilateral
- Bezier curves approximated as polylines
- TEXT
- Editable DXF output
- No database
- No permanent PDF storage
- No AI
- No OCR in V1

## Important coordinate/unit behavior

PDF coordinates are preserved in PDF points.

The converter does **not** guess mm or inch in V1. The DXF is therefore created as unitless while preserving the PDF geometry scale.

This avoids silently applying an incorrect engineering scale.

## Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## API

### GET /

Health/status endpoint.

### GET /health

Returns:

```json
{"status":"ok"}
```

### POST /pdf-info

Upload a PDF to get the number of sheets/pages and page sizes.

### POST /convert

Form fields:

- `file`: PDF file
- `page`: 1-based page/sheet number

Example with curl:

```bash
curl -X POST "http://127.0.0.1:8000/convert" \
  -F "file=@drawing.pdf" \
  -F "page=1" \
  -o drawing.dxf
```

## Render

For Render Web Service:

- Runtime: Python
- Build command:

```text
pip install -r requirements.txt
```

- Start command:

```text
uvicorn main:app --host 0.0.0.0 --port $PORT
```

The frontend will call the deployed `/pdf-info` and `/convert` endpoints.

## Security note

This V1 is intended as a prototype. Uploaded PDFs are processed temporarily and the source PDF is removed after processing. The generated DXF remains temporarily on the server so it can be returned to the client; a production version should add automatic cleanup of old output files and stricter upload/rate limits.
