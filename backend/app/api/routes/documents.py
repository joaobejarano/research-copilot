import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import STORAGE_DIR
from app.db.database import get_db
from app.db.models.document import Document

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".doc", ".docx"}
WRITE_CHUNK_SIZE = 1024 * 1024


def _sanitize_path_component(value: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip()).strip("._")
    return sanitized or "unknown"


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    company_name: str = Form(...),
    document_type: str = Form(...),
    period: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict[str, str | int]:
    filename = file.filename or ""
    extension = Path(filename).suffix.lower()

    if not filename:
        raise HTTPException(status_code=400, detail="Uploaded file must include a filename.")
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{extension or 'none'}'.",
        )

    document = Document(
        company_name=company_name,
        document_type=document_type,
        period=period,
        source_filename=filename,
        storage_path="pending",
        status="uploaded",
    )
    db.add(document)
    db.flush()

    relative_path = (
        Path(_sanitize_path_component(company_name))
        / _sanitize_path_component(document_type)
        / _sanitize_path_component(period)
        / f"{document.id}{extension}"
    )
    storage_path = STORAGE_DIR / relative_path
    storage_path.parent.mkdir(parents=True, exist_ok=True)

    source_file = file.file

    try:
        with storage_path.open("wb") as output_file:
            while True:
                chunk = source_file.read(WRITE_CHUNK_SIZE)
                if not chunk:
                    break
                output_file.write(chunk)
    except OSError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Could not store the uploaded file."
        ) from exc
    finally:
        source_file.close()

    document.storage_path = str(relative_path)

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        storage_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500, detail="Could not save document metadata."
        ) from exc

    db.refresh(document)

    return {
        "id": document.id,
        "company_name": document.company_name,
        "document_type": document.document_type,
        "period": document.period,
        "source_filename": document.source_filename,
        "status": document.status,
        "created_at": document.created_at.isoformat(),
    }
