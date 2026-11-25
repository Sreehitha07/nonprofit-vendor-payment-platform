from functools import lru_cache

from sentence_transformers import SentenceTransformer
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.policy_chunk import PolicyChunk
from app.models.policy_document import PolicyDocument


MODEL_NAME = (
    "sentence-transformers/"
    "all-MiniLM-L6-v2"
)

CHUNK_SIZE_WORDS = 160
CHUNK_OVERLAP_WORDS = 30


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Load the local embedding model once and reuse it.
    """
    return SentenceTransformer(
        MODEL_NAME
    )


def clean_text(text: str) -> str:
    """
    Normalize whitespace while keeping the text readable.
    """
    return " ".join(
        text.split()
    ).strip()


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE_WORDS,
    overlap: int = CHUNK_OVERLAP_WORDS,
) -> list[str]:
    """
    Split policy text into overlapping chunks.

    Example:
        chunk 1 = words 0-159
        chunk 2 = words 130-289
        ...
    """
    cleaned = clean_text(text)

    if not cleaned:
        return []

    words = cleaned.split()

    chunks: list[str] = []

    start = 0

    while start < len(words):
        end = min(
            start + chunk_size,
            len(words),
        )

        chunk = " ".join(
            words[start:end]
        ).strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(words):
            break

        start = end - overlap

    return chunks


def generate_embeddings(
    texts: list[str],
) -> list[list[float]]:
    """
    Generate normalized local embeddings.
    """
    if not texts:
        return []

    model = get_embedding_model()

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    return embeddings.tolist()


def store_policy_chunks(
    db: Session,
    policy_document: PolicyDocument,
    text: str,
) -> int:
    """
    Split a policy document into chunks,
    generate embeddings and store them
    in PostgreSQL/pgvector.
    """
    chunks = chunk_text(text)

    if not chunks:
        policy_document.processing_status = (
            "failed"
        )

        db.commit()

        raise ValueError(
            "Policy document contains no readable text."
        )

    embeddings = generate_embeddings(
        chunks
    )

    # Remove old chunks if this policy
    # document is processed again.
    db.execute(
        delete(PolicyChunk).where(
            PolicyChunk.policy_document_id
            == policy_document.id
        )
    )

    for index, (
        chunk,
        embedding,
    ) in enumerate(
        zip(
            chunks,
            embeddings,
            strict=True,
        )
    ):
        db.add(
            PolicyChunk(
                policy_document_id=
                    policy_document.id,

                chunk_index=index,

                content=chunk,

                embedding=embedding,
            )
        )

    policy_document.processing_status = (
        "processed"
    )

    db.commit()

    return len(chunks)


def retrieve_policy_chunks(
    db: Session,
    nonprofit_id: int,
    query: str,
    limit: int = 5,
    max_distance: float = 0.65,
) -> list[dict]:
    """
    Find the policy chunks most semantically
    similar to the supplied query.
    """
    query_text = clean_text(
        query
    )

    if not query_text:
        return []

    query_embedding = (
        generate_embeddings(
            [query_text]
        )[0]
    )

    distance = (
        PolicyChunk.embedding
        .cosine_distance(
            query_embedding
        )
        .label(
            "distance"
        )
    )

    statement = (
        select(
            PolicyChunk,
            PolicyDocument,
            distance,
        )
        .join(
            PolicyDocument,
            PolicyDocument.id
            == PolicyChunk.policy_document_id,
        )
        .where(
            PolicyDocument.nonprofit_id
            == nonprofit_id
        )
        .order_by(
            distance
        )
        .limit(
            limit
        )
    )

    rows = db.execute(
        statement
    ).all()

    results = []

    for (
        chunk,
        document,
        chunk_distance,
    ) in rows:

        distance_value = float(
            chunk_distance
        )

    # Ignore weak semantic matches.
    # Smaller cosine distance means
    # greater semantic similarity.
        if distance_value > max_distance:
            continue

        results.append(
            {
                "chunk_id":
                    chunk.id,

                "policy_document_id":
                    document.id,

                "policy_title":
                    document.title,

                "chunk_index":
                    chunk.chunk_index,

                "content":
                    chunk.content,

                "distance":
                    distance_value,
            }
        )
    return results