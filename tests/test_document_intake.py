from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from services.vnext import document_intake as intake

SCOPE = {"workspace_id": UUID(int=1), "case_id": UUID(int=2)}
NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)


def metadata(**overrides):
    return {"document_class": "registry_extract", "observed_at": NOW,
            "effective_at": None, "expires_at": None, **overrides}


def receive(data=b'%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\n%%EOF', **kwargs):
    return intake.inspect_document(chunks=[data], filename=kwargs.pop("filename", "extract.pdf"),
                                   metadata=kwargs.pop("metadata", metadata()), **SCOPE, **kwargs)


def test_quarantine_is_not_extraction_or_verification():
    receipt = receive()
    assert receipt.scan_status == "pending"
    assert receipt.extraction_status == "not_attempted"
    assert receipt.verification_status == "unverified"
    assert receipt.lifecycle == "unknown"
    assert receipt.source_id == "user-upload"
    assert receipt.detected_media_type == "application/pdf"
    assert receipt.case_id == SCOPE["case_id"]
    assert receipt.received_at.tzinfo is not None
    assert len(receipt.sha256) == 64
    assert "filename" not in receipt.model_dump()
    assert "bytes" not in receipt.model_dump()
    with pytest.raises(ValidationError):
        receipt.lifecycle = "current"


@pytest.mark.parametrize("filename", ["../a.pdf", "a\\b.pdf", "C:a.pdf", "a.pdf.exe", "%2e%2e%2fa.pdf", "a\x00.pdf", "a\u202epdf.exe", ".pdf", "CON.pdf"])
def test_unsafe_names_fail_closed(filename):
    with pytest.raises(intake.DocumentRejected):
        receive(filename=filename)


@pytest.mark.parametrize("data", [b'MZ executable', b'#!/bin/sh', b'<svg onload="x"/>', b'PK\x03\x04archive', b''])
def test_signature_and_extension_mismatch(data):
    with pytest.raises(intake.DocumentRejected):
        receive(data)


@pytest.mark.parametrize("token", [b'/JavaScript', b'/JS', b'/Launch', b'/EmbeddedFile', b'/OpenAction', b'/AA', b'/RichMedia', b'/Encrypt', b'/Java#53cript'])
def test_active_pdf_rejected(token):
    with pytest.raises(intake.DocumentRejected):
        receive(b'%PDF-1.7\n' + token + b'\n%%EOF')


def test_size_bound_applies_before_reading_more_chunks():
    def chunks():
        yield b'x' * (intake.MAX_DOCUMENT_BYTES + 1)
        raise AssertionError("must stop before consuming more data")
    with pytest.raises(intake.DocumentRejected):
        intake.inspect_document(chunks=chunks(), filename="a.pdf", metadata=metadata(), **SCOPE)


@pytest.mark.parametrize("overrides", [{"document_class": "executable"}, {"observed_at": "yesterday"},
    {"observed_at": "2026-02-30T00:00:00Z"}, {"observed_at": "2026-10-16"},
    {"remote_url": "http://localhost/private"}, {"source_id": "official"},
    {"effective_at": NOW, "expires_at": "2020-01-01T00:00:00Z"}, {"observed_at": 123}, {"observed_at": "123"}])
def test_malformed_metadata(overrides):
    with pytest.raises(intake.DocumentRejected):
        receive(metadata=metadata(**overrides))


def test_json_export_is_bounded_data_never_extracted_fact():
    receipt = receive(b'{"parcel": "123"}', filename="export.json")
    assert receipt.detected_media_type == "application/json"
    assert receipt.extraction_status == "not_attempted"
    for bad in [b'{bad}', b'null', b'{"x": NaN}', b'{"x": 1e999}', b'{"x": -1e999}', b'{"x": 1, "x": 2}']:
        with pytest.raises(intake.DocumentRejected):
            receive(bad, filename="export.json")


def test_client_content_type_is_not_authority_and_scope_is_required():
    assert receive(declared_content_type="application/x-msdownload").detected_media_type == "application/pdf"
    with pytest.raises(intake.DocumentRejected):
        intake.inspect_document(chunks=[b'{}'], filename="a.json", metadata=metadata(), workspace_id=None, case_id=None)


def test_identical_bytes_have_unique_version_ids_and_scoped_receipts():
    a, b = receive(), receive()
    assert a.sha256 == b.sha256
    assert a.version_id != b.version_id
    assert a.document_id != b.document_id


@pytest.mark.parametrize("key", ["token", "filename", "storage_url", "raw_payload", "extracted_text"])
def test_private_metadata_is_rejected_with_a_bounded_error(key):
    with pytest.raises(intake.DocumentRejected) as error:
        receive(metadata=metadata(**{key: "PRIVATE_SENTINEL"}))
    assert str(error.value) == "invalid_metadata"
    assert "PRIVATE_SENTINEL" not in str(error.value)


def test_image_signatures_remain_quarantined_without_decoding_or_providers(monkeypatch):
    import socket
    def no_network(*args, **kwargs):
        raise AssertionError("intake must not call a provider")
    monkeypatch.setattr(socket, "create_connection", no_network)
    for filename, content, media_type in [
        ("map.png", b'\x89PNG\r\n\x1a\nIEND\xaeB`\x82', "image/png"),
        ("map.jpg", b'\xff\xd8\xff\xe0\xff\xd9', "image/jpeg"),
    ]:
        receipt = receive(content, filename=filename)
        assert receipt.detected_media_type == media_type
        assert receipt.scan_status == "pending"
        assert receipt.extraction_status == "not_attempted"
