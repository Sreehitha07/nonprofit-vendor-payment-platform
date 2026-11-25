from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import (
    get_current_user,
    require_roles,
)
from app.models.policy_document import (
    PolicyDocument,
)
from app.models.user import User
from app.services.policy_ingestion import (
    POLICY_UPLOAD_DIR,
    extract_policy_text,
)
from app.services.policy_rag import (
    retrieve_policy_chunks,
    store_policy_chunks,
)


router = APIRouter(
    prefix="/api/policies",
    tags=["Policy RAG"],
)


MAX_POLICY_FILE_SIZE = 10 * 1024 * 1024


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
)
async def upload_policy_document(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "staff",
            "manager",
            "admin",
        )
    ),
):
    """
    Upload a nonprofit policy PDF.

    The document is:
    1. saved locally,
    2. converted to text,
    3. split into chunks,
    4. embedded locally,
    5. stored in PostgreSQL/pgvector.
    """

    if not title.strip():
        raise HTTPException(
            status_code=400,
            detail="Policy title is required.",
        )

    content_type = (
        file.content_type or ""
    ).lower()

    if content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail=(
                "Only PDF policy documents "
                "are supported."
            ),
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail=(
                "Uploaded policy document "
                "is empty."
            ),
        )

    if (
        len(file_bytes)
        > MAX_POLICY_FILE_SIZE
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Policy document exceeds "
                "the 10 MB limit."
            ),
        )

    POLICY_UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    original_filename = (
        file.filename or "policy.pdf"
    )

    stored_filename = (
        f"{uuid4().hex}.pdf"
    )

    stored_path = (
        POLICY_UPLOAD_DIR
        / stored_filename
    )

    stored_path.write_bytes(
        file_bytes
    )

    policy = PolicyDocument(
        nonprofit_id=
            current_user.nonprofit_id,

        uploaded_by_user_id=
            current_user.id,

        title=
            title.strip(),

        original_filename=
            original_filename,

        stored_filename=
            stored_filename,

        content_type=
            content_type,

        file_size=
            len(file_bytes),

        processing_status=
            "pending",
    )

    db.add(policy)
    db.commit()
    db.refresh(policy)

    try:
        text, extraction_method = (
            extract_policy_text(
                stored_path
            )
        )

        chunk_count = (
            store_policy_chunks(
                db=db,
                policy_document=policy,
                text=text,
            )
        )

    except Exception as exc:
        policy.processing_status = (
            "failed"
        )

        db.commit()

        raise HTTPException(
            status_code=500,
            detail=(
                "Policy document processing "
                f"failed: {str(exc)}"
            ),
        ) from exc

    return {
        "id":
            policy.id,

        "title":
            policy.title,

        "original_filename":
            policy.original_filename,

        "processing_status":
            policy.processing_status,

        "extraction_method":
            extraction_method,

        "chunk_count":
            chunk_count,
    }


@router.get("")
def list_policy_documents(
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    List policy documents belonging
    to the current nonprofit.
    """

    statement = (
        select(
            PolicyDocument
        )
        .where(
            PolicyDocument.nonprofit_id
            == current_user.nonprofit_id
        )
        .order_by(
            PolicyDocument.created_at.desc()
        )
    )

    policies = (
        db.execute(statement)
        .scalars()
        .all()
    )

    return [
        {
            "id":
                policy.id,

            "title":
                policy.title,

            "original_filename":
                policy.original_filename,

            "content_type":
                policy.content_type,

            "file_size":
                policy.file_size,

            "processing_status":
                policy.processing_status,

            "created_at":
                policy.created_at,

            "updated_at":
                policy.updated_at,
        }
        for policy in policies
    ]


@router.get(
    "/search"
)
def search_policy_documents(
    query: str = Query(
        ...,
        min_length=2,
    ),
    limit: int = Query(
        5,
        ge=1,
        le=10,
    ),
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_roles(
            "staff",
            "manager",
            "admin",
        )
    ),
):
    """
    Search policy chunks using
    local sentence-transformer
    embeddings and pgvector.
    """

    results = (
        retrieve_policy_chunks(
            db=db,

            nonprofit_id=
                current_user.nonprofit_id,

            query=query,

            limit=limit,
        )
    )

    return {
        "query":
            query,

        "result_count":
            len(results),

        "results":
            results,
    }


@router.get(
    "/{policy_id}"
)
def get_policy_document(
    policy_id: int,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Return one policy document
    belonging to the current nonprofit.
    """

    policy = (
        db.execute(
            select(
                PolicyDocument
            ).where(
                PolicyDocument.id
                == policy_id,

                PolicyDocument.nonprofit_id
                == current_user.nonprofit_id,
            )
        )
        .scalar_one_or_none()
    )

    if policy is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Policy document not found."
            ),
        )

    return {
        "id":
            policy.id,

        "title":
            policy.title,

        "original_filename":
            policy.original_filename,

        "content_type":
            policy.content_type,

        "file_size":
            policy.file_size,

        "processing_status":
            policy.processing_status,

        "created_at":
            policy.created_at,

        "updated_at":
            policy.updated_at,

        "chunk_count":
            len(policy.chunks),
    }