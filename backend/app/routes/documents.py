from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import (
    ensure_vendor_access,
    get_current_user,
    require_roles,
)
from app.models.document import Document
from app.models.invoice import Invoice
from app.models.user import User
from app.schemas.document import DocumentResponse


router = APIRouter(tags=["Documents"])


UPLOAD_DIR = (
    Path(__file__).resolve().parents[2]
    / "uploads"
)

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_FILES = {
    ".pdf": {"application/pdf"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
}

ALLOWED_DOCUMENT_TYPES = {
    "invoice",
    "purchase_order",
    "receipt",
    "supporting_document",
}


def get_authorized_invoice(
    invoice_id: int,
    current_user: User,
    db: Session,
) -> Invoice:
    invoice = db.get(
        Invoice,
        invoice_id,
    )

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found",
        )

    ensure_vendor_access(
        current_user,
        invoice.vendor_id,
        invoice.nonprofit_id,
    )

    return invoice


@router.post(
    "/api/invoices/{invoice_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    invoice_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_authorized_invoice(
        invoice_id,
        current_user,
        db,
    )

    if document_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid document type. "
                "Allowed types: invoice, purchase_order, "
                "receipt, supporting_document"
            ),
        )

    original_filename = Path(
        file.filename or ""
    ).name

    if not original_filename:
        raise HTTPException(
            status_code=400,
            detail="File must have a filename",
        )

    extension = Path(
        original_filename
    ).suffix.lower()

    if extension not in ALLOWED_FILES:
        raise HTTPException(
            status_code=415,
            detail=(
                "Unsupported file type. "
                "Only PDF, PNG, JPG, and JPEG are allowed"
            ),
        )

    if file.content_type not in ALLOWED_FILES[extension]:
        raise HTTPException(
            status_code=415,
            detail="File extension and content type do not match",
        )

    stored_filename = (
        f"{uuid4().hex}{extension}"
    )

    stored_path = (
        UPLOAD_DIR / stored_filename
    )

    file_size = 0

    try:
        with stored_path.open("wb") as buffer:
            while chunk := await file.read(
                1024 * 1024
            ):
                file_size += len(chunk)

                if file_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "File is too large. "
                            "Maximum size is 10 MB"
                        ),
                    )

                buffer.write(chunk)

    except Exception:
        stored_path.unlink(
            missing_ok=True
        )
        raise

    finally:
        await file.close()

    if file_size == 0:
        stored_path.unlink(
            missing_ok=True
        )

        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty",
        )

    document = Document(
        invoice_id=invoice_id,
        uploaded_by_user_id=current_user.id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        document_type=document_type,
        content_type=file.content_type,
        file_size=file_size,
        verification_status="pending",
    )

    try:
        db.add(document)
        db.commit()
        db.refresh(document)

    except Exception:
        db.rollback()

        stored_path.unlink(
            missing_ok=True
        )

        raise

    return document


@router.get(
    "/api/invoices/{invoice_id}/documents",
    response_model=list[DocumentResponse],
)
def list_documents(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_authorized_invoice(
        invoice_id,
        current_user,
        db,
    )

    query = (
        select(Document)
        .where(
            Document.invoice_id
            == invoice_id
        )
        .order_by(
            Document.id.desc()
        )
    )

    return db.scalars(
        query
    ).all()


@router.get(
    "/api/documents/{document_id}/download",
)
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.get(
        Document,
        document_id,
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    invoice = get_authorized_invoice(
        document.invoice_id,
        current_user,
        db,
    )

    stored_path = (
        UPLOAD_DIR
        / document.stored_filename
    )

    if not stored_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Stored document file not found",
        )

    return FileResponse(
        path=stored_path,
        media_type=document.content_type,
        filename=document.original_filename,
    )


@router.delete(
    "/api/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "vendor",
            "staff",
            "manager",
            "admin",
        )
    ),
):
    document = db.get(
        Document,
        document_id,
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    get_authorized_invoice(
        document.invoice_id,
        current_user,
        db,
    )

    stored_path = (
        UPLOAD_DIR
        / document.stored_filename
    )

    db.delete(document)
    db.commit()

    stored_path.unlink(
        missing_ok=True
    )