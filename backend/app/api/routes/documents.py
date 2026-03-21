import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import (
    EMBEDDING_DIMENSION,
    RETRIEVAL_MIN_SIMILARITY,
    RETRIEVAL_TOP_K,
    STORAGE_DIR,
)
from app.db.database import get_db
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.ingestion.processing import process_uploaded_document
from app.qa.service import answer_document_question
from app.retrieval.service import retrieve_relevant_chunks

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".doc", ".docx"}
WRITE_CHUNK_SIZE = 1024 * 1024


class DocumentMetadataResponse(BaseModel):
    id: int
    company_name: str
    document_type: str
    period: str
    source_filename: str
    storage_path: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentProcessResponse(BaseModel):
    document_id: int
    status: str
    chunk_count: int


class DocumentChunkSummaryResponse(BaseModel):
    chunk_index: int
    page_number: int | None
    text: str
    token_count: int


class DocumentChunksResponse(BaseModel):
    document_id: int
    status: str
    chunk_count: int
    embedding_dimension: int
    chunks: list[DocumentChunkSummaryResponse]


class DocumentRetrievalRequest(BaseModel):
    question: str
    top_k: int | None = None
    min_similarity: float | None = None


class DocumentRetrievedChunkResponse(BaseModel):
    chunk_index: int
    page_number: int | None
    text: str
    token_count: int
    similarity: float


class DocumentRetrievalResponse(BaseModel):
    document_id: int
    question: str
    top_k: int
    min_similarity: float
    result_count: int
    chunks: list[DocumentRetrievedChunkResponse]


class DocumentAskRequest(BaseModel):
    question: str
    top_k: int | None = None
    min_similarity: float | None = None


class DocumentCitationResponse(BaseModel):
    citation_id: str
    rank: int
    document_id: int
    chunk_index: int
    page_number: int | None
    text_excerpt: str
    retrieval_score: float


class DocumentAskResponse(BaseModel):
    question: str
    answer: str
    status: str
    citations: list[DocumentCitationResponse]


def _sanitize_path_component(value: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip()).strip("._")
    return sanitized or "unknown"


@router.get("", response_model=list[DocumentMetadataResponse])
async def list_documents(db: Session = Depends(get_db)) -> list[Document]:
    documents = db.query(Document).order_by(Document.id.asc()).all()
    return documents


@router.get("/{document_id}", response_model=DocumentMetadataResponse)
async def get_document(document_id: int, db: Session = Depends(get_db)) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


@router.post("/{document_id}/process", response_model=DocumentProcessResponse)
async def process_document(document_id: int, db: Session = Depends(get_db)) -> DocumentProcessResponse:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    document.status = "processing"
    db.commit()
    db.refresh(document)

    try:
        chunk_count = process_uploaded_document(db=db, document_id=document_id)
    except Exception as exc:
        db.rollback()

        failed_document = db.get(Document, document_id)
        if failed_document is not None:
            failed_document.status = "failed"
            try:
                db.commit()
            except SQLAlchemyError:
                db.rollback()

        detail = str(exc)
        status_code = 400 if "Unsupported document extension" in detail else 500
        raise HTTPException(
            status_code=status_code,
            detail=f"Document processing failed: {detail}",
        ) from exc

    ready_document = db.get(Document, document_id)
    if ready_document is None:
        raise HTTPException(status_code=500, detail="Document was not found after processing.")

    ready_document.status = "ready"
    db.commit()
    db.refresh(ready_document)

    return DocumentProcessResponse(
        document_id=ready_document.id,
        status=ready_document.status,
        chunk_count=chunk_count,
    )


@router.get("/{document_id}/chunks", response_model=DocumentChunksResponse)
async def get_document_chunks(
    document_id: int, db: Session = Depends(get_db)
) -> DocumentChunksResponse:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )

    return DocumentChunksResponse(
        document_id=document.id,
        status=document.status,
        chunk_count=len(chunks),
        embedding_dimension=EMBEDDING_DIMENSION,
        chunks=[
            DocumentChunkSummaryResponse(
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                text=chunk.text,
                token_count=chunk.token_count,
            )
            for chunk in chunks
        ],
    )


@router.post("/{document_id}/retrieve", response_model=DocumentRetrievalResponse)
async def retrieve_document_chunks(
    document_id: int,
    payload: DocumentRetrievalRequest,
    db: Session = Depends(get_db),
) -> DocumentRetrievalResponse:
    top_k = payload.top_k if payload.top_k is not None else RETRIEVAL_TOP_K
    min_similarity = (
        payload.min_similarity
        if payload.min_similarity is not None
        else RETRIEVAL_MIN_SIMILARITY
    )

    try:
        retrieved_chunks = retrieve_relevant_chunks(
            db=db,
            document_id=document_id,
            question=payload.question,
            top_k=top_k,
            min_similarity=min_similarity,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail.endswith("was not found.") else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return DocumentRetrievalResponse(
        document_id=document_id,
        question=payload.question,
        top_k=top_k,
        min_similarity=min_similarity,
        result_count=len(retrieved_chunks),
        chunks=[
            DocumentRetrievedChunkResponse(
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                text=chunk.text,
                token_count=chunk.token_count,
                similarity=chunk.similarity,
            )
            for chunk in retrieved_chunks
        ],
    )


@router.post("/{document_id}/ask", response_model=DocumentAskResponse)
async def ask_document_question(
    document_id: int,
    payload: DocumentAskRequest,
    db: Session = Depends(get_db),
) -> DocumentAskResponse:
    top_k = payload.top_k if payload.top_k is not None else RETRIEVAL_TOP_K
    min_similarity = (
        payload.min_similarity
        if payload.min_similarity is not None
        else RETRIEVAL_MIN_SIMILARITY
    )

    try:
        result = answer_document_question(
            db=db,
            document_id=document_id,
            question=payload.question,
            top_k=top_k,
            min_similarity=min_similarity,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail.endswith("was not found.") else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return DocumentAskResponse(
        question=result.question,
        answer=result.answer,
        status=result.status,
        citations=[
            DocumentCitationResponse(
                citation_id=citation.citation_id,
                rank=citation.rank,
                document_id=citation.document_id,
                chunk_index=citation.chunk_index,
                page_number=citation.page_number,
                text_excerpt=citation.text_excerpt,
                retrieval_score=citation.retrieval_score,
            )
            for citation in result.citations
        ],
    )


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
