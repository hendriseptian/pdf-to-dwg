from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.background import BackgroundTask
from pathlib import Path
import uuid

from pdf_parser import extract_pdf_page, get_pdf_info
from dxf_writer import write_dxf


app = FastAPI(
    title="PDF2DXF",
    version="1.0.0",
    description="Convert one PDF sheet/page into an editable DXF."
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024


def cleanup_files(*paths):
    for path in paths:
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:
            pass


@app.get("/")
def root():
    return {
        "app": "PDF2DXF",
        "status": "online",
        "version": "1.0.0"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/convert")
async def convert_pdf_to_dxf(
    file: UploadFile = File(...),
    page: int = Form(1),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    if page < 1:
        raise HTTPException(
            status_code=400,
            detail="Page must be 1 or greater."
        )

    job_id = uuid.uuid4().hex

    pdf_path = TEMP_DIR / f"{job_id}.pdf"
    dxf_path = TEMP_DIR / f"{Path(file.filename).stem}_sheet_{page}_{job_id}.dxf"

    conversion_success = False

    try:
        content = await file.read()

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="PDF is larger than the 50 MB V1 limit."
            )

        pdf_path.write_bytes(content)

        objects, page_info = extract_pdf_page(
            pdf_path,
            page
        )

        write_dxf(
            dxf_path,
            objects,
            page_info
        )

        if not dxf_path.exists():
            raise HTTPException(
                status_code=500,
                detail="DXF file was not created."
            )

        conversion_success = True

        return FileResponse(
            path=dxf_path,
            media_type="application/dxf",
            filename=dxf_path.name,
            background=BackgroundTask(
                cleanup_files,
                pdf_path,
                dxf_path
            ),
        )

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Conversion failed: {exc}"
        )

    finally:
        cleanup_files(pdf_path)

        if not conversion_success:
            cleanup_files(dxf_path)


@app.post("/pdf-info")
async def pdf_info(
    file: UploadFile = File(...)
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    job_id = uuid.uuid4().hex
    pdf_path = TEMP_DIR / f"{job_id}.pdf"

    try:
        content = await file.read()

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="PDF is larger than the 50 MB V1 limit."
            )

        pdf_path.write_bytes(content)

        return get_pdf_info(pdf_path)

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read PDF: {exc}"
        )

    finally:
        cleanup_files(pdf_path)
