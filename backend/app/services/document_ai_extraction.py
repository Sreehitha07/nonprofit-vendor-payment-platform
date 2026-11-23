import io
import re
from datetime import datetime
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image

from app.models.document import Document
from app.schemas.invoice_extraction import (
    ExtractedInvoice,
)


UPLOAD_DIR = (
    Path(__file__).resolve().parents[2]
    / "uploads"
)


def _extract_pdf_text(
    path: Path,
) -> tuple[str, str]:
    document = pymupdf.open(path)

    text_parts: list[str] = []

    for page in document:
        page_text = page.get_text(
            "text"
        ).strip()

        if page_text:
            text_parts.append(page_text)

    text = "\n".join(text_parts).strip()

    if text:
        return (
            text,
            "pymupdf_text",
        )

    # Scanned/image-only PDF fallback.
    ocr_parts: list[str] = []

    for page in document:
        pixmap = page.get_pixmap(
            matrix=pymupdf.Matrix(
                2,
                2,
            ),
            alpha=False,
        )

        image = Image.open(
            io.BytesIO(
                pixmap.tobytes("png")
            )
        )

        ocr_text = (
            pytesseract.image_to_string(
                image
            )
        )

        if ocr_text.strip():
            ocr_parts.append(
                ocr_text
            )

    return (
        "\n".join(
            ocr_parts
        ).strip(),
        "tesseract_ocr",
    )


def _extract_image_text(
    path: Path,
) -> tuple[str, str]:
    image = Image.open(path)

    text = (
        pytesseract.image_to_string(
            image
        )
    )

    return (
        text.strip(),
        "tesseract_ocr",
    )


def _normalize_date(
    value: str | None,
) -> str | None:
    if not value:
        return None

    value = value.strip()

    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%m/%d/%y",
        "%B %d, %Y",
        "%b %d, %Y",
    ]

    for date_format in formats:
        try:
            parsed = datetime.strptime(
                value,
                date_format,
            )

            return parsed.date().isoformat()

        except ValueError:
            continue

    return value


def _find_value(
    text: str,
    patterns: list[str],
) -> str | None:
    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return (
                match.group(1)
                .strip()
            )

    return None


def _extract_invoice_number(
    text: str,
) -> str | None:
    return _find_value(
        text,
        [
            r"invoice\s*(?:number|no\.?|#)\s*[:\-]?\s*([A-Z0-9_\-/]+)",
            r"invoice\s*[:\-]\s*([A-Z0-9_\-/]+)",
        ],
    )


def _extract_invoice_date(
    text: str,
) -> str | None:
    value = _find_value(
        text,
        [
            (
                r"invoice\s*date\s*[:\-]?\s*"
                r"([A-Za-z0-9,\-/ ]+)"
            ),
            (
                r"date\s*[:\-]?\s*"
                r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
            ),
        ],
    )

    if value:
        # Avoid capturing following labels.
        value = value.split("\n")[0]

    return _normalize_date(
        value
    )


def _extract_due_date(
    text: str,
) -> str | None:
    value = _find_value(
        text,
        [
            (
                r"due\s*date\s*[:\-]?\s*"
                r"([A-Za-z0-9,\-/ ]+)"
            ),
        ],
    )

    if value:
        value = value.split("\n")[0]

    return _normalize_date(
        value
    )


def _extract_currency(
    text: str,
) -> str | None:
    upper = text.upper()

    if "$" in text:
        return "USD"

    for currency in [
        "USD",
        "EUR",
        "GBP",
        "INR",
        "CAD",
        "AUD",
    ]:
        if currency in upper:
            return currency

    return None


def _money_to_float(
    value: str | None,
) -> float | None:
    if not value:
        return None

    cleaned = re.sub(
        r"[^\d.\-]",
        "",
        value,
    )

    try:
        return float(cleaned)

    except ValueError:
        return None


def _extract_total(
    text: str,
) -> float | None:
    patterns = [
        (
            r"(?:grand\s*total|amount\s*due|"
            r"invoice\s*total|total)"
            r"\s*[:\-]?\s*"
            r"(?:USD\s*)?\$?\s*"
            r"([\d,]+\.\d{2})"
        ),
    ]

    values: list[float] = []

    for pattern in patterns:
        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        for value in matches:
            parsed = _money_to_float(
                value
            )

            if parsed is not None:
                values.append(
                    parsed
                )

    if values:
        # Usually the largest total is the final total.
        return max(values)

    return None


def _extract_vendor_name(
    text: str,
) -> str | None:
    explicit = _find_value(
        text,
        [
            (
                r"(?:vendor|seller|from)"
                r"\s*[:\-]\s*"
                r"([^\n]+)"
            ),
        ],
    )

    if explicit:
        return explicit

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    # Common invoice layout:
    # vendor/business name appears near the top.
    for line in lines[:5]:
        lowered = line.lower()

        if any(
            keyword in lowered
            for keyword in [
                "invoice",
                "date",
                "bill to",
                "ship to",
            ]
        ):
            continue

        if len(line) >= 3:
            return line

    return None


def extract_invoice_document(
    document: Document,
) -> ExtractedInvoice:
    stored_path = (
        UPLOAD_DIR
        / document.stored_filename
    )

    if not stored_path.is_file():
        raise FileNotFoundError(
            "Stored document file was not found"
        )

    content_type = (
        document.content_type
        or ""
    ).lower()

    suffix = (
        stored_path.suffix.lower()
    )

    if (
        content_type
        == "application/pdf"
        or suffix == ".pdf"
    ):
        text, method = (
            _extract_pdf_text(
                stored_path
            )
        )

    elif (
        content_type.startswith(
            "image/"
        )
        or suffix
        in {
            ".png",
            ".jpg",
            ".jpeg",
        }
    ):
        text, method = (
            _extract_image_text(
                stored_path
            )
        )

    else:
        raise RuntimeError(
            "Unsupported document type"
        )

    if not text:
        raise RuntimeError(
            "No readable text could be extracted "
            "from the document"
        )

    invoice_number = (
        _extract_invoice_number(
            text
        )
    )

    invoice_date = (
        _extract_invoice_date(
            text
        )
    )

    due_date = (
        _extract_due_date(
            text
        )
    )

    currency = (
        _extract_currency(
            text
        )
    )

    total_amount = (
        _extract_total(
            text
        )
    )

    vendor_name = (
        _extract_vendor_name(
            text
        )
    )

    return ExtractedInvoice(
        vendor_name=vendor_name,

        invoice_number=
            invoice_number,

        invoice_date=
            invoice_date,

        due_date=
            due_date,

        currency=
            currency,

        total_amount=
            total_amount,

        # We'll improve local line-item
        # extraction after basic fields
        # are verified.
        line_items=[],

        document_type_guess=
            "invoice",

        extraction_method=
            method,

        raw_text=
            text[:10000],
    )