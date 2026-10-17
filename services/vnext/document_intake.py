"""Schema-independent, request-scoped quarantine boundary. No storage or extraction.

The future HTTP adapter MUST authorize workspace, case, purpose and sensitivity
before reading a stream. A receipt grants no permission to serve or retain bytes.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from datetime import datetime, timezone
from typing import Iterable, Literal
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
DocumentClass = Literal["registry_extract", "cadastral_map", "permit", "zoning", "valuation_attachment", "official_export"]


class DocumentRejected(ValueError):
    """Bounded code only; never includes user names, payloads or parser errors."""


class IntakeMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    document_class: DocumentClass
    observed_at: AwareDatetime
    effective_at: AwareDatetime | None = None
    expires_at: AwareDatetime | None = None

    @field_validator("observed_at", "effective_at", "expires_at", mode="before")
    @classmethod
    def timestamp_input(cls, value):
        if value is not None and not isinstance(value, datetime):
            if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", value):
                raise ValueError("invalid_timestamp")
        return value

    @model_validator(mode="after")
    def dates(self):
        if self.effective_at and self.expires_at and self.expires_at <= self.effective_at:
            raise ValueError("invalid_date_order")
        return self


class QuarantineReceipt(IntakeMetadata):
    workspace_id: UUID
    case_id: UUID
    document_id: UUID
    version_id: UUID
    sha256: str
    byte_length: int
    detected_media_type: str
    received_at: AwareDatetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_id: Literal["user-upload"] = "user-upload"
    scan_status: Literal["pending"] = "pending"
    extraction_status: Literal["not_attempted"] = "not_attempted"
    verification_status: Literal["unverified"] = "unverified"
    lifecycle: Literal["unknown"] = "unknown"


def _extension(filename: str) -> str:
    if not isinstance(filename, str) or not 1 <= len(filename) <= 160:
        raise DocumentRejected("unsafe_filename")
    # Names are validation hints only. They are never used as filesystem paths.
    if (filename != filename.strip() or any(unicodedata.category(c).startswith("C") for c in filename)
            or any(c in filename for c in '/\\:%<>"|?*') or ".." in filename):
        raise DocumentRejected("unsafe_filename")
    match = re.fullmatch(r"([^.]+)\.(pdf|png|jpg|jpeg|json)", filename, re.IGNORECASE)
    if not match or "." in match.group(1):
        raise DocumentRejected("unsupported_filename")
    if re.fullmatch(r"CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9]", match.group(1), re.IGNORECASE):
        raise DocumentRejected("unsafe_filename")
    return match.group(2).lower()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_key")
        result[key] = value
    return result


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non_finite")
    return number


def _detect(data: bytes, extension: str) -> str:
    if extension == "pdf" and re.match(rb"%PDF-1\.[0-7](?:\r|\n)", data) and data.rstrip().endswith(b"%%EOF"):
        # Decode PDF name escapes before the conservative active-content screen.
        names = re.sub(rb"#([0-9a-fA-F]{2})", lambda m: bytes([int(m[1], 16)]), data)
        if re.search(rb"/(?:JavaScript|JS|Launch|EmbeddedFile|Filespec|OpenAction|AA|RichMedia|Encrypt|XFA|AcroForm)\b", names, re.I):
            raise DocumentRejected("active_pdf_content")
        return "application/pdf"
    if extension == "png" and data.startswith(b"\x89PNG\r\n\x1a\n") and data.endswith(b'IEND\xaeB`\x82'):
        return "image/png"
    if extension in {"jpg", "jpeg"} and data.startswith(b"\xff\xd8\xff") and data.endswith(b"\xff\xd9"):
        return "image/jpeg"
    if extension == "json":
        try:
            parsed = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object,
                                parse_float=_finite_float,
                                parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non_finite")))
            if not isinstance(parsed, (dict, list)):
                raise ValueError("not_structured_export")
        except (UnicodeError, ValueError, RecursionError):
            raise DocumentRejected("invalid_data_export") from None
        return "application/json"
    raise DocumentRejected("unsupported_or_mismatched_type")


def inspect_document(*, chunks: Iterable[bytes], filename: str, metadata: dict,
                     workspace_id: UUID, case_id: UUID,
                     declared_content_type: str | None = None) -> QuarantineReceipt:
    """Inspect at most 10 MiB; caller-supplied MIME never grants authority.

    Signature checks reject obvious mismatches, not polyglots or malware. Every
    accepted receipt remains quarantined pending a real scanner and parser.
    No URL input, filesystem operations, logging, network, DB or provider calls.
    """
    if not isinstance(workspace_id, UUID) or not isinstance(case_id, UUID):
        raise DocumentRejected("invalid_scope")
    extension = _extension(filename)
    try:
        selected = IntakeMetadata.model_validate(metadata)
    except (ValidationError, TypeError):
        raise DocumentRejected("invalid_metadata") from None
    payload = bytearray()
    for chunk in chunks:
        if not isinstance(chunk, bytes) or len(payload) + len(chunk) > MAX_DOCUMENT_BYTES:
            raise DocumentRejected("invalid_or_oversized_upload")
        payload.extend(chunk)
    if not payload:
        raise DocumentRejected("empty_upload")
    data = bytes(payload)
    media_type = _detect(data, extension)
    return QuarantineReceipt(**selected.model_dump(), workspace_id=workspace_id, case_id=case_id,
                             document_id=uuid4(), version_id=uuid4(), sha256=hashlib.sha256(data).hexdigest(),
                             byte_length=len(data), detected_media_type=media_type)
