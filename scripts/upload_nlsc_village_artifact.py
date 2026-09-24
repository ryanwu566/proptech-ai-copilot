"""Operator-run immutable upload and verification for the NLSC artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

DEFAULT_BUCKET = "proptech-government-data"
FEATURES_KEY = "processed/nlsc/village-boundary/v1/features.json.gz"
MANIFEST_KEY = "processed/nlsc/village-boundary/v1/manifest.json"
REQUIRED_ENV = ("R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_ENDPOINT")


class UploadBlocked(RuntimeError):
    """Upload cannot proceed without operator credentials."""


class UploadConflict(RuntimeError):
    """An immutable object already contains different bytes."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _client():
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name, "").strip()]
    if missing:
        raise UploadBlocked("missing required R2 environment variables: " + ", ".join(missing))
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name=os.environ.get("R2_REGION", "auto"),
    )


def _head_or_none(client, bucket: str, key: str):
    try:
        return client.head_object(Bucket=bucket, Key=key)
    except Exception as exc:
        response = getattr(exc, "response", {})
        code = str(response.get("Error", {}).get("Code", "")) if isinstance(response, dict) else ""
        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode") if isinstance(response, dict) else None
        if code in {"404", "NoSuchKey", "NotFound"} or status == 404:
            return None
        raise


def _put_verified(client, bucket: str, key: str, data: bytes, content_type: str) -> dict[str, object]:
    digest = _sha256(data)
    head = _head_or_none(client, bucket, key)
    if head is not None:
        if head.get("ContentLength") == len(data) and (head.get("Metadata") or {}).get("sha256") == digest:
            return {"key": key, "action": "skip", "sha256": digest, "size": len(data)}
        raise UploadConflict(f"immutable object conflict: {key}")
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
        Metadata={"sha256": digest, "artifact": "nlsc-village-boundary-v1"},
    )
    head = client.head_object(Bucket=bucket, Key=key)
    if head.get("ContentLength") != len(data) or (head.get("Metadata") or {}).get("sha256") != digest:
        raise UploadConflict(f"post-upload HEAD verification failed: {key}")
    remote = client.get_object(Bucket=bucket, Key=key)["Body"]
    remote_data = remote.read() if hasattr(remote, "read") else remote
    if _sha256(remote_data) != digest:
        raise UploadConflict(f"post-upload GET checksum failed: {key}")
    return {"key": key, "action": "upload", "sha256": digest, "size": len(data), "verified": True}


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload NLSC processed artifact to R2 immutably")
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--bucket", default=os.environ.get("R2_BUCKET", DEFAULT_BUCKET))
    args = parser.parse_args()
    try:
        client = _client()
        artifact = args.artifact.read_bytes()
        manifest = args.manifest.read_bytes()
        result = {
            "bucket": args.bucket,
            "features": _put_verified(client, args.bucket, FEATURES_KEY, artifact, "application/gzip"),
            "manifest": _put_verified(client, args.bucket, MANIFEST_KEY, manifest, "application/json"),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except UploadBlocked as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    except (FileNotFoundError, UploadConflict) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
