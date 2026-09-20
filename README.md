# PDF → Editable DXF — Frontend V1

Static frontend for the PDF2DXF backend.

## Backend
https://hendri.pythonanywhere.com

## Files
- `index.html`
- `style.css`
- `script.js`

## Deployment
Upload these three files to the GitHub Pages repository/branch used for the public frontend.

The frontend calls:
- `POST /pdf-info`
- `POST /convert`

V1 supports vector PDF drawings. Scanned/image-only PDFs are not supported yet.
