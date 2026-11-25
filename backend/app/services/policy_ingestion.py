import io
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image


POLICY_UPLOAD_DIR = (
    Path(__file__).resolve().parents[2]
    / "policy_uploads"
)


def extract_policy_text(
    file_path: Path,
) -> tuple[str, str]:
    """
    Extract text from a nonprofit policy PDF.

    First tries native PDF text extraction
    using PyMuPDF.

    If the PDF is scanned/image-only,
    falls back to Tesseract OCR.
    """

    if not file_path.is_file():
        raise FileNotFoundError(
            "Policy file was not found."
        )

    pdf = pymupdf.open(file_path)

    text_parts: list[str] = []

    # Try normal PDF text extraction first.
    for page in pdf:
        page_text = (
            page.get_text("text")
            .strip()
        )

        if page_text:
            text_parts.append(
                page_text
            )

    text = "\n".join(
        text_parts
    ).strip()

    if text:
        pdf.close()

        return (
            text,
            "pymupdf_text",
        )

    # OCR fallback for scanned PDFs.
    ocr_parts: list[str] = []

    for page in pdf:
        pixmap = page.get_pixmap(
            matrix=pymupdf.Matrix(
                2,
                2,
            ),
            alpha=False,
        )

        image = Image.open(
            io.BytesIO(
                pixmap.tobytes(
                    "png"
                )
            )
        )

        ocr_text = (
            pytesseract
            .image_to_string(
                image
            )
            .strip()
        )

        if ocr_text:
            ocr_parts.append(
                ocr_text
            )

    pdf.close()

    text = "\n".join(
        ocr_parts
    ).strip()

    if not text:
        raise ValueError(
            "No readable text could be extracted from the policy document."
        )

    return (
        text,
        "tesseract_ocr",
    )